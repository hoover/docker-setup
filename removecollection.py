from src.util import get_args, get_collections_data, validate_collections, cleanup,\
    generate_docker_file


if __name__ == '__main__':
    args = get_args()
    collections, last_snoop_port = get_collections_data()
    if args.collection not in collections:
        print('Invalid collection %s' % args.collection)
        exit(1)

    validate_collections(collections)

    collections.remove(args.collection)
    generate_docker_file(collections)

    cleanup(args.collection, keep_new_docker_file=True)

    print('Restart docker-compose')
