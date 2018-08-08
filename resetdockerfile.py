import argparse

from src.util import validate_collections, \
    get_collections_data, generate_docker_file, \
    regenerate_collections_docker_files, cleanup


def get_args():
    parser = argparse.ArgumentParser(description='Regenerates the docker collections file.')
    parser.add_argument('-s', '--snoop-image', default='liquidinvestigations/hoover-snoop2',
                        help='Snoop docker image')
    parser.add_argument('-d', '--dev', action='store_const', const=True,
                        help='Add development settings to the docker file')
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()

    collections, _, _ = get_collections_data()
    if len(collections):
        validate_collections(collections)
    collections.sort()

    try:
        regenerate_collections_docker_files(collections, args.snoop_image, args.dev)
        generate_docker_file(collections, args.dev)
    except Exception as e:
        print('Error creating collection: %s' % e)
        cleanup(args.collection)
        exit(1)

    print('Restart docker-compose:')
    print('  $ docker-compose down')
    print('  $ docker-compose up -d')
