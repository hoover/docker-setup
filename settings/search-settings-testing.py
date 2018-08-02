DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.postgresql_psycopg2',
       'NAME': 'search',
       'USER': 'search',
       'HOST': 'search-pg',
       'PORT': 5432,
   },
}

HOOVER_ELASTICSEARCH_URL = 'http://search-es:9200'
