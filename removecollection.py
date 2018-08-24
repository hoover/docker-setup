import argparse
import os
from shutil import rmtree
from subprocess import run
import sys

from src.util import get_collections_data, validate_collections, cleanup, \
    generate_docker_file, collection_allowed_chars, validate_collection_name, \
    volumes_dir_name, blobs_dir_name


def get_args():
    parser = argparse.ArgumentParser(description='Remove collection.')
    parser.add_argument('-c', '--collection', required=True,
                        help='Collection name; allowed characters: ' + collection_allowed_chars)
    parser.add_argument('--skip-index', action='store_const', const=True,
                        help='Skip the index removal from search.')
    parser.add_argument('-b', '--remove-blobs', action='store_const', const=True, default=False,
                        help='Remove blobs')
    parser.add_argument('-y', '--yes', action='store_const', const=True, default=False,
                        help='Force yes answer to all interactive user inputs.')
    args = parser.parse_args()

    validate_collection_name(args.collection)

    return args


def remove_pg_dir(collection):
    pg_dir = os.path.join(volumes_dir_name, 'snoop-pg--%s' % collection)
    if os.path.isdir(pg_dir):
        rmtree(pg_dir)


def remove_index(collection_name):
    docker_args = ['docker-compose', 'run', '--rm', 'snoop--%s' % collection_name, './manage.py',
                   'deletecollection', collection_name]
    process = run(docker_args, stdout=sys.stdout, stderr=sys.stderr)
    if process.returncode != 0:
        print('Error removing %s index' % collection_name)
        print('Use --skip-index if you only want to remove collection settings')
        exit(1)


def remove_blobs(collection_name, force_yes=False):
    blobs_dir = os.path.join(blobs_dir_name, collection_name)
    if os.path.isdir(blobs_dir):
        if not force_yes:
            while True:
                option = input('Please confirm the deletion of blobs (yes/no): ')
                if option.lower() not in ['yes', 'no']:
                    print('Invalid option "%s"' % option)
                    continue
                break
            if option.lower() == 'no':
                return
        rmtree(blobs_dir)


if __name__ == '__main__':
    args = get_args()
    collections, _, for_dev = get_collections_data()
    if args.collection not in collections:
        print('Invalid collection %s' % args.collection)
        exit(1)

    validate_collections(collections, exit_on_errors=False)

    if not args.skip_index:
        remove_index(args.collection)
    collections.remove(args.collection)
    generate_docker_file(collections, for_dev)

    cleanup(args.collection)
    remove_pg_dir(args.collection)
    if args.remove_blobs:
        remove_blobs(args.collection, args.yes)

    print('Restart docker-compose:')
    print('  $ docker-compose down')
    print('  $ docker-compose up -d')
