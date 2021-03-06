from collections import OrderedDict
from contextlib import contextmanager
import os
from pathlib import Path
import re
from shutil import copytree

import pytest
import yaml

from src.common import get_collections_data, write_python_settings_file, \
    write_collection_docker_file, docker_collection_file_name, \
    write_global_docker_file, read_env_file, write_env_file, \
    InvalidCollectionName, validate_collection_name, \
    write_collections_docker_files, read_collection_docker_file, \
    settings_dir_name, get_collections_data_old
import src.common as c


@pytest.fixture
def data_dir_path():
    return Path(__file__).absolute().parent / 'data'


@pytest.fixture
def templates_dir_path():
    return Path(__file__).absolute().parent.parent / 'templates'


@contextmanager
def chdir(new_path):
    currdir = os.getcwd()
    os.chdir(new_path)
    yield
    os.chdir(currdir)


def test_validate_collection_name():
    with pytest.raises(InvalidCollectionName):
        validate_collection_name(None)
    with pytest.raises(InvalidCollectionName):
        validate_collection_name('')
    for char in "./\\()\"':,.;<>~!@#$%^&*|+=[]{}`~?-_":
        with pytest.raises(InvalidCollectionName):
            validate_collection_name('aaa%s' % char)
    validate_collection_name('Aa0')


def test_get_collections_data_old(monkeypatch, data_dir_path):
    env = {
        c.DOCKER_HOOVER_SNOOP_SECRET_KEY: 'secret-key===',
        c.DOCKER_HOOVER_SNOOP_DEBUG: False,
        c.DOCKER_HOOVER_SNOOP_BASE_URL: 'http://localhost'
    }

    monkeypatch.setattr(c, 'docker_file_name', str(data_dir_path / 'docker-compose-clean.yml'))
    monkeypatch.setattr(c, 'settings_dir_name', str(data_dir_path))
    monkeypatch.setattr(c, 'get_settings_dir', lambda _: c.settings_dir_name)
    data = get_collections_data_old()
    assert data['collections'] == OrderedDict((
        ('testdata1', {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45025, 'flower_port': 15555}),
        ('testdata2', {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45026, 'flower_port': 15556})))
    assert data['snoop_port'] == 45027
    assert data['flower_port'] == 15557
    assert data['pg_port'] == 5433
    assert data['dev_instances'] == 0

    c.docker_file_name = str(data_dir_path / 'docker-compose-profiling.yml')
    data = get_collections_data_old()
    assert data['collections'] == OrderedDict((
        ('testdata1', {'profiling': True, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45025}),
        ('testdata2', {'profiling': True, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45026})))
    assert data['snoop_port'] == 45027
    assert data['flower_port'] == 15557
    assert data['pg_port'] == 5433
    assert data['dev_instances'] == 0

    monkeypatch.setattr(c, 'docker_file_name', str(data_dir_path / 'docker-compose-dev.yml'))
    data = get_collections_data_old()
    assert data['collections'] == OrderedDict((
        ('testdata1', {'profiling': False, 'for_dev': True, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45025}),
        ('testdata2', {'profiling': False, 'for_dev': True, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45026})))
    assert data['snoop_port'] == 45027
    assert data['flower_port'] == 15557
    assert data['pg_port'] == 5435
    assert data['dev_instances'] == 2


def test_get_collections_data(monkeypatch, data_dir_path):
    env = {
        c.DOCKER_HOOVER_SNOOP_SECRET_KEY: 'secret-key===',
        c.DOCKER_HOOVER_SNOOP_DEBUG: False,
        c.DOCKER_HOOVER_SNOOP_BASE_URL: 'http://localhost'
    }

    monkeypatch.setattr(c, 'settings_dir_name', str(data_dir_path))
    monkeypatch.setattr(c, 'get_settings_dir', lambda _: c.settings_dir_name)
    data = get_collections_data()
    assert data['collections'] == OrderedDict((
        ('testdata1', {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45025, 'flower_port': 15555, 'tracing': False,
                       'pg_port': None}),
        ('testdata2', {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45026, 'flower_port': 15556, 'tracing': False,
                       'pg_port': None})))
    assert data['snoop_port'] == 45027
    assert data['flower_port'] == 15557
    assert data['pg_port'] == 5433
    assert data['dev_instances'] == 0


def test_write_python_settings_file(tmpdir):
    collection = 'testdata'

    write_python_settings_file(collection, str(tmpdir), {'profiling': False, 'for_dev': False})
    with open(str(tmpdir / 'snoop-settings.py')) as settings_file:
        settings = settings_file.read()
        assert 'PROFILING_ENABLED' not in settings
        assert 'REMOTE_DEBUG_ENABLED' not in settings
        found = re.search('TASK_PREFIX = \'(\w+)\'', settings)
        assert found and found.group(1) == collection

    write_python_settings_file(collection, str(tmpdir), {'profiling': True, 'for_dev': False})
    with open(str(tmpdir / 'snoop-settings.py')) as settings_file:
        settings = settings_file.read()
        assert 'PROFILING_ENABLED' in settings
        assert 'REMOTE_DEBUG_ENABLED' not in settings

    write_python_settings_file(collection, str(tmpdir), {'profiling': False, 'for_dev': True})
    with open(str(tmpdir / 'snoop-settings.py')) as settings_file:
        settings = settings_file.read()
        assert 'PROFILING_ENABLED' not in settings
        assert 'REMOTE_DEBUG_ENABLED' in settings


def test_write_collection_docker_file(data_dir_path, tmpdir):
    collection = 'testdata'
    snoop_image = 'snoop_image'
    tmpdir_path = str(tmpdir)

    write_collection_docker_file(collection, tmpdir_path,
                                 {'image': snoop_image, 'autoindex': True, 'snoop_port': 45025,
                                  'flower_port': 15555})
    with open(os.path.join(tmpdir_path, docker_collection_file_name)) as collection_file, \
            open(str(data_dir_path / 'docker-collection-clean.yml')) as test_file:
        collection_settings = yaml.load(collection_file, Loader=yaml.FullLoader)
        test_settings = yaml.load(test_file, Loader=yaml.FullLoader)
        assert collection_settings == test_settings

    write_collection_docker_file(collection, tmpdir_path,
                                 {'image': snoop_image, 'autoindex': True, 'snoop_port': 45025,
                                  'profiling': True})
    with open(os.path.join(tmpdir_path, docker_collection_file_name)) as collection_file, \
            open(str(data_dir_path / 'docker-collection-profiling.yml')) as test_file:
        collection_settings = yaml.load(collection_file, Loader=yaml.FullLoader)
        test_settings = yaml.load(test_file, Loader=yaml.FullLoader)
        assert collection_settings == test_settings

    write_collection_docker_file(collection, tmpdir_path,
                                 {'image': snoop_image, 'autoindex': True, 'snoop_port': 45025,
                                  'for_dev': True, 'pg_port': 5433})
    with open(os.path.join(tmpdir_path, docker_collection_file_name)) as collection_file, \
            open(str(data_dir_path / 'docker-collection-dev.yml')) as test_file:
        collection_settings = yaml.load(collection_file, Loader=yaml.FullLoader)
        test_settings = yaml.load(test_file, Loader=yaml.FullLoader)
        assert collection_settings == test_settings


def test_write_global_docker_file(monkeypatch, data_dir_path, templates_dir_path, tmpdir):
    monkeypatch.setattr(c, 'docker_file_name', 'docker-compose.override.yml')
    monkeypatch.setattr(c, 'settings_dir_name', str(tmpdir / 'settings'))
    monkeypatch.setattr(c, 'root_dir', tmpdir)

    collection = 'FL1'
    collections = OrderedDict((
        (collection, {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2'}),))
    os.makedirs(os.path.join(c.settings_dir_name, collection))

    write_collection_docker_file(collection, os.path.join(c.settings_dir_name, collection),
                                 {'image': 'snoop2', 'snoop_port': 45025, 'autoindex': True})
    write_global_docker_file(collections)
    with open(str(tmpdir / c.docker_file_name)) as docker_file, \
            open(str(data_dir_path / 'docker-compose.override-uppercase.yml')) as test_file:
        global_settings = yaml.load(docker_file, Loader=yaml.FullLoader)
        test_settings = yaml.load(test_file, Loader=yaml.FullLoader)
        assert global_settings == test_settings

    collection = 'fl2'
    collections = OrderedDict((
        (collection, {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2'}),))
    os.makedirs(os.path.join(c.settings_dir_name, collection))

    write_collection_docker_file(collection, os.path.join(c.settings_dir_name, collection),
                                 {'image': 'snoop2', 'snoop_port': 45025, 'autoindex': True})
    write_global_docker_file(collections)
    with open(str(tmpdir / c.docker_file_name)) as docker_file, \
            open(str(data_dir_path / 'docker-compose.override-lowercase.yml')) as test_file:
        global_settings = yaml.load(docker_file, Loader=yaml.FullLoader)
        test_settings = yaml.load(test_file, Loader=yaml.FullLoader)
        assert global_settings == test_settings

    collection = 'FL3'
    collections = OrderedDict((
        (collection, {'profiling': False, 'for_dev': True, 'autoindex': True, 'image': 'snoop2'}),))
    os.makedirs(os.path.join(c.settings_dir_name, collection))

    write_collection_docker_file(collection, os.path.join(c.settings_dir_name, collection),
                                 {'image': 'snoop2', 'snoop_port': 45025, 'for_dev': True, 'autoindex': True})
    write_global_docker_file(collections, for_dev=True)
    with open(str(tmpdir / c.docker_file_name)) as docker_file, \
            open(str(data_dir_path / 'docker-compose.override-dev.yml')) as test_file:
        global_settings = yaml.load(docker_file, Loader=yaml.FullLoader)
        test_settings = yaml.load(test_file, Loader=yaml.FullLoader)
        assert global_settings == test_settings


def test_read_write_env_file(monkeypatch, data_dir_path, tmpdir):
    env1_test = {
        c.DOCKER_HOOVER_SNOOP_SECRET_KEY: 'secret-key===',
        c.DOCKER_HOOVER_SNOOP_DEBUG: False,
        c.DOCKER_HOOVER_SNOOP_BASE_URL: 'http://localhost'
    }
    env2_test = {
        c.DOCKER_HOOVER_SNOOP_SECRET_KEY: 'secret-key===',
        c.DOCKER_HOOVER_SNOOP_DEBUG: True,
        c.DOCKER_HOOVER_SNOOP_BASE_URL: 'http://localhost'
    }

    with monkeypatch.context() as m:
        m.setattr(c, 'env_file_name', 'snoop-1.env')
        env1 = read_env_file(str(data_dir_path))
        assert env1 == env1_test
    write_env_file(str(tmpdir), {'env': env1})
    with open(str(data_dir_path / 'snoop-1-test.env')) as env1_test_file, \
            open(str(tmpdir / c.env_file_name)) as env_file:
        env1_test_content = env1_test_file.read()
        env_content = env_file.read()
        assert env1_test_content == env_content

    with monkeypatch.context() as m:
        m.setattr(c, 'env_file_name', 'snoop-2.env')
        env2 = read_env_file(str(data_dir_path))
        assert env2 == env2_test
    write_env_file(str(tmpdir), {'env': env2})
    with open(str(data_dir_path / 'snoop-2.env')) as env2_test_file, \
            open(str(tmpdir / c.env_file_name)) as env_file:
        env2_test_content = env2_test_file.read()
        env_content = env_file.read()
        assert env2_test_content == env_content


def test_write_collections_docker_files(monkeypatch, data_dir_path, tmpdir):
    monkeypatch.setattr(c, 'templates_dir_name', str(data_dir_path.parent.parent / 'templates'))
    monkeypatch.setattr(c, 'validate_collection_data_dir', lambda _: True)
    collections_settings = {
        'testdata1': {'image': 'snoop2', 'snoop_port': 45025, 'flower_port': None},
        'testdata2': {'image': 'liquidinvestigations/hoover-snoop2:0.1', 'snoop_port': 45026,
                      'flower_port': 15555},
    }

    with chdir(str(data_dir_path / 'collections')):
        data = get_collections_data()

    copytree(str(data_dir_path / 'collections'), str(tmpdir / 'collections'))
    with chdir(str(tmpdir / 'collections')):
        write_collections_docker_files(data['collections'])
        for collection in data['collections']:
            settings_dir = str(tmpdir / 'collections' / settings_dir_name / collection)
            image, snoop_port, flower_port = read_collection_docker_file(collection, settings_dir)
            assert image == collections_settings[collection]['image']
            assert snoop_port == collections_settings[collection]['snoop_port']
            assert flower_port == collections_settings[collection]['flower_port']
