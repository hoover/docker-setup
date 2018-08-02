import sys
import argparse

from src.util import get_collections_data, validate_collections, cleanup,\
    generate_docker_file, collection_allowed_chars, validate_collection_name
from subprocess import run, STDOUT, PIPE


def get_args():
    parser = argparse.ArgumentParser(description='Remove collection.')
    parser.add_argument('-c', '--collection', required=True,
                        help='Collection name; allowed characters: ' + collection_allowed_chars)
    parser.add_argument('--skip-index', action='store_const', const=True,
                        help='Skip the index removal from search.')
    args = parser.parse_args()

    validate_collection_name(args.collection)

    return args

def remove_index(collection_name):
    docker_args = ['docker-compose', 'run', '--rm', 'snoop--%s' % collection_name, './manage.py',
                   'deletecollection', collection_name]
    process = run(docker_args, stdout=sys.stdout, stderr=sys.stderr)
    if process.returncode != 0:
        print('Error removing %s index' % collection_name)
        print('Use --skip-index if you only want to remove collection settings')
        exit(1)


if __name__ == '__main__':
    args = get_args()
    collections, last_snoop_port = get_collections_data()
    if args.collection not in collections:
        print('Invalid collection %s' % args.collection)
        exit(1)

    validate_collections(collections)

    if not args.skip_index:
        remove_index(args.collection)
    collections.remove(args.collection)
    generate_docker_file(collections)

    cleanup(args.collection, keep_new_docker_file=True)

    print('Restart docker-compose')
