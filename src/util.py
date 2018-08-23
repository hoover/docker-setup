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
docker_file_name = 'docker-compose.override.yml'
docker_dev_file_name = 'docker-compose.override-dev.yml'
orig_docker_file_name = 'docker-compose.override-orig.yml'
new_docker_file_name = 'docker-compose.override-new.yml'
docker_collection_file_name = 'docker-collection.yml'
snoop_settings_file_name = 'snoop-settings.py'
snoop_settings_profiling_file_name = 'snoop-settings-profiling.py'
snoop_settings_dev_file_name = 'snoop-settings-dev.py'
env_file_name = 'snoop.env'
default_pg_port = 5432


def exit_collection_exists(collection):
    print('Collection %s already exists!' % collection)
    exit(1)


def exit_invalid_collection(collection):
    print('Collection %s does not exist!' % collection)
    exit(1)


def validate_collection_name(collection_name):
    if re.search('\W+', collection_name):
        print('Invalid collection name ' + collection_name)
        print('Allowed characters: ' + collection_allowed_chars)
        exit(1)


def validate_collection_data_dir(collection_name):
    data_dir = os.path.join(collections_dir_name, collection_name)
    if not os.path.isdir(data_dir):
        print('Collection %s does not have a data directory (%s)' % (collection_name, data_dir))
        exit(1)


def get_collections_data(new_collection=None):
    if not os.path.isfile(docker_file_name):
        return [], start_snoop_port, False

    collections = []
    last_snoop_port = start_snoop_port - 1
    for_dev = False
    exists = False

    with open(docker_file_name) as collections_file:
        collections_settings = yaml.load(collections_file)
        for service, settings in collections_settings['services'].items():
            if service in ['snoop-rabbitmq', 'snoop-tika', 'search-pg', 'search-es']:
                for_dev = True
            if service.startswith('snoop--'):
                collection_name = service[len('snoop--'):]
                collections.append(collection_name)

                if new_collection and collection_name.lower() == new_collection.lower():
                    exit_collection_exists(new_collection)
                exists = exists or (new_collection and collection_name.lower() == new_collection.lower())

                port = int(settings['ports'][0].split(sep=':')[0])
                if port > last_snoop_port:
                    last_snoop_port = port

    return collections, last_snoop_port + 1, for_dev


def validate_collections(collections, exit_on_errors=True):
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
    if collections is None:
        return False
    if len(collections):
        collections = collections[0]
    if len(collections) == 0:
        return True
    return reduce(lambda found, elem: found or collection.lower() == elem.lower(),
                  collections, False)


def cleanup(collection_name, keep_new_docker_file=False):
    settings_dir = os.path.join(settings_dir_name, collection_name)
    if os.path.isdir(settings_dir):
        rmtree(settings_dir, ignore_errors=True)
    if not keep_new_docker_file and os.path.isfile(orig_docker_file_name):
        os.rename(orig_docker_file_name, docker_file_name)


def create_settings_dir(collection, ignore_exists=False):
    '''Create the directory for settings files. Returns the settings directory path.

    :param collection: the collection name
    :param ignore_exists: if true do not exit when the directory already exists
    :return str
    '''
    settings_dir = os.path.join(settings_dir_name, collection)
    try:
        os.mkdir(settings_dir)
    except FileExistsError:
        if not ignore_exists:
            exit_collection_exists(collection)
    return settings_dir


def generate_python_settings_file(collection, settings_dir, profiling=False, for_dev=False):
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


def regenerate_settings_files(collections, profiling_collections=None, for_dev=False):
    '''Re-generate the collections settings files.

    :param collections: the collections name list
    :param profiling_collections: the collections selected for profiling
    :param for_dev: if true, will add development settings
    '''
    for collection in collections:
        settings_dir = create_settings_dir(collection, ignore_exists=True)
        selected = collection_selected(collection, profiling_collections)
        generate_python_settings_file(collection, settings_dir,
                                      profiling=selected, for_dev=for_dev)


def generate_collection_docker_file(collection, snoop_image, settings_dir, snoop_port,
                                    profiling=False, for_dev=False, pg_port=None):
    '''Generate the corresponding collection docker file using the docker template.

    :param collection: the collection name
    :param snoop_image: the snoop image name
    :param settings_dir: the directory containing the settings files
    :param snoop_port: the snoop web admin port exposed by docker
    :param for_dev: if true, will add development settings
    :param pg_port: the port on which the postgresql database is exposed if for_dev enabled
    '''
    dev_volumes = '\n      - ../snoop2:/opt/hoover/snoop:cached' if for_dev else ''
    pg_port = pg_port if pg_port else default_pg_port + 1
    dev_ports = '    ports:\n      - "%d:%d"\n' % (pg_port, default_pg_port) if for_dev else ''
    snoop_port = snoop_port if snoop_port else start_snoop_port
    profiling_volumes = ''
    if profiling:
        profiling_volumes = '\n      - ./profiles:/opt/hoover/snoop/profiles' + \
                            '\n      - ./settings/urls.py:/opt/hoover/snoop/snoop/urls.py'

    with open(os.path.join(templates_dir_name, docker_collection_file_name)) as docker_template:
        template = Template(docker_template.read())
        collection_settings = template.render(collection_name=collection,
                                              snoop_image=snoop_image,
                                              snoop_port=snoop_port,
                                              profiling_volumes=profiling_volumes,
                                              dev_volumes=dev_volumes,
                                              dev_ports=dev_ports)

    with open(os.path.join(settings_dir, docker_collection_file_name), mode='w') \
            as collection_file:
        collection_file.write(collection_settings)


def read_collection_docker_file(collection, settings_dir):
    '''Read the docker file correspoding to the given collection. Returns the coolection
    snoop image and the snoop web admin port exposed by docker.

    :param collection: the collection name
    :param settings_dir: the directory containing the settings files
    :return: snoop_image, snoop_port (tuple)
    '''
    with open(os.path.join(settings_dir, docker_collection_file_name)) as collection_file:
        settings = yaml.load(collection_file)
        snoop_image = settings['snoop-worker--' + collection]['image']
        snoop_port = int(settings['snoop--' + collection]['ports'][0].split(sep=':')[0])
        return snoop_image, snoop_port


def regenerate_collections_docker_files(collections, snoop_image=None, profiling=None, for_dev=False):
    '''Re-generate the collections docker files. Returns the next available port to
    expose postgresl database from docker.

    :param collections: the collections name list
    :param snoop_image: the snoop image name
    :param profiling: a list of collections selected for profiling
    :param for_dev: if true, will add development settings
    :return int
    '''
    pg_port = default_pg_port + 1
    for collection in collections:
        validate_collection_data_dir(collection)

        settings_dir = create_settings_dir(collection, ignore_exists=True)
        orig_snoop_image, snoop_port = read_collection_docker_file(collection, settings_dir)
        snoop_image = snoop_image if snoop_image else orig_snoop_image
        profile = collection_selected(collection, profiling)

        generate_collection_docker_file(collection, snoop_image, settings_dir, snoop_port,
                                        profile, for_dev, pg_port)
        pg_port += 1
    return pg_port


def generate_docker_file(collections, for_dev=False):
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
