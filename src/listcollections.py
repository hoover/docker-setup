import argparse
from copy import deepcopy
import json

from src.common import get_collections_data, DOCKER_HOOVER_SNOOP_STATS


def get_args():
    parser = argparse.ArgumentParser(description='List collections.')
    parser.add_argument('-j', '--json', action='store_const', const=True, default=False,
                        help='Output in json format.')
    return parser.parse_args()


def print_collections(collections):
    index = 1
    for collection, settings in collections.items():
        print('%d. %s' % (index, collection))
        print('  - profiling: %s' % settings['profiling'])
        print('  - development: %s' % settings['for_dev'])
        print('  - auto-indexing: %s' % settings['autoindex'])
        print('  - image: %s' % settings['image'])
        print('  - stats: %s' % settings['stats'])
        print('  - snoop admin URL: %s' % settings['snoop_url'])
        if 'flower_url' in settings:
            print('  - flower URL: %s' % settings['flower_url'])
        index += 1


def prepare_data(collections):
    data = deepcopy(collections)
    for settings in data.values():
        settings['stats'] = 'enabled' if settings['env'].get(DOCKER_HOOVER_SNOOP_STATS, False) \
            else 'disabled'
        del settings['env']
        settings['snoop_url'] = 'http://localhost:%d' % settings['snoop_port']
        if 'flower_port' in settings:
            settings['flower_url'] = 'http://localhost:%d' % settings['flower_port']
    return data


def list_collections(args):
    collections = prepare_data(get_collections_data()['collections'])
    if args.json:
        print(json.dumps(collections, indent=4))
    else:
        print_collections(collections)
