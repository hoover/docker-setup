import argparse

from src.common import validate_collections, get_collections_data, write_global_docker_file, \
    write_collections_docker_files, write_python_settings_files


def get_args():
    parser = argparse.ArgumentParser(description='Update the collections settings with given options.')
    parser.add_argument('-s', '--snoop-image', help='Snoop docker image')
    for_dev = parser.add_mutually_exclusive_group()
    for_dev.add_argument('-d', '--dev', action='append', nargs='*',
                         help='Add development settings for the given collections. ' +
                              'If no collections were specified dev settings will be enabled for all.')
    for_dev.add_argument('-r', '--remove-dev', action='append', nargs='*',
                         help='Remove development settings from the given collections. ' +
                              'If no collections were specified dev settings will be disabled for all.')
    profiling = parser.add_mutually_exclusive_group()
    profiling.add_argument('-p', '--profiling', action='append', nargs='*',
                           help='Add profiling settings for the given collections. ' +
                                'If no collections were specified profiling will be enabled for all.')
    profiling.add_argument('-n', '--no-profiling', action='append', nargs='*',
                           help='Remove profiling settings for the given collections. ' +
                                'If no collections were specified profiling will be disabled for all.')
    autoindex = parser.add_mutually_exclusive_group()
    autoindex.add_argument('-a', '--autoindex', action='append', nargs='*',
                           help='Enable automatic indexing for the given collections. ' +
                                'If no collections were specified auto-indexing will be enabled for all.')
    autoindex.add_argument('-m', '--manual-indexing', action='append', nargs='*',
                           help='Enable automatic indexing for the given collections. ' +
                                'If no collections were specified auto-indexing will be disabled for all.')
    return parser.parse_args()


def read_collections_arg(add_list, remove_list, all_collections):
    if add_list:
        validate_collections(add_list[0])
        collections = add_list[0] if add_list[0] else all_collections
        remove = False
    elif remove_list:
        validate_collections(remove_list[0])
        collections = remove_list[0] if remove_list[0] else all_collections
        remove = True
    else:
        collections = None
        remove = False
    return collections, remove


def update_settings(args):
    collections, _, _, _ = get_collections_data()
    if len(collections):
        validate_collections(collections)

    collections_names = set(collections.keys())
    profiling, remove_profiling = read_collections_arg(args.profiling, args.no_profiling,
                                                       collections_names)
    for_dev, remove_dev = read_collections_arg(args.dev, args.remove_dev, collections_names)
    indexing, disable = read_collections_arg(args.autoindex, args.manual_indexing, collections_names)

    write_python_settings_files(collections, profiling, remove_profiling, for_dev, remove_dev)
    _, dev_instances = write_collections_docker_files(collections, args.snoop_image, profiling,
                                                      remove_profiling, for_dev, remove_dev,
                                                      indexing, disable)
    write_global_docker_file(collections, bool(dev_instances))

    print('Restart docker-compose:')
    print('  $ docker-compose down')
    print('  $ docker-compose up -d')
