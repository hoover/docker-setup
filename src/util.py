import re
import yaml
import os

from shutil import rmtree
from jinja2 import Template


collection_allowed_chars = 'a-z, A-Z, 0-9, _'
start_snoop_port = 45025
settings_dir_name = 'settings'
templates_dir_name = 'templates'
docker_file_name = 'docker-compose.yml'
orig_docker_file_name = 'docker-compose-orig.yml'
new_docker_file_name = 'docker-compose-new.yml'
docker_collection_file_name = 'docker-collection.yml'
snoop_settings_file_name = 'snoop-settings.py'
env_file_name = 'snoop.env'


def exit_collection_exists(collection):
    print('Collection %s already exists!' % collection)
    exit(1)

def validate_collection_name(collection_name):
    if re.search('\W+', collection_name):
        print('Invalid collection name ' + collection_name)
        print('Allowed characters: ' + collection_allowed_chars)
        exit(1)

def get_collections_data(new_collection=None):
    collections = []
    last_snoop_port = start_snoop_port
    with open(docker_file_name) as collections_settings:
        collections_settings = yaml.load(collections_settings)
        for service, settings in collections_settings['services'].items():
            if service.startswith('snoop--'):
                collection_name = service[len('snoop--'):]
                collections.append(collection_name)

                if new_collection and collection_name == new_collection:
                    exit_collection_exists(new_collection)
                port = int(settings['ports'][0].split(sep=':')[0])
                if port > last_snoop_port:
                    last_snoop_port = port

    return collections, last_snoop_port

def validate_collections(collections):
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
    if errors:
        print('\n'.join(errors))
        exit(1)

def cleanup(collection_name, keep_new_docker_file=False):
    settings_dir = os.path.join(settings_dir_name, collection_name)
    if os.path.isdir(settings_dir):
        rmtree(settings_dir, ignore_errors=True)
    if not keep_new_docker_file and os.path.isfile(orig_docker_file_name):
        os.rename(orig_docker_file_name, docker_file_name)

def generate_docker_file(collections):
    with open(new_docker_file_name, 'w') as new_docker_file:
        with open(os.path.join(templates_dir_name, docker_file_name)) as docker_file:
            template = Template(docker_file.read())
            snoop_collections = '\n      - '.join(['snoop--' + c for c in collections])
            new_docker_file.write(template.render(snoop_collections=snoop_collections))
        new_docker_file.write('\n')

        for collection_name in collections:
            collection_docker_file_path = os.path.join(settings_dir_name, collection_name,
                                                       docker_collection_file_name)
            with open(collection_docker_file_path) as collection_docker_file:
                new_docker_file.write(collection_docker_file.read())
            new_docker_file.write('\n\n')

    if os.path.isfile(docker_file_name):
        os.rename(docker_file_name, orig_docker_file_name)
    os.rename(new_docker_file_name, docker_file_name)
