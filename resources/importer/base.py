import os
import base64
import logging
import time
import struct
from django.utils.text import slugify
from django.contrib.gis.gdal import DataSource, SpatialReference, CoordTransform
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point
from django.conf import settings
from modeltranslation.translator import translator

from resources.models import Unit, UnitIdentifier


def convert_from_wgs84(coords):
    pnt = Point(coords[1], coords[0], srid=4326)
    pnt.transform(PROJECTION_SRID)
    return pnt


class Importer(object):
    def find_data_file(self, data_file):
        for path in self.data_paths:
            full_path = os.path.join(path, data_file)
            if os.path.exists(full_path):
                return full_path
        raise FileNotFoundError("Data file '%s' not found" % data_file)

    def _set_field(self, obj, field_name, val):
        if not hasattr(obj, field_name):
            print(vars(obj))
        obj_val = getattr(obj, field_name)
        if obj_val == val:
            return

        field = obj._meta.get_field_by_name(field_name)[0]
        if field.get_internal_type() == 'CharField':
            if len(val) > field.max_length:
                raise Exception("field '%s' too long (max. %d): %s" % field_name, field.max_length, val)

        setattr(obj, field_name, val)
        obj._changed = True
        obj._changed_fields.append(field_name)

    def _update_fields(self, obj, info, skip_fields):
        obj_fields = list(obj._meta.fields)
        trans_fields = translator.get_options_for_model(type(obj)).fields
        for field_name, lang_fields in trans_fields.items():
            lang_fields = list(lang_fields)
            for lf in lang_fields:
                lang = lf.language
                # Do not process this field later
                skip_fields.append(lf.name)

                if field_name not in info:
                    continue

                data = info[field_name]
                if data is not None and lang in data:
                    val = data[lang]
                else:
                    val = None
                self._set_field(obj, lf.name, val)

            # Remove original translated field
            skip_fields.append(field_name)

        for d in skip_fields:
            for f in obj_fields:
                if f.name == d:
                    obj_fields.remove(f)
                    break

        for field in obj_fields:
            field_name = field.name
            if field_name not in info:
                continue
            self._set_field(obj, field_name, info[field_name])

    def _generate_id(self):
        t = time.time() * 1000000
        b = base64.b32encode(struct.pack(">Q", int(t)).lstrip(b'\x00')).strip(b'=').lower()
        return b.decode('utf8')

    def save_unit(self, data, obj):
        if not obj:
            obj = Unit()
            obj._created = True
        else:
            obj._created = False
            obj._changed = False
        obj._changed_fields = []

        self._update_fields(obj, data, ['id', 'identifiers'])

        obj.id = data.get('id')
        if not obj.id:
            obj.id = self._generate_id()

        if obj._created:
            print("%s created" % obj)
            obj.save()

        identifiers = {x.namespace: x for x in obj.identifiers.all()}
        for id_data in data.get('identifiers', []):
            ns = id_data['namespace']
            val = id_data['value']
            if ns in identifiers:
                id_obj = identifiers[ns]
                if id_obj.value != val:
                    id_obj.value = val
                    id_obj.save()
                    obj._changed = True
            else:
                id_obj = UnitIdentifier(unit=obj, namespace=ns, value=val)
                id_obj.save()
                obj._changed = True

        if obj._changed:
            if not obj._created:
                print("%s changed: %s" % (obj, ', '.join(obj._changed_fields)))
            obj.save()

        return obj

    def __init__(self, options):
        self.logger = logging.getLogger("%s_importer" % self.name)

        if hasattr(settings, 'PROJECT_ROOT'):
            root_dir = settings.PROJECT_ROOT
        else:
            root_dir = settings.BASE_DIR
        self.data_paths = [os.path.join(root_dir, 'data')]
        module_path = os.path.dirname(__file__)
        app_path = os.path.abspath(os.path.join(module_path, '..', 'data'))
        self.data_paths.append(app_path)

        self.options = options

importers = {}

def register_importer(klass):
    importers[klass.name] = klass
    return klass

def get_importers():
    if importers:
        return importers
    module_path = __name__.rpartition('.')[0]
    # Importing the packages will cause their register_importer() methods
    # being called.
    for fname in os.listdir(os.path.dirname(__file__)):
        module, ext = os.path.splitext(fname)
        if ext.lower() != '.py':
            continue
        if module in ('__init__', 'base'):
            continue
        full_path = "%s.%s" % (module_path, module)
        ret = __import__(full_path, locals(), globals())
    return importers