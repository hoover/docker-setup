from distutils.util import strtobool
import os
from urllib.parse import urlparse

from .defaultsettings import *

ALLOWED_HOSTS = ['snoop--{{ collection_name }}']

snoop_base_url = os.environ['DOCKER_HOOVER_SNOOP_BASE_URL']
if snoop_base_url:
    ALLOWED_HOSTS.append(urlparse(snoop_base_url).netloc)

SECRET_KEY = os.environ['DOCKER_HOOVER_SNOOP_SECRET_KEY']
DEBUG = bool(strtobool(os.environ.get('DOCKER_HOOVER_SNOOP_DEBUG')))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'snoop',
        'USER': 'snoop',
        'HOST': 'snoop-pg--{{ collection_name }}',
        'PORT': 5432,
    },
}

CELERY_BROKER_URL = 'amqp://snoop-rabbitmq'

SNOOP_TIKA_URL = 'http://snoop-tika:9998'

if os.environ.get('DOCKER_HOOVER_SNOOP_STATS', 'on') == 'on':
    SNOOP_STATS_ELASTICSEARCH_URL = 'http://snoop-stats-es:9200'

SNOOP_COLLECTIONS_ELASTICSEARCH_URL = 'http://search-es:9200'

SNOOP_GNUPG_HOME = '/opt/hoover/gnupg'

TASK_PREFIX = '{{ collection_name }}'

SNOOP_COLLECTIONS_ELASTICSEARCH_INDEX = '{{ collection_index }}'

SNOOP_COLLECTION_ROOT = 'collection'

