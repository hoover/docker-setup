import os.path

from jinja2 import Template
from base64 import b64encode
from src.util import get_args, get_collections_data,\
    exit_collection_exists, docker_collection_file_name, settings_dir_name,\
    validate_collections, env_file_name, snoop_settings_file_name, cleanup,\
    generate_docker_file, templates_dir_name


collections_dir_name = 'collections'


def validate_collection_data_dir(collection_name):
    data_dir = os.path.join(collections_dir_name, collection_name)
    if not os.path.isdir(data_dir):
        print('Collection %s does not have a data directory (%s)' % (collection_name, data_dir))
        exit(1)

def generate_collection_docker_file(args, last_snoop_port):
    with open(os.path.join(templates_dir_name, docker_collection_file_name)) as docker_template:
        template = Template(docker_template.read())
        collection_settings = template.render(collection_name=args.collection,
                                              snoop_port=last_snoop_port + 1)

    with open(os.path.join(collection_settings_dir, docker_collection_file_name), mode='w') \
            as collection_file:
        collection_file.write(collection_settings)

def generate_env_file():
    with open(os.path.join(templates_dir_name, env_file_name)) as env_template:
        template = Template(env_template.read())
        env_settings = template.render(secret_key=b64encode(os.urandom(100)).decode('utf-8'))

    with open(os.path.join(collection_settings_dir, env_file_name), mode='w') as env_file:
        env_file.write(env_settings)

def generate_python_settings_file():
    with open(os.path.join(templates_dir_name, snoop_settings_file_name)) as settings_template:
        template = Template(settings_template.read())
        snoop_settings = template.render(collection_name=args.collection)

    with open(os.path.join(collection_settings_dir, snoop_settings_file_name), mode='w') as settings_file:
        settings_file.write(snoop_settings)


if __name__ == '__main__':
    args = get_args()
    collections, last_snoop_port = get_collections_data(args.collection)
    validate_collections(collections)
    validate_collection_data_dir(args.collection)
    collection_settings_dir = os.path.join(settings_dir_name, args.collection)
    try:
        os.mkdir(collection_settings_dir)
    except FileExistsError:
        exit_collection_exists(args.collection)

    collections.append(args.collection)
    collections.sort()
    try:
        generate_collection_docker_file(args, last_snoop_port)
        generate_env_file()
        generate_python_settings_file()
        generate_docker_file(collections)
    except Exception as e:
        print('Error creating collection: %s' % e)
        cleanup(args.collection)
        exit(1)

    migrate_command = 'docker-compose run --rm snoop--%s ./manage.py migrate' % args.collection
    resetstats_command = 'docker-compose run --rm snoop--%s ./manage.py resetstatsindex' %\
        args.collection
    collection_data_dir = '/opt/hoover/collections/%s/data' % args.collection
    create_command = 'docker-compose run --rm snoop--%s ./manage.py createcollection %s %s' % \
        (args.collection, args.collection, collection_data_dir)
    print('Restart docker-compose and run the following comands:\n$ %s\n$ %s\n$ %s' %
          (migrate_command, resetstats_command, create_command))

    logs_command = 'docker-compose logs -f snoop-worker--%s' % args.collection
    print('Run the following command to view when the indexing was finished:\n$ %s' % logs_command)

    snoop_url = 'http://snoop--%s/collections/%s/json' % (args.collection, args.collection)
    search_command = 'docker-compose run --rm search ./manage.py addcollection %s %s --public' % \
        (args.collection, snoop_url)
    print('Run the following command to add the collection to search (after indexing finished):\n$ %s' %
          search_command)
