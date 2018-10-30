import os
from urllib.parse import urlparse
from distutils.util import strtobool

from .defaultsettings import *

ALLOWED_HOSTS = ['snoop--testdata1']

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
        'HOST': 'snoop-pg--testdata1',
        'PORT': 5432,
    },
}

CELERY_BROKER_URL = 'amqp://snoop-rabbitmq'

SNOOP_TIKA_URL = 'http://snoop-tika:9998'

if os.environ.get('DOCKER_HOOVER_SNOOP_STATS', 'on') == 'on':
    SNOOP_STATS_ELASTICSEARCH_URL = 'http://snoop-stats-es:9200'

SNOOP_COLLECTIONS_ELASTICSEARCH_URL = 'http://search-es:9200'

SNOOP_GNUPG_HOME = '/opt/hoover/gnupg'

TASK_PREFIX = 'testdata1'

REMOTE_DEBUG_ENABLED = False

REMOTE_DEBUG_HOST = 'localhost'

REMOTE_DEBUG_PORT = 5678