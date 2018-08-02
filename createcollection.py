import argparse
import os.path

from jinja2 import Template
from base64 import b64encode
from src.util import get_collections_data,\
    exit_collection_exists, docker_collection_file_name, settings_dir_name,\
    validate_collections, env_file_name, snoop_settings_file_name, cleanup,\
    generate_docker_file, templates_dir_name, collection_allowed_chars,\
    validate_collection_name


steps_file_name = 'collection%s steps.txt'
collections_dir_name = 'collections'


def validate_collection_data_dir(collection_name):
    data_dir = os.path.join(collections_dir_name, collection_name)
    if not os.path.isdir(data_dir):
        print('Collection %s does not have a data directory (%s)' % (collection_name, data_dir))
        exit(1)

def generate_collection_docker_file(args, last_snoop_port, settings_dir):
    with open(os.path.join(templates_dir_name, docker_collection_file_name)) as docker_template:
        template = Template(docker_template.read())
        collection_settings = template.render(collection_name=args.collection,
                                              snoop_image=args.snoop_image,
                                              snoop_port=last_snoop_port + 1)

    with open(os.path.join(settings_dir, docker_collection_file_name), mode='w') \
            as collection_file:
        collection_file.write(collection_settings)

def generate_env_file(settings_dir):
    with open(os.path.join(templates_dir_name, env_file_name)) as env_template:
        template = Template(env_template.read())
        env_settings = template.render(secret_key=b64encode(os.urandom(100)).decode('utf-8'))

    with open(os.path.join(settings_dir, env_file_name), mode='w') as env_file:
        env_file.write(env_settings)

def generate_python_settings_file(settings_dir):
    with open(os.path.join(templates_dir_name, snoop_settings_file_name)) as settings_template:
        template = Template(settings_template.read())
        snoop_settings = template.render(collection_name=args.collection)

    with open(os.path.join(settings_dir, snoop_settings_file_name), mode='w') as settings_file:
        settings_file.write(snoop_settings)

def write_instructions(args):
    with open(os.path.join(templates_dir_name, steps_file_name % '')) as steps_template:
        template = Template(steps_template.read())
        steps = template.render(collection_name=args.collection)

    collection_steps_file_name = steps_file_name % ' %s' % args.collection
    with open(collection_steps_file_name, mode='w') as steps_file:
        steps_file.write(steps)

    print(open(collection_steps_file_name).read())
    print('\nThe steps above are described in "%s"' % collection_steps_file_name)

def create_settings_dir(args):
    settings_dir = os.path.join(settings_dir_name, args.collection)
    try:
        os.mkdir(settings_dir)
    except FileExistsError:
        exit_collection_exists(args.collection)
    return settings_dir

def get_args():
    parser = argparse.ArgumentParser(description='Create a new collection.')
    parser.add_argument('-c', '--collection', required=True,
                        help='Collection name; allowed characters: ' + collection_allowed_chars)
    parser.add_argument('-s', '--snoop-image', default='liquidinvestigations/hoover-snoop2',
                        help='Snoop docker image')
    args = parser.parse_args()

    validate_collection_name(args.collection)

    return args


if __name__ == '__main__':
    args = get_args()
    collections, last_snoop_port = get_collections_data(args.collection)
    validate_collections(collections)
    validate_collection_data_dir(args.collection)
    settings_dir = create_settings_dir(args)

    collections.append(args.collection)
    collections.sort()
    try:
        generate_collection_docker_file(args, last_snoop_port, settings_dir)
        generate_env_file(settings_dir)
        generate_python_settings_file(settings_dir)
        generate_docker_file(collections)
    except Exception as e:
        print('Error creating collection: %s' % e)
        cleanup(args.collection)
        exit(1)

    write_instructions(args)
