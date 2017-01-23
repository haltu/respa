DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'postgres',
        'USER': 'postgres',
        'CONN_MAX_AGE': 600,
        'HOST': 'db',
        'PORT': 5432,
        'ATOMIC_REQUESTS': True,
    }
}

# Containers are assumed to be test environments by default
DEBUG = True

STATIC_ROOT = '/code/static'
MEDIA_ROOT = '/code/media'
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

LOGIN_REDIRECT_URL = 'https://example.com/respa/admin/'
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

RESPA_MAILS_ENABLED = False
