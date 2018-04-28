from urllib.parse import urlparse
import os
from pathlib import Path

base_dir = Path(__file__).absolute().parent.parent.parent.parent

SECRET_KEY = os.environ['DOCKER_HOOVER_SEARCH_SECRET_KEY']

HOOVER_BASE_URL = os.environ['DOCKER_HOOVER_BASE_URL']
ALLOWED_HOSTS = [urlparse(HOOVER_BASE_URL).netloc]

DEBUG = bool(os.environ.get('DOCKER_HOOVER_SEARCH_DEBUG'))

if bool(os.environ.get('DOCKER_HOOVER_TWOFACTOR_ENABLED')):
    from hoover.site.settings.common import INSTALLED_APPS
    from hoover.site.settings.common import MIDDLEWARE_CLASSES

    INSTALLED_APPS += (
        'hoover.contrib.twofactor',
        'django_otp',
        'django_otp.plugins.otp_totp',
        'hoover.contrib.ratelimit',
    )

    MIDDLEWARE_CLASSES += (
        'django_otp.middleware.OTPMiddleware',
        'hoover.contrib.twofactor.middleware.AutoLogout',
        'hoover.contrib.twofactor.middleware.RequireAuth',
    )

    if 'DOCKER_HOOVER_TWOFACTOR_INVITATION_VALID' in os.environ:
        HOOVER_TWOFACTOR_INVITATION_VALID = \
            int(os.environ['DOCKER_HOOVER_TWOFACTOR_INVITATION_VALID'])

    if 'DOCKER_HOOVER_TWOFACTOR_AUTOLOGOUT' in os.environ:
        HOOVER_TWOFACTOR_AUTOLOGOUT = \
            int(os.environ['DOCKER_HOOVER_TWOFACTOR_AUTOLOGOUT'])

    HOOVER_RATELIMIT_USER = (30, 60) # 30 per minute
    HOOVER_TWOFACTOR_RATELIMIT = (3, 60) # 3 per minute

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
