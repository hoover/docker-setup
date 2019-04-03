import argparse
from collections import OrderedDict
import os.path

from jinja2 import Template

from src.common import get_collections_data, validate_collections, cleanup, \
    write_global_docker_file, templates_dir_name, instructions_dir_name, \
    collection_allowed_chars, validate_collection_name, validate_collection_data_dir, \
    create_settings_dir, write_collection_docker_file, volumes_dir_name, \
    write_python_settings_file, default_snoop_image, write_env_file, \
    InvalidCollectionName, exit_msg, init_collection_settings,\
    write_collections_settings

steps_file_name = 'collection-%s-steps.txt'
steps_script_name = 'init-%s.sh'


def write_instructions(args):
    with open(os.path.join(templates_dir_name, 'collection-steps.txt')) as steps_template:
        template = Template(steps_template.read())
        steps = template.render(collection_name=args.collection,
                                collection_index=str.lower(args.collection))

    collection_steps_file_name = os.path.join(instructions_dir_name, steps_file_name % '%s' % args.collection)
    with open(collection_steps_file_name, mode='w') as steps_file:
        steps_file.write(steps)

    print(open(collection_steps_file_name).read())
    print('\nThe steps above are described in "%s" OR' % collection_steps_file_name)

    with open(os.path.join(templates_dir_name, 'collection-steps.sh')) as script_template:
        template = Template(script_template.read())
        script = template.render(collection_name=args.collection, collection_index=str.lower(args.collection))

    collection_steps_script_name = os.path.join(instructions_dir_name,
                                                steps_script_name % '%s' % args.collection)
    with open(collection_steps_script_name, mode='w') as script_file:
        script_file.write(script)
        os.chmod(collection_steps_script_name, 0o750)

    print('\nExecute script ./%s' % collection_steps_script_name)


def get_args():
    parser = argparse.ArgumentParser(description='Create a collection.')
    parser.add_argument('-c', '--collection', required=True,
                        help='Collection name; allowed characters: ' + collection_allowed_chars)
    parser.add_argument('-s', '--snoop-image', default=default_snoop_image,
                        help='Snoop docker image')
    parser.add_argument('-d', '--dev', action='store_const', const=True, default=False,
                        help='Add development settings to the docker file')
    parser.add_argument('-p', '--profiling', action='store_const', const=True, default=False,
                        help='Add profiling settings for the new collection.')
    parser.add_argument('-t', '--tracing', action='store_const', const=True, default=False,
                        help='Add tracing settings for the new collection.')
    parser.add_argument('-m', '--manual-indexing', action='store_const', const=True, default=False,
                        help='Do not add the option to start indexing automatically.')
    args = parser.parse_args()

    return args


def create_pg_dir(collection):
    pg_dir = os.path.join(volumes_dir_name, 'snoop-pg--%s' % collection)
    if not os.path.isdir(pg_dir):
        os.mkdir(pg_dir)


def create_collection(args):
    data = get_collections_data()
    try:
        validate_collection_name(args.collection, data['collections'])
    except InvalidCollectionName as e:
        exit_msg(str(e))
    if len(data['collections']):
        validate_collections(data['collections'])
    validate_collection_data_dir(args.collection)

    try:
        init_collection_settings(data['collections'], args, data)
        create_pg_dir(args.collection)
        settings_dir = create_settings_dir(args.collection)

        ordered_collections = OrderedDict(sorted(data['collections'].items(), key=lambda t: t[0]))

        write_collection_docker_file(args.collection, settings_dir,
                                     data['collections'][args.collection])
        write_env_file(settings_dir, data['collections'][args.collection])
        write_python_settings_file(args.collection, settings_dir, data['collections'][args.collection])
        write_global_docker_file(ordered_collections, args.dev or bool(data['dev_instances']))
        write_collections_settings(data)
    except Exception as e:
        print('Error creating collection: %s' % e)
        cleanup(args.collection)
        raise

    write_instructions(args)
