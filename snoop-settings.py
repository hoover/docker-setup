import os
from pathlib import Path

base_dir = Path(__file__).absolute().parent.parent.parent.parent

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'snoop',
        'USER': 'snoop',
        'HOST': 'snoop-pg',
        'PORT': 5432,
    },
}

SECRET_KEY = os.environ['DOCKER_HOOVER_SNOOP_SECRET_KEY']
DEBUG = bool(os.environ.get('DOCKER_HOOVER_SEARCH_DEBUG'))
ALLOWED_HOSTS = ['snoop']

SNOOP_ELASTICSEARCH_URL = 'http://search-es:9200'
SNOOP_TIKA_SERVER_ENDPOINT = 'http://snoop-tika:9998'
SNOOP_TIKA_FILE_TYPES = ['doc', 'pdf', 'xls', 'ppt']
SNOOP_TIKA_MAX_FILE_SIZE = 32 * (2 ** 20)  # 32mb
SNOOP_MSGCONVERT_SCRIPT = 'msgconvert'
SNOOP_MSG_CACHE = str(base_dir.parent / 'cache' / 'msg')
SNOOP_ARCHIVE_CACHE_ROOT = str(base_dir.parent / 'cache' / 'archive')
SNOOP_SEVENZIP_BINARY = '7z'
SNOOP_ELASTICSEARCH_INDEX = 'hoover'
SNOOP_READPST_BINARY = 'readpst'
SNOOP_PST_CACHE_ROOT = str(base_dir.parent / 'cache' / 'pst')
