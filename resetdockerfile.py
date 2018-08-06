import argparse
import os

import yaml

from src.util import validate_collections, \
    get_collections_data, generate_docker_file, validate_collection_data_dir, \
    cleanup, create_settings_dir, docker_collection_file_name,\
    generate_collection_docker_file, default_pg_port


def get_args():
    parser = argparse.ArgumentParser(description='Regenerates the docker collections file.')
    parser.add_argument('-s', '--snoop-image', default='liquidinvestigations/hoover-snoop2',
                        help='Snoop docker image')
    parser.add_argument('-d', '--dev', action='store_const', const=True,
                        help='Add development settings to the docker file')
    args = parser.parse_args()

    return args

def read_collection_docker_file(collection, settings_dir):
    with open(os.path.join(settings_dir, docker_collection_file_name)) as collection_file:
        settings = yaml.load(collection_file)
        snoop_image = settings['snoop-worker--' + collection]['image']
        snoop_port = int(settings['snoop--' + collection]['ports'][0].split(sep=':')[0])
        return snoop_image, snoop_port


if __name__ == '__main__':
    args = get_args()

    collections, last_snoop_port, last_pg_port = get_collections_data(for_dev = args.dev)
    if len(collections):
        validate_collections(collections)
    collections.sort()

    pg_port = default_pg_port + 1
    for collection in collections:
        validate_collection_data_dir(collection)
        settings_dir = create_settings_dir(collection, ignore_exists=True)
        snoop_image, snoop_port = read_collection_docker_file(collection, settings_dir)
        snoop_image = args.snoop_image if args.snoop_image else snoop_image
        generate_collection_docker_file(collection, snoop_image, settings_dir, snoop_port,
                                        args.dev, pg_port)
        pg_port += 1

    try:
        generate_docker_file(collections, args.dev)
    except Exception as e:
        print('Error creating collection: %s' % e)
        cleanup(args.collection)
        exit(1)
