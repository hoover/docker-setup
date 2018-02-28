import os
from .defaultsettings import *

ALLOWED_HOSTS = ['snoop']

SECRET_KEY = os.environ['DOCKER_HOOVER_SNOOP_SECRET_KEY']
DEBUG = bool(os.environ.get('DOCKER_HOOVER_SNOOP_DEBUG'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'snoop',
        'USER': 'snoop',
        'HOST': 'snoop-pg',
        'PORT': 5432,
    },
}

CELERY_BROKER_URL = 'amqp://snoop-rabbitmq'

SNOOP_TIKA_URL = 'http://snoop-tika:9998'
