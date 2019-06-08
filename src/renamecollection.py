import argparse
import shutil
from os.path import join, dirname
from time import strftime, gmtime

from src.common import get_collections_data, validate_collections, \
    write_global_docker_file, collection_allowed_chars, validate_collection_name, \
    InvalidCollectionName, exit_msg, write_collections_settings, collections_path, volumes_path, blobs_path, \
    write_collection_docker_file, create_settings_dir, write_env_file, write_python_settings_file
from src.process import ensure_docker_setup_stopped, run, ensure_docker_running, exit_on_exception


def get_args():
    parser = argparse.ArgumentParser(description='Remove collection.')
    parser.add_argument('-c', '--collection', required=True,
                        help='Collection name; allowed characters: ' + collection_allowed_chars)
    parser.add_argument('-n', '--new-name', required=True,
                        help='New collection name; allowed characters: ' + collection_allowed_chars)
    args = parser.parse_args()

    return args


def rename_multiple(dirs):
    for src, dst in dirs:
        if not src.is_dir() and not src.is_file():
            raise RuntimeError(f'Directory/file {src} does not exist.')
        if dst.is_dir() or dst.is_file():
            raise RuntimeError(f'Directory/file {dst} already exists.')

    for src, dst in dirs:
        src.rename(dst)


@exit_on_exception
def export_index(collection):
    ensure_docker_running()

    export_file_name = strftime('%Y-%m-%d_%H-%M-%S.tar', gmtime())
    export_file_path = volumes_path / 'exports' / collection / export_file_name
    print(f'Exporting index for {collection} to {export_file_path}')
    print(run(f'docker-compose run --rm snoop--{collection} ' +
              f'./manage.py exportindex {export_file_name}'))

    return (export_file_name, export_file_path)


@exit_on_exception
def import_index(old_index, collection, import_file_name):
    ensure_docker_running(collection=collection)

    import_file_path = join(volumes_path, collection, import_file_name)
    print(f'Importing index for {collection} from {import_file_path}')
    print(run(f'docker-compose run --rm snoop--{collection} ' +
              f'./manage.py importindex -i {old_index} {import_file_name}'))


@exit_on_exception
def docker_remove_index(collection):
    ensure_docker_running('--remove-orphans')

    print(f'Removing collection "{collection}" index...')
    print(run(f'docker-compose run --rm search ./manage.py removeindex {collection}'))


@exit_on_exception
def docker_rename_collection(args):
    ensure_docker_running('--remove-orphans')

    print(f'Renaming collection "{args.collection}" to {args.new_name}...')
    print(run('docker-compose run --rm search ./manage.py renamecollection ' +
              f'{args.collection} {args.new_name}'))


def rename_collection(args):
    data = get_collections_data()
    try:
        validate_collection_name(args.collection, data['collections'], new=False)
        validate_collection_name(args.new_name, data['collections'], new=True)
    except InvalidCollectionName as e:
        exit_msg(str(e))

    validate_collections(data['collections'])

    index_file_name, index_file_path = export_index(args.collection)
    renamed_index_file_path = index_file_path.parent.parent / args.new_name / index_file_name
    docker_remove_index(args.collection)

    ensure_docker_setup_stopped()

    paths_to_rename = [
        (collections_path / args.collection, collections_path / args.new_name),
        (volumes_path / f'snoop-pg--{args.collection}', volumes_path / f'snoop-pg--{args.new_name}'),
        (blobs_path / args.collection, blobs_path / args.new_name),
        (index_file_path, renamed_index_file_path)
    ]
    rename_multiple(paths_to_rename)

    data['collections'][args.new_name] = data['collections'][args.collection]
    del data['collections'][args.collection]

    settings_dir = create_settings_dir(args.new_name)
    write_collections_settings(data['collections'])
    write_env_file(settings_dir, data['collections'][args.new_name])
    write_python_settings_file(args.new_name, settings_dir, data['collections'][args.new_name])
    shutil.rmtree(join(dirname(settings_dir), args.collection))

    write_collection_docker_file(args.new_name, settings_dir, data['collections'][args.new_name])
    write_global_docker_file(data['collections'], bool(data['dev_instances']))

    import_index(args.collection.lower(), args.new_name, index_file_name)

    docker_rename_collection(args)
