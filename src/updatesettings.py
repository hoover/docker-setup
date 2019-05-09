import argparse

from src.common import validate_collections, get_collections_data, write_global_docker_file, \
    write_collections_docker_files, write_python_settings_files, write_env_files,\
    update_collections_settings, write_collections_settings, default_snoop_image


def get_args():
    parser = argparse.ArgumentParser(description='Update the collections settings with given options.')
    parser.add_argument('-s', '--snoop-image', help='Snoop docker image', nargs='?',
                        const=default_snoop_image)

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

    profiling = parser.add_mutually_exclusive_group()
    profiling.add_argument('-t', '--tracing', action='append', nargs='*',
                           help='Add tracing settings for the given collections. ' +
                                'If no collections were specified the tracing will be enabled for all.')
    profiling.add_argument('-z', '--no-tracing', action='append', nargs='*',
                           help='Remove tracing settings for the given collections. ' +
                                'If no collections were specified the tracing will be disabled for all.')

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
    data = get_collections_data()

    collections = data['collections']
    if len(collections):
        validate_collections(collections)

    collections_names = set(collections.keys())

    indexing, disable_indexing = read_collections_arg(args.autoindex, args.manual_indexing,
                                                      collections_names)
    update_collections_settings(data, {'autoindex': not disable_indexing}, indexing)

    profiling, remove_profiling = read_collections_arg(args.profiling, args.no_profiling,
                                                       collections_names)
    update_collections_settings(data, {'profiling': not remove_profiling}, profiling)

    tracing, disable_tracing = read_collections_arg(args.tracing, args.no_tracing,
                                                    collections_names)
    update_collections_settings(data, {'tracing': not disable_tracing}, tracing)

    for_dev, remove_dev = read_collections_arg(args.dev, args.remove_dev, collections_names)
    update_collections_settings(data, {'for_dev': not remove_dev}, for_dev)

    if args.snoop_image:
        for settings in data['collections'].values():
            settings['image'] = args.snoop_image

    write_env_files(collections)

    write_python_settings_files(collections)
    dev_instances = write_collections_docker_files(collections)
    write_global_docker_file(collections, bool(dev_instances))
    write_collections_settings(collections)

    print('Restart docker-compose:')
    print('  $ docker-compose down && docker-compose up -d')
