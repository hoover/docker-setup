from base64 import b64encode
from collections import OrderedDict
from copy import copy
from curses.ascii import isalpha
from distutils.util import strtobool
from functools import reduce
import os
from pathlib import Path
import re
from shutil import rmtree

from jinja2 import Template
import yaml
import json

root_dir = Path(__file__).absolute().parent.parent
collection_allowed_chars = 'a-z, A-Z, 0-9'
start_snoop_port = 45025
default_flower_port = 5555
start_flower_port = 15555
collections_dir_name = 'collections'
instructions_dir_name = 'instructions'
settings_dir_name = 'settings'
templates_dir_name = 'templates'
volumes_dir_name = 'volumes'
blobs_dir_name = 'snoop-blobs'
docker_file_name = 'docker-compose.override.yml'
docker_dev_file_name = 'docker-compose.override-dev.yml'
orig_docker_file_name = 'docker-compose.override-orig.yml'
new_docker_file_name = 'docker-compose.override-new.yml'
docker_collection_file_name = 'docker-collection.yml'
custom_services_file_name = 'docker-custom-services.yml'
snoop_settings_file_name = 'snoop-settings.py'
snoop_settings_profiling_file_name = 'snoop-settings-profiling.py'
snoop_settings_dev_file_name = 'snoop-settings-dev.py'
snoop_settings_tracing_file_name = 'snoop-settings-tracing.py'
collections_settings_file_name = 'collections.json'
env_file_name = 'snoop.env'
default_pg_port = 5432
collection_exists_msg = 'Collection %s already exists!'
default_snoop_image = 'liquidinvestigations/hoover-snoop2:0.1.2'
DOCKER_HOOVER_SNOOP_SECRET_KEY = 'DOCKER_HOOVER_SNOOP_SECRET_KEY'
DOCKER_HOOVER_SNOOP_DEBUG = 'DOCKER_HOOVER_SNOOP_DEBUG'
DOCKER_HOOVER_SNOOP_BASE_URL = 'DOCKER_HOOVER_SNOOP_BASE_URL'
default_collections_data = {
    'collections': {},
    'snoop_port': start_snoop_port,
    'pg_port': default_pg_port + 1,
    'flower_port': start_flower_port,
    'dev_instances': 0,
    'stats_clients': 0
}
collections_path = Path(__file__).resolve().parent.parent / collections_dir_name
volumes_path = Path(__file__).resolve().parent.parent / volumes_dir_name
blobs_path = Path(__file__).resolve().parent.parent / blobs_dir_name
ocr_path = Path(__file__).resolve().parent.parent / 'ocr'


def gen_secret_key():
    return b64encode(os.urandom(100)).decode('utf-8')


default_collection_settings = {
    'autoindex': True,
    'profiling': False,
    'tracing': False,
    'for_dev': False,
    'image': default_snoop_image,
    'env': {
        DOCKER_HOOVER_SNOOP_SECRET_KEY: gen_secret_key(),
        DOCKER_HOOVER_SNOOP_BASE_URL: 'http://localhost',
        DOCKER_HOOVER_SNOOP_DEBUG: False
    }
}


def exit_msg(msg, *args):
    print(msg % tuple(args))
    exit(1)


class InvalidCollectionName(RuntimeError):
    pass


class DuplicateCollection(RuntimeError):
    pass


def validate_collection_name(collection_name, collections={}, new=True):
    '''Return true if the given name is a valid collection name
    :param collection_name:
    :return: bool
    '''
    if not collection_name:
        raise InvalidCollectionName('Collection name must not be empty.')
    if not re.search('^[a-zA-Z0-9]+$', collection_name):
        raise InvalidCollectionName('Invalid collection name %s. Allowed characters: "%s"' %
                                    (collection_name, collection_allowed_chars))
    if not isalpha(collection_name[0]):
        raise InvalidCollectionName('The first character must be a letter.')

    if new:
        for collection in collections:
            if collection.lower() == collection_name.lower():
                raise InvalidCollectionName('Collection %s already exists' % collection_name)
    elif collection_name not in collections:
        raise InvalidCollectionName('Collection %s does not exist' % collection_name)


def get_collection_data_dir(collection_name):
    return os.path.join(collections_dir_name, collection_name)


def validate_collection_data_dir(collection_name):
    data_dir = get_collection_data_dir(collection_name)
    if not os.path.isdir(data_dir):
        print('Collection %s does not have a data directory (%s)' % (collection_name, data_dir))
        exit(1)


def has_volume(settings, volume_local):
    '''Return true if the service docker compose settings contain a volume linked
    to the given local directory.
    :param settings: service settings in dict format
    :param volume_local: local path
    :return: bool
    '''
    if 'volumes' not in settings:
        return False
    for volume in settings['volumes']:
        if volume_local == volume.split(sep=':')[0]:
            return True
    return False


def get_collections_data_old():
    '''Return collections data in form of a tuple of ordered dictionary, next
    snoop available port, next postgresql available port (for development),
    next port available for flower web admin, number of development instances

    :return: dict
    '''
    if not os.path.isfile(docker_file_name):
        return default_collections_data

    collections = {}
    last_snoop_port = start_snoop_port - 1
    pg_port = default_pg_port + 1
    flower_port = start_flower_port
    dev_instances = 0

    with open(docker_file_name) as collections_file:
        collections_settings = yaml.load(collections_file, Loader=yaml.FullLoader)
        for service, settings in collections_settings['services'].items():
            if service.startswith('snoop--'):
                collection_name = service[len('snoop--'):]
                collections.setdefault(collection_name, {}).update({
                    'profiling': has_volume(settings, './profiles/%s' % collection_name) and
                    has_volume(settings, './settings/urls.py'),
                    'for_dev': has_volume(settings, '../snoop2'),
                    'image': settings['image']})
                if collections[collection_name]['for_dev']:
                    dev_instances += 1
                    pg_port += 1

                port = int(settings['ports'][0].split(sep=':')[0])
                collections[collection_name]['snoop_port'] = port
                if port > last_snoop_port:
                    last_snoop_port = port
            if service.startswith('snoop-worker--'):
                collection_name = service[len('snoop-worker--'):]
                collections.setdefault(collection_name, {}).update({
                    'autoindex': settings.get('command', '').find('./manage.py runworkers') != -1})
                if settings.get('ports'):
                    collections[collection_name]['flower_port'] = int(settings['ports'][0].split(':')[0])
                    if collections[collection_name]['flower_port'] > flower_port:
                        flower_port = collections[collection_name]['flower_port']
                flower_port += 1

    for collection_name in collections:
        collections[collection_name]['env'] = read_env_file(get_settings_dir(collection_name))

    ordered_collections = OrderedDict(sorted(collections.items(), key=lambda t: t[0]))

    return {
        'collections': ordered_collections,
        'snoop_port': last_snoop_port + 1,
        'pg_port': pg_port,
        'flower_port': flower_port,
        'dev_instances': dev_instances
    }


def get_collections_data():
    '''Return collections data in form of a tuple of ordered dictionary, next
    snoop available port, next postgresql available port (for development),
    next port available for flower web admin, number of development instance

    :return: dict
    '''
    collections_file_name = os.path.join(settings_dir_name, collections_settings_file_name)

    if not os.path.isfile(collections_file_name):
        return get_collections_data_old()

    last_snoop_port = start_snoop_port - 1
    pg_port = default_pg_port + 1
    flower_port = start_flower_port
    dev_instances = 0

    with open(collections_file_name) as collections_file:
        collections = json.load(collections_file)

    for settings in collections.values():
        if settings['for_dev']:
            dev_instances += 1
            pg_port += 1
            if settings['pg_port'] >= pg_port:
                pg_port = settings['pg_port'] + 1
        if settings['snoop_port'] > last_snoop_port:
            last_snoop_port = settings['snoop_port']
        if settings.get('flower_port') and settings['flower_port'] >= flower_port:
            flower_port = settings['flower_port'] + 1

    ordered_collections = OrderedDict(sorted(collections.items(), key=lambda t: t[0]))

    return {
        'collections': ordered_collections,
        'snoop_port': last_snoop_port + 1,
        'pg_port': pg_port,
        'flower_port': flower_port,
        'dev_instances': dev_instances
    }


def write_collections_settings(settings):
    '''Write collections settings to the settings file
    :param settings: dictionary containing collections
    '''
    coll_settings = settings if 'collections' not in settings else settings['collections']

    with open(os.path.join(settings_dir_name, collections_settings_file_name), 'w') as settings_file:
        settings_file.write(json.dumps(coll_settings, indent=4))


def init_collection_settings(collections, args, data):
    collections[args.collection] = {
        'autoindex': not args.manual_indexing,
        'image': args.snoop_image,
        'profiling': args.profiling,
        'tracing': args.tracing,
        'for_dev': args.dev,
        'snoop_port': data['snoop_port'],
        'flower_port': data['flower_port'] if not args.manual_indexing else None,
        'pg_port': data['pg_port'] if args.dev else None,
        'env': default_collection_settings['env']
    }
    collections[args.collection]['env'][DOCKER_HOOVER_SNOOP_DEBUG] = args.dev


def update_collections_settings(settings, attributes, collections_names=None):
    if not collections_names:
        return
    collections = settings['collections']
    for collection in collections_names:
        if collection not in collections:
            raise InvalidCollectionName('Collection %s does not exist' % collection)
        for attribute, new_value in attributes.items():
            setting = collections[collection]

            path = attribute.split(sep='.')
            while len(path) > 1:
                attribute = path.pop(0)
                if attribute not in setting:
                    setting[attribute] = {}
                setting = setting[attribute]
            attribute = path.pop(0)
            setting[attribute] = new_value

            if attribute == 'autoindex':
                collections[collection]['flower_port'] = settings['flower_port'] if new_value else None
            if attribute == 'for_dev':
                collections[collection]['pg_port'] = settings['pg_port'] if new_value else None
                collections[collection]['env'][DOCKER_HOOVER_SNOOP_DEBUG] = new_value


def validate_collections(collections, exit_on_errors=True):
    '''Validates the collections found in the given list/dict of collections
    :param collections: a list/dict o collections
    :param exit_on_errors: if true exit when errors were found
    '''
    errors = []
    for collection_name in collections:
        settings_dir = os.path.join(settings_dir_name, collection_name)
        if not os.path.isdir(settings_dir):
            errors.append('Collection %s does not have a settings directory (%s)' %
                          (collection_name, settings_dir))
        snoop_settings_file = os.path.join(settings_dir, snoop_settings_file_name)
        if not os.path.isfile(snoop_settings_file):
            errors.append('Collection %s has no snoop settings file (%s)' %
                          (collection_name, snoop_settings_file))
        env_file = os.path.join(settings_dir, env_file_name)
        if not os.path.isfile(env_file):
            errors.append('Collection %s has no docker environment file (%s)' %
                          (collection_name, env_file))
    if errors and exit_on_errors:
        print('\n'.join(errors))
        exit(1)


def collection_selected(collection, collections):
    '''Returns true if the given collection was selected. A collection is selected
    if it was found in the list of collections or the list of collections is empty.
    :param collection: collection name
    :param collections: list of collections
    :return: bool
    '''
    if collections is None:
        return False
    if len(collections) == 0:
        return True
    return reduce(lambda found, elem: found or collection.lower() == elem.lower(),
                  collections, False)


def cleanup(collection_name):
    '''Does a cleanup of collection files. Used when the collection creation
    encountered an error.
    :param collection_name:
    '''
    settings_dir = os.path.join(settings_dir_name, collection_name)
    if os.path.isdir(settings_dir):
        rmtree(settings_dir, ignore_errors=True)
    pg_dir = os.path.join(volumes_dir_name, 'snoop-pg--%s' % collection_name)
    if os.path.isdir(pg_dir):
        rmtree(pg_dir, ignore_errors=True)


def get_settings_dir(collection_name):
    '''Get the settings directory for the given collection.

    :param collection_name: the collection name
    :return: str
    '''
    return os.path.join(settings_dir_name, collection_name)


def create_settings_dir(collection_name, ignore_exists=False):
    '''Create the directory for settings files. Returns the settings directory path.

    :param collection_name: the collection name
    :param ignore_exists: if true do not exit when the directory already exists
    :return: str
    '''
    settings_dir = get_settings_dir(collection_name)
    try:
        os.mkdir(settings_dir)
    except FileExistsError:
        if not ignore_exists:
            exit_msg(collection_exists_msg, collection_name)
    return settings_dir


def read_env_file(settings_dir):
    '''Read the env file correspoding to the given collection. Returns a dictionary
    containing the environment variables.

    :param settings_dir: the directory containing the settings files
    :return: dict
    '''
    env_vars = [DOCKER_HOOVER_SNOOP_SECRET_KEY, DOCKER_HOOVER_SNOOP_DEBUG,
                DOCKER_HOOVER_SNOOP_BASE_URL]
    bool_vars = [DOCKER_HOOVER_SNOOP_DEBUG]
    env = {}
    with open(os.path.join(settings_dir, env_file_name)) as env_file:
        for line in env_file.readlines():
            for var in env_vars:
                if var in line:
                    env[var] = line.split(sep='=', maxsplit=1)[1].strip()
                    if var in bool_vars:
                        env[var] = bool(strtobool(env[var]))
    return env


def write_env_file(settings_dir, settings):
    '''Generate the environment file in the given settings directory.

    :param settings_dir: the directory containing the settings files
    :param env: dictionary with environment variables
    '''
    bool_params = {DOCKER_HOOVER_SNOOP_DEBUG: False}
    if 'env' not in settings:
        settings['env'] = {}
    tpl_env = copy(settings['env'])
    for bool_param, value in bool_params.items():
        if bool_param not in settings['env']:
            settings['env'][bool_param] = value
        tpl_env[bool_param] = 'on' if settings['env'][bool_param] else 'off'
    settings['env'].setdefault(DOCKER_HOOVER_SNOOP_SECRET_KEY, gen_secret_key())
    settings['env'].setdefault(DOCKER_HOOVER_SNOOP_BASE_URL, 'http://localhost')

    with open(os.path.join(templates_dir_name, env_file_name)) as env_template:
        template = Template(env_template.read())
        env_settings = template.render(tpl_env)

    with open(os.path.join(settings_dir, env_file_name), mode='w') as env_file:
        env_file.write(env_settings)


def write_env_files(collections):
    '''Generate environment files for the given collections.

    :param collections: list/dictionary of collections
    '''
    for collection, settings in collections.items():
        settings_dir = create_settings_dir(collection, ignore_exists=True)
        write_env_file(settings_dir, settings)


def write_python_settings_file(collection, settings_dir, settings):
    '''Generate the corresponding collection python settings file.

    :param collection: the collection name
    :param settings_dir: the directory containing the settings files
    :param settings: dictionary containing collection settings
    '''
    with open(os.path.join(templates_dir_name, snoop_settings_file_name)) as settings_template:
        template = Template(settings_template.read())
        snoop_settings = template.render(collection_name=collection,
                                         collection_index=collection.lower(),
                                         collection_root=get_collection_data_dir(collection))
    if settings.get('profiling'):
        with open(os.path.join(templates_dir_name, snoop_settings_profiling_file_name)) as \
                profiling_template:
            snoop_settings += Template(profiling_template.read()).render()
    if settings.get('for_dev'):
        with open(os.path.join(templates_dir_name, snoop_settings_dev_file_name)) as \
                dev_template:
            snoop_settings += Template(dev_template.read()).render()
    if settings.get('tracing'):
        with open(os.path.join(templates_dir_name, snoop_settings_tracing_file_name)) as \
                tracing_template:
            snoop_settings += Template(tracing_template.read()).render()

    with open(os.path.join(settings_dir, snoop_settings_file_name), mode='w') as settings_file:
        settings_file.write(snoop_settings)


def write_python_settings_files(collections):
    '''Generate the collections settings files.

    :param collections: the dictionary containing the collections settings
    '''
    for collection, settings in collections.items():
        settings_dir = create_settings_dir(collection, ignore_exists=True)
        write_python_settings_file(collection, settings_dir, settings)


def write_collection_docker_file(collection, settings_dir, settings):
    '''Generate the corresponding collection docker file using the docker template.

    :param collection: the collection name
    :param settings_dir: the directory containing the settings files
    :param settings: dictionary containing the collection settings
    '''
    dev_volumes = '\n      - ../snoop2:/opt/hoover/snoop:cached' if settings.get('for_dev') else ''
    pg_port = settings.get('pg_port', default_pg_port + 1)
    if settings.get('for_dev'):
        dev_ports = '    ports:\n      - "%d:%d"\n' % (pg_port, default_pg_port)
    else:
        dev_ports = ''
    snoop_port = settings.get('snoop_port', start_snoop_port)
    profiling_volumes = ''
    if settings.get('profiling'):
        profiling_volumes = '\n      - ./%s:/opt/hoover/snoop/profiles' % \
                            os.path.join('profiles', collection) + \
                            '\n      - ./settings/urls.py:/opt/hoover/snoop/snoop/urls.py'
    if settings.get('autoindex'):
        index_command = '    command: ./manage.py runworkers\n'
    else:
        index_command = '    command: echo "disabled"\n'
    if settings.get('flower_port'):
        flower_port_text = '    ports:\n      - "%d:%d"\n' % (settings['flower_port'], default_flower_port)
    else:
        flower_port_text = ''

    with open(os.path.join(templates_dir_name, docker_collection_file_name)) as docker_template:
        template = Template(docker_template.read())
        collection_settings = template.render(collection_name=collection,
                                              snoop_image=settings['image'],
                                              snoop_port=snoop_port,
                                              profiling_volumes=profiling_volumes,
                                              dev_volumes=dev_volumes,
                                              dev_ports=dev_ports,
                                              index_command=index_command,
                                              flower_port=flower_port_text)

    with open(os.path.join(settings_dir, docker_collection_file_name), mode='w') \
            as collection_file:
        collection_file.write(collection_settings)


def read_collection_docker_file(collection, settings_dir):
    '''Read the docker file correspoding to the given collection. Returns the coolection
    snoop image, the snoop web admin port exposed by docker and the flower web admin port.

    :param collection: the collection name
    :param settings_dir: the directory containing the settings files
    :return: (str, int, int)
    '''
    with open(os.path.join(settings_dir, docker_collection_file_name)) as collection_file:
        settings = yaml.load(collection_file, Loader=yaml.FullLoader)
        snoop_image = settings['snoop-worker--' + collection]['image']
        snoop_port = int(settings['snoop--' + collection]['ports'][0].split(sep=':')[0])
        if 'ports' in settings['snoop-worker--' + collection]:
            flower_port = int(settings['snoop-worker--' + collection]['ports'][0].split(sep=':')[0])
        else:
            flower_port = None
        return snoop_image, snoop_port, flower_port


def write_collections_docker_files(collections):
    '''Generate the collections docker files. Returns the number of dev instances.

    :param collections: the dictionary containing the collections settings
    :return: int
    '''
    pg_port = default_pg_port + 1
    last_snoop_port = start_snoop_port
    next_flower_port = start_flower_port
    dev_instances = 0
    flower_ports = set()
    snoop_ports = set()

    for collection, settings in collections.items():
        validate_collection_data_dir(collection)

        settings_dir = create_settings_dir(collection, ignore_exists=True)

        dev_instances += int(settings.get('for_dev', False))

        if settings.get('autoindex'):
            if not settings.get('flower_port') or settings['flower_port'] in flower_ports:
                settings['flower_port'] = next_flower_port
            if next_flower_port <= settings['flower_port']:
                next_flower_port += 1
            flower_ports.add(settings['flower_port'])
        else:
            settings['flower_port'] = None

        if settings.get('snoop_port') and settings['snoop_port'] not in snoop_ports:
            last_snoop_port = settings['snoop_port']
        else:
            last_snoop_port += 1
            settings['snoop_port'] = last_snoop_port
        snoop_ports.add(last_snoop_port)

        write_collection_docker_file(collection, settings_dir, settings)
        pg_port += 1
    return dev_instances


def write_global_docker_file(collections, for_dev=False):
    '''Generate the override docker file from collection docker files.

    :param collections: the collections name list
    :param for_dev: if true, will add development settings
    '''
    if len(collections) == 0:
        if os.path.isfile(docker_file_name):
            os.rename(docker_file_name, orig_docker_file_name)
        return

    with open(str(root_dir / new_docker_file_name), 'w') as new_docker_file:
        new_docker_file.write('version: "3.3"\n\nservices:\n')

        custom_services_file_path = os.path.join(templates_dir_name, custom_services_file_name)
        if os.path.isfile(custom_services_file_path):
            with open(custom_services_file_path) as custom_services_file:
                new_docker_file.write(custom_services_file.read())
            new_docker_file.write('\n')

        template_file = docker_file_name if not for_dev else docker_dev_file_name
        with open(os.path.join(templates_dir_name, template_file)) as docker_file:
            new_docker_file.write(docker_file.read())

        snoop_collections = '\n      - '.join(['snoop--' + c for c in collections])
        new_docker_file.write('    depends_on:\n      - %s\n' % snoop_collections)
        snoop_aliases = ''.join(['\n      - "snoop--%s:snoop--%s"' % (c, c.lower()) if c != c.lower()
                                 else '' for c in collections])
        if snoop_aliases:
            new_docker_file.write('    links:%s\n' % snoop_aliases)

        for collection_name in collections:
            new_docker_file.write('\n')
            collection_docker_file_path = os.path.join(settings_dir_name, collection_name,
                                                       docker_collection_file_name)
            with open(collection_docker_file_path) as collection_docker_file:
                new_docker_file.write(collection_docker_file.read())
            new_docker_file.write('\n')

    if os.path.isfile(str(root_dir / docker_file_name)):
        os.rename(str(root_dir / docker_file_name), str(root_dir / orig_docker_file_name))
    os.rename(str(root_dir / new_docker_file_name), str(root_dir / docker_file_name))
