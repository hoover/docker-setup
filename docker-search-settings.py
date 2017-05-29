from urllib.parse import urlparse
import os
from pathlib import Path

base_dir = Path(__file__).absolute().parent.parent.parent.parent

SECRET_KEY = os.environ['DOCKER_HOOVER_SEARCH_SECRET_KEY']

HOOVER_BASE_URL = os.environ['DOCKER_HOOVER_BASE_URL']
ALLOWED_HOSTS = [urlparse('http://hoover.docker.tufa').netloc]

DEBUG = bool(os.environ.get('DOCKER_HOOVER_SEARCH_DEBUG'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'search',
        'USER': 'search',
        'HOST': 'search-pg',
        'PORT': 5432,
    },
}

STATIC_ROOT = str(base_dir / 'static')

HOOVER_UPLOADS_ROOT = str(base_dir / 'uploads')
HOOVER_UI_ROOT = str(base_dir.parent / 'ui' / 'build')
HOOVER_EVENTS_DIR = str(base_dir.parent / 'metrics' / 'users')
HOOVER_ELASTICSEARCH_URL = 'http://search-es:9200'
