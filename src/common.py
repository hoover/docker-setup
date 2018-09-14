from base64 import b64encode
from collections import OrderedDict
from curses.ascii import isalpha
from functools import reduce
import os
import re
from shutil import rmtree

from jinja2 import Template
import yaml

collection_allowed_chars = 'a-z, A-Z, 0-9, _'
start_snoop_port = 45025
collections_dir_name = 'collections'
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
env_file_name = 'snoop.env'
default_pg_port = 5432
collection_exists_msg = 'Collection %s already exists!'
default_snoop_image = 'liquidinvestigations/hoover-snoop2'


def exit_msg(msg, *args):
    print(msg % tuple(args))
    exit(1)


def validate_collection_name(collection_name):
    '''Return true if the given name is a valid collection name
    :param collection_name:
    :return: bool
    '''
    if not collection_name:
        print('Collection name must not be empty.')
        exit(1)
    if re.search('\W+', collection_name):
        print('Invalid collection name ' + collection_name)
        print('Allowed characters: ' + collection_allowed_chars)
        exit(1)
    if not isalpha(collection_name[0]):
        print('The first character must be a letter.')
        exit(1)


def validate_collection_data_dir(collection_name):
    data_dir = os.path.join(collections_dir_name, collection_name)
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


def get_collections_data(new_collection=None):
    '''Return collections data in form of a tuple of ordered dictionary, next
    snoop available port, next postgresql available port (for development),
    number of development instance
    :param new_collection: new collection name (if any)
    :return: (OrderedDict, bool, bool, int)
    '''
    if not os.path.isfile(docker_file_name):
        return {}, start_snoop_port, default_pg_port + 1, False

    collections = {}
    last_snoop_port = start_snoop_port - 1
    pg_port = default_pg_port + 1
    dev_instances = 0
    exists = False

    with open(docker_file_name) as collections_file:
        collections_settings = yaml.load(collections_file)
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

                if new_collection and collection_name.lower() == new_collection.lower():
                    exit_msg(collection_exists_msg, new_collection)
                exists = exists or (new_collection and collection_name.lower() == new_collection.lower())

                port = int(settings['ports'][0].split(sep=':')[0])
                if port > last_snoop_port:
                    last_snoop_port = port
            if service.startswith('snoop-worker--'):
                collection_name = service[len('snoop-worker--'):]
                collections.setdefault(collection_name, {}).update({
                    'autoindex': settings.get('command') == './manage.py runworkers'})

    ordered_collections = OrderedDict(sorted(collections.items(), key=lambda t: t[0]))

    return ordered_collections, last_snoop_port + 1, pg_port, dev_instances


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
        docker_file = os.path.join(settings_dir, docker_collection_file_name)
        if not os.path.isfile(docker_file):
            errors.append('Collection %s does not have a docker compose yml file (%s)' %
                          (collection_name, docker_file))
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


def create_settings_dir(collection, ignore_exists=False):
    '''Create the directory for settings files. Returns the settings directory path.

    :param collection: the collection name
    :param ignore_exists: if true do not exit when the directory already exists
    :return: str
    '''
    settings_dir = os.path.join(settings_dir_name, collection)
    try:
        os.mkdir(settings_dir)
    except FileExistsError:
        if not ignore_exists:
            exit_msg(collection_exists_msg, collection)
    return settings_dir


def write_env_file(settings_dir):
    with open(os.path.join(templates_dir_name, env_file_name)) as env_template:
        template = Template(env_template.read())
        env_settings = template.render(secret_key=b64encode(os.urandom(100)).decode('utf-8'))

    with open(os.path.join(settings_dir, env_file_name), mode='w') as env_file:
        env_file.write(env_settings)


def write_env_files(collections):
    for collection in collections:
        settings_dir = create_settings_dir(collection, ignore_exists=True)
        write_env_file(settings_dir)


def write_python_settings_file(collection, settings_dir, profiling=False, for_dev=False):
    '''Generate the corresponding collection python settings file.

    :param collection: the collection name
    :param settings_dir: the directory containing the settings files
    :param profiling: if true, will add profiling settings
    :param for_dev: if true, will add development settings
    '''
    with open(os.path.join(templates_dir_name, snoop_settings_file_name)) as settings_template:
        template = Template(settings_template.read())
        snoop_settings = template.render(collection_name=collection)
    if profiling:
        with open(os.path.join(templates_dir_name, snoop_settings_profiling_file_name)) as \
                profiling_template:
            snoop_settings += Template(profiling_template.read()).render()
    if for_dev:
        with open(os.path.join(templates_dir_name, snoop_settings_dev_file_name)) as \
                dev_template:
            snoop_settings += Template(dev_template.read()).render()

    with open(os.path.join(settings_dir, snoop_settings_file_name), mode='w') as settings_file:
        settings_file.write(snoop_settings)


def write_python_settings_files(collections, profiling_collections=None, remove_profiling=False,
                                dev_collections=None, remove_dev=False):
    '''Generate the collections settings files.

    :param collections: the collections name list
    :param profiling_collections: the collections selected for profiling/no profiling
    :param remove_profiling: if true, remove profiling from collections in profiling_collections
    :param dev_collections: collections selected for dev/no dev
    :param remove_dev: if true, remove dev from collections in dev_collections
    '''
    for collection, settings in collections.items():
        settings_dir = create_settings_dir(collection, ignore_exists=True)
        if remove_profiling:
            profiling = not collection_selected(collection, profiling_collections) and settings['profiling']
        else:
            profiling = collection_selected(collection, profiling_collections) or settings['profiling']
        if remove_dev:
            for_dev = not collection_selected(collection, dev_collections) and settings['for_dev']
        else:
            for_dev = collection_selected(collection, dev_collections) or settings['for_dev']

        write_python_settings_file(collection, settings_dir,
                                   profiling=profiling, for_dev=for_dev)


def write_collection_docker_file(collection, snoop_image, settings_dir, snoop_port,
                                 profiling=False, for_dev=False, pg_port=None, autoindex=True):
    '''Generate the corresponding collection docker file using the docker template.

    :param collection: the collection name
    :param snoop_image: the snoop image name
    :param settings_dir: the directory containing the settings files
    :param snoop_port: the snoop web admin port exposed by docker
    :param profiling: if true, will add profiling settings
    :param for_dev: if true, will add development settings
    :param pg_port: the port on which the postgresql database is exposed if for_dev enabled
    :param autoindex: if true add the command to automatically index the collection
    '''
    dev_volumes = '\n      - ../snoop2:/opt/hoover/snoop:cached' if for_dev else ''
    pg_port = pg_port if pg_port else default_pg_port + 1
    dev_ports = '    ports:\n      - "%d:%d"\n' % (pg_port, default_pg_port) if for_dev else ''
    snoop_port = snoop_port if snoop_port else start_snoop_port
    profiling_volumes = ''
    if profiling:
        profiling_volumes = '\n      - ./%s:/opt/hoover/snoop/profiles' % \
                            os.path.join('profiles', collection) + \
                            '\n      - ./settings/urls.py:/opt/hoover/snoop/snoop/urls.py'
    index_command = '    command: ./manage.py runworkers\n' if autoindex else ''

    with open(os.path.join(templates_dir_name, docker_collection_file_name)) as docker_template:
        template = Template(docker_template.read())
        collection_settings = template.render(collection_name=collection,
                                              snoop_image=snoop_image,
                                              snoop_port=snoop_port,
                                              profiling_volumes=profiling_volumes,
                                              dev_volumes=dev_volumes,
                                              dev_ports=dev_ports,
                                              index_command=index_command)

    with open(os.path.join(settings_dir, docker_collection_file_name), mode='w') \
            as collection_file:
        collection_file.write(collection_settings)


def read_collection_docker_file(collection, settings_dir):
    '''Read the docker file correspoding to the given collection. Returns the coolection
    snoop image and the snoop web admin port exposed by docker.

    :param collection: the collection name
    :param settings_dir: the directory containing the settings files
    :return: (str, int)
    '''
    with open(os.path.join(settings_dir, docker_collection_file_name)) as collection_file:
        settings = yaml.load(collection_file)
        snoop_image = settings['snoop-worker--' + collection]['image']
        snoop_port = int(settings['snoop--' + collection]['ports'][0].split(sep=':')[0])
        return snoop_image, snoop_port


def write_collections_docker_files(collections, snoop_image=None, profiling_collections=None,
                                   remove_profiling=False, dev_collections=None, remove_dev=False,
                                   index_collections=None, remove_indexing=False):
    '''Generate the collections docker files. Returns the next available port to
    expose postgresl database from docker and the number of dev instances.

    :param collections: the collections name list
    :param snoop_image: the snoop image name
    :param profiling_collections: the collections selected for profiling/no profiling
    :param remove_profiling: if true, remove profiling from collections in profiling_collections
    :param dev_collections: collections selected for dev/no dev
    :param remove_dev: if true, remove dev from collections in dev_collections
    :param index_collections: collections selected for automatic/manual indexing
    :param remove_indexing: if true, remove autoindexing from collections in dev_collections
    :return: (int, int)
    '''
    pg_port = default_pg_port + 1
    dev_instances = 0

    for collection, settings in collections.items():
        validate_collection_data_dir(collection)

        settings_dir = create_settings_dir(collection, ignore_exists=True)
        orig_snoop_image, snoop_port = read_collection_docker_file(collection, settings_dir)
        updated_snoop_image = snoop_image if snoop_image else orig_snoop_image
        if remove_profiling:
            profiling = not collection_selected(collection, profiling_collections) and settings['profiling']
        else:
            profiling = collection_selected(collection, profiling_collections) or settings['profiling']
        if remove_dev:
            for_dev = not collection_selected(collection, dev_collections) and settings['for_dev']
        else:
            for_dev = collection_selected(collection, dev_collections) or settings['for_dev']
        dev_instances += int(for_dev)
        if remove_indexing:
            indexing = not collection_selected(collection, index_collections) and settings['autoindex']
        else:
            indexing = collection_selected(collection, index_collections) or settings['autoindex']

        write_collection_docker_file(collection, updated_snoop_image, settings_dir, snoop_port,
                                     profiling, for_dev, pg_port, indexing)
        pg_port += 1
    return pg_port, dev_instances


def write_global_docker_file(collections, for_dev=False):
    '''Generate the override docker file from collection docker files.

    :param collections: the collections name list
    :param for_dev: if true, will add development settings
    '''
    if len(collections) == 0:
        if os.path.isfile(docker_file_name):
            os.rename(docker_file_name, orig_docker_file_name)
        return

    template_file = docker_file_name if not for_dev else docker_dev_file_name

    with open(new_docker_file_name, 'w') as new_docker_file:
        with open(os.path.join(templates_dir_name, template_file)) as docker_file:
            new_docker_file.write('version: "2"\n\nservices:\n')
            custom_services_file_path = os.path.join(templates_dir_name, custom_services_file_name)
            if os.path.isfile(custom_services_file_path):
                with open(custom_services_file_path) as custom_services_file:
                    new_docker_file.write(custom_services_file.read())
                new_docker_file.write('\n')
            new_docker_file.write(docker_file.read())
            new_docker_file.write('    depends_on:\n      - ')
            snoop_collections = '\n      - '.join(['snoop--' + c for c in collections])
            new_docker_file.write(snoop_collections)
        new_docker_file.write('\n')

        for collection_name in collections:
            new_docker_file.write('\n')
            collection_docker_file_path = os.path.join(settings_dir_name, collection_name,
                                                       docker_collection_file_name)
            with open(collection_docker_file_path) as collection_docker_file:
                new_docker_file.write(collection_docker_file.read())
            new_docker_file.write('\n')

    if os.path.isfile(docker_file_name):
        os.rename(docker_file_name, orig_docker_file_name)
    os.rename(new_docker_file_name, docker_file_name)
