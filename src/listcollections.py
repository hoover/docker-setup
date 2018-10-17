import argparse
import json

from src.common import get_collections_data, create_settings_dir, read_env_file, \
    DOCKER_HOOVER_SNOOP_STATS


def get_args():
    parser = argparse.ArgumentParser(description='List collections.')
    parser.add_argument('-j', '--json', action='store_const', const=True, default=False,
                        help='Output in json format.')
    return parser.parse_args()


def print_collections(collections):
    index = 1
    for collection, settings in collections.items():
        settings_dir = create_settings_dir(collection, ignore_exists=True)
        env = read_env_file(settings_dir)

        print('%d. %s' % (index, collection))
        print('  - profiling: %s' % settings['profiling'])
        print('  - development: %s' % settings['for_dev'])
        print('  - auto-indexing: %s' % settings['autoindex'])
        print('  - image: %s' % settings['image'])
        print('  - stats: %s' % ('enabled' if env.get(DOCKER_HOOVER_SNOOP_STATS, False) else 'disabled'))
        index += 1


def list_collections(args):
    collections = get_collections_data()['collections']
    if args.json:
        print(json.dumps(collections, indent=4))
    else:
        print_collections(collections)
