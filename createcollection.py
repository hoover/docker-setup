import argparse
from base64 import b64encode
import os.path

from jinja2 import Template

from src.util import get_collections_data, \
    validate_collections, env_file_name, snoop_settings_file_name, cleanup, \
    generate_docker_file, templates_dir_name, collection_allowed_chars, \
    validate_collection_name, \
    validate_collection_data_dir, create_settings_dir, \
    generate_collection_docker_file


steps_file_name = 'collection%s steps.txt'


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

def get_args():
    parser = argparse.ArgumentParser(description='Create a new collection.')
    parser.add_argument('-c', '--collection', required=True,
                        help='Collection name; allowed characters: ' + collection_allowed_chars)
    parser.add_argument('-s', '--snoop-image', default='liquidinvestigations/hoover-snoop2',
                        help='Snoop docker image')
    parser.add_argument('-d', '--dev', action='store_const', const=True, default=False,
                        help='Add development settings to the docker file')
    args = parser.parse_args()

    validate_collection_name(args.collection)

    return args


if __name__ == '__main__':
    args = get_args()

    collections, snoop_port, pg_port = get_collections_data(args.collection, args.dev)
    if len(collections):
        validate_collections(collections)
    validate_collection_data_dir(args.collection)
    settings_dir = create_settings_dir(args.collection)

    collections.append(args.collection)
    collections.sort()
    try:
        generate_collection_docker_file(args.collection, args.snoop_image, settings_dir,
                                        snoop_port, args.dev, pg_port)
        generate_env_file(settings_dir)
        generate_python_settings_file(settings_dir)
        generate_docker_file(collections, args.dev)
    except Exception as e:
        print('Error creating collection: %s' % e)
        cleanup(args.collection)
        exit(1)

    write_instructions(args)
