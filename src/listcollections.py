import argparse
from copy import deepcopy
import json

from src.common import get_collections_data


def get_args():
    parser = argparse.ArgumentParser(description='List collections.')
    parser.add_argument('-j', '--json', action='store_const', const=True, default=False,
                        help='Output in json format.')
    return parser.parse_args()


def print_collections(collections):
    index = 1
    for collection, settings in collections.items():
        print('%d. %s' % (index, collection))
        print('  - auto-indexing: %s' % settings.get('autoindex', False))
        if settings.get('autoindex') and 'flower_url' in settings:
            print('  - flower URL: %s' % settings['flower_url'])
        print('  - image: %s' % settings['image'])
        print('  - snoop admin URL: %s' % settings['snoop_url'])
        print('  - profiling: %s' % settings.get('profiling', False))
        print('  - tracing: %s' % settings.get('tracing', False))
        print('  - development: %s' % settings.get('for_dev', False))
        index += 1


def prepare_data(collections):
    data = deepcopy(collections)
    for settings in data.values():
        if 'env' in settings:
            del settings['env']
        settings['snoop_url'] = 'http://localhost:%d' % settings['snoop_port']
        if settings.get('autoindex') and settings.get('flower_port'):
            settings['flower_url'] = 'http://localhost:%d' % settings['flower_port']
    return data


def list_collections(args):
    collections = prepare_data(get_collections_data()['collections'])
    if args.json:
        print(json.dumps(collections, indent=4))
    else:
        print_collections(collections)
