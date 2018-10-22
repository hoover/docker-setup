from collections import OrderedDict
import os
from pathlib import Path
import re

import pytest
import yaml

from src.common import get_collections_data, write_python_settings_file, \
    write_collection_docker_file, docker_collection_file_name, \
    write_global_docker_file, read_env_file, write_env_file, \
    InvalidCollectionName, validate_collection_name
import src.common as c


@pytest.fixture
def data_dir_path():
    return Path(__file__).absolute().parent / 'data'


@pytest.fixture
def templates_dir_path():
    return Path(__file__).absolute().parent.parent / 'templates'


def test_validate_collection_name():
    with pytest.raises(InvalidCollectionName):
        validate_collection_name(None)
    with pytest.raises(InvalidCollectionName):
        validate_collection_name('')
    for char in "./\\()\"':,.;<>~!@#$%^&*|+=[]{}`~?-":
        with pytest.raises(InvalidCollectionName):
            validate_collection_name('aaa%s' % char)
    validate_collection_name('Aa0_')


def test_get_collections_data(monkeypatch, data_dir_path):
    env = {
        c.DOCKER_HOOVER_SNOOP_SECRET_KEY: 'secret-key===',
        c.DOCKER_HOOVER_SNOOP_DEBUG: False,
        c.DOCKER_HOOVER_SNOOP_BASE_URL: 'http://localhost',
        c.DOCKER_HOOVER_SNOOP_STATS: True
    }

    monkeypatch.setattr(c, 'docker_file_name', str(data_dir_path / 'docker-compose-clean.yml'))
    monkeypatch.setattr(c, 'settings_dir_name', str(data_dir_path))
    monkeypatch.setattr(c, 'get_settings_dir', lambda _: c.settings_dir_name)
    data = get_collections_data()
    assert data['collections'] == OrderedDict((
        ('testdata1', {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45025, 'flower_port': 15555}),
        ('testdata2', {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45026, 'flower_port': 15556})))
    assert data['snoop_port'] == 45027
    assert data['flower_port'] == 15557
    assert data['pg_port'] == 5433
    assert data['dev_instances'] == 0
    assert data['stats_clients'] == 2

    c.docker_file_name = str(data_dir_path / 'docker-compose-profiling.yml')
    data = get_collections_data()
    assert data['collections'] == OrderedDict((
        ('testdata1', {'profiling': True, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45025}),
        ('testdata2', {'profiling': True, 'for_dev': False, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45026})))
    assert data['snoop_port'] == 45027
    assert data['flower_port'] == 15557
    assert data['pg_port'] == 5433
    assert data['dev_instances'] == 0
    assert data['stats_clients'] == 2

    monkeypatch.setattr(c, 'docker_file_name', str(data_dir_path / 'docker-compose-dev.yml'))
    data = get_collections_data()
    assert data['collections'] == OrderedDict((
        ('testdata1', {'profiling': False, 'for_dev': True, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45025}),
        ('testdata2', {'profiling': False, 'for_dev': True, 'autoindex': True, 'image': 'snoop2',
                       'env': env, 'snoop_port': 45026})))
    assert data['snoop_port'] == 45027
    assert data['flower_port'] == 15557
    assert data['pg_port'] == 5435
    assert data['dev_instances'] == 2
    assert data['stats_clients'] == 2


def test_write_python_settings_file(tmpdir):
    collection = 'testdata'

    write_python_settings_file(collection, str(tmpdir), profiling=False, for_dev=False)
    with open(str(tmpdir / 'snoop-settings.py')) as settings_file:
        settings = settings_file.read()
        assert 'PROFILING_ENABLED' not in settings
        assert 'REMOTE_DEBUG_ENABLED' not in settings
        found = re.search('TASK_PREFIX = \'(\w+)\'', settings)
        assert found and found.group(1) == collection

    write_python_settings_file(collection, str(tmpdir), profiling=True, for_dev=False)
    with open(str(tmpdir / 'snoop-settings.py')) as settings_file:
        settings = settings_file.read()
        assert 'PROFILING_ENABLED' in settings
        assert 'REMOTE_DEBUG_ENABLED' not in settings

    write_python_settings_file(collection, str(tmpdir), profiling=False, for_dev=True)
    with open(str(tmpdir / 'snoop-settings.py')) as settings_file:
        settings = settings_file.read()
        assert 'PROFILING_ENABLED' not in settings
        assert 'REMOTE_DEBUG_ENABLED' in settings


def test_write_collection_docker_file(data_dir_path, tmpdir):
    collection = 'testdata'
    snoop_image = 'snoop_image'
    tmpdir_path = str(tmpdir)

    write_collection_docker_file(collection, snoop_image, tmpdir_path, 45025, flower_port=15555)
    with open(os.path.join(tmpdir_path, docker_collection_file_name)) as collection_file, \
            open(str(data_dir_path / 'docker-collection-clean.yml')) as test_file:
        collection_settings = yaml.load(collection_file)
        test_settings = yaml.load(test_file)
        assert collection_settings == test_settings

    write_collection_docker_file(collection, snoop_image, tmpdir_path, 45025, profiling=True)
    with open(os.path.join(tmpdir_path, docker_collection_file_name)) as collection_file, \
            open(str(data_dir_path / 'docker-collection-profiling.yml')) as test_file:
        collection_settings = yaml.load(collection_file)
        test_settings = yaml.load(test_file)
        assert collection_settings == test_settings

    write_collection_docker_file(collection, snoop_image, tmpdir_path, 45025, for_dev=True, pg_port=5433)
    with open(os.path.join(tmpdir_path, docker_collection_file_name)) as collection_file, \
            open(str(data_dir_path / 'docker-collection-dev.yml')) as test_file:
        collection_settings = yaml.load(collection_file)
        test_settings = yaml.load(test_file)
        assert collection_settings == test_settings

    write_collection_docker_file(collection, snoop_image, tmpdir_path, 45025, stats=True)
    with open(os.path.join(tmpdir_path, docker_collection_file_name)) as collection_file, \
            open(str(data_dir_path / 'docker-collection-stats.yml')) as test_file:
        collection_settings = yaml.load(collection_file)
        test_settings = yaml.load(test_file)
        assert collection_settings == test_settings


def test_write_global_docker_file(monkeypatch, data_dir_path, templates_dir_path, tmpdir):
    monkeypatch.setattr(c, 'docker_file_name', 'docker-compose.override.yml')
    monkeypatch.setattr(c, 'settings_dir_name', str(tmpdir / 'settings'))
    monkeypatch.setattr(c, 'root_dir', tmpdir)

    collection = 'FL1'
    collections = OrderedDict((
        (collection, {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2'}),))
    os.makedirs(os.path.join(c.settings_dir_name, collection))

    write_collection_docker_file(collection, 'snoop2', os.path.join(c.settings_dir_name, collection), 45025)
    write_global_docker_file(collections)
    with open(str(tmpdir / c.docker_file_name)) as docker_file, \
            open(str(data_dir_path / 'docker-compose.override-uppercase.yml')) as test_file:
        global_settings = yaml.load(docker_file)
        test_settings = yaml.load(test_file)
        assert global_settings == test_settings

    collection = 'fl2'
    collections = OrderedDict((
        (collection, {'profiling': False, 'for_dev': False, 'autoindex': True, 'image': 'snoop2'}),))
    os.makedirs(os.path.join(c.settings_dir_name, collection))

    write_collection_docker_file(collection, 'snoop2', os.path.join(c.settings_dir_name, collection), 45025)
    write_global_docker_file(collections)
    with open(str(tmpdir / c.docker_file_name)) as docker_file, \
            open(str(data_dir_path / 'docker-compose.override-lowercase.yml')) as test_file:
        global_settings = yaml.load(docker_file)
        test_settings = yaml.load(test_file)
        assert global_settings == test_settings

    collection = 'FL3'
    collections = OrderedDict((
        (collection, {'profiling': False, 'for_dev': True, 'autoindex': True, 'image': 'snoop2'}),))
    os.makedirs(os.path.join(c.settings_dir_name, collection))

    write_collection_docker_file(collection, 'snoop2', os.path.join(c.settings_dir_name, collection),
                                 45025, for_dev=True)
    write_global_docker_file(collections, for_dev=True)
    with open(str(tmpdir / c.docker_file_name)) as docker_file, \
            open(str(data_dir_path / 'docker-compose.override-dev.yml')) as test_file:
        global_settings = yaml.load(docker_file)
        test_settings = yaml.load(test_file)
        assert global_settings == test_settings

    write_collection_docker_file(collection, 'snoop2', os.path.join(c.settings_dir_name, collection),
                                 45025, stats=True)
    write_global_docker_file(collections, stats=True)
    with open(str(tmpdir / c.docker_file_name)) as docker_file, \
            open(str(data_dir_path / 'docker-compose.override-stats.yml')) as test_file:
        global_settings = yaml.load(docker_file)
        test_settings = yaml.load(test_file)
        assert global_settings == test_settings


def test_read_write_env_file(monkeypatch, data_dir_path, tmpdir):
    env1_test = {
        c.DOCKER_HOOVER_SNOOP_SECRET_KEY: 'secret-key===',
        c.DOCKER_HOOVER_SNOOP_DEBUG: False,
        c.DOCKER_HOOVER_SNOOP_BASE_URL: 'http://localhost',
        c.DOCKER_HOOVER_SNOOP_STATS: False
    }
    env2_test = {
        c.DOCKER_HOOVER_SNOOP_SECRET_KEY: 'secret-key===',
        c.DOCKER_HOOVER_SNOOP_DEBUG: True,
        c.DOCKER_HOOVER_SNOOP_BASE_URL: 'http://localhost',
        c.DOCKER_HOOVER_SNOOP_STATS: True
    }

    with monkeypatch.context() as m:
        m.setattr(c, 'env_file_name', 'snoop-1.env')
        env1 = read_env_file(str(data_dir_path))
        assert env1 == env1_test
    write_env_file(str(tmpdir), env1)
    with open(str(data_dir_path / 'snoop-1-test.env')) as env1_test_file, \
            open(str(tmpdir / c.env_file_name)) as env_file:
        env1_test_content = env1_test_file.read()
        env_content = env_file.read()
        assert env1_test_content == env_content

    with monkeypatch.context() as m:
        m.setattr(c, 'env_file_name', 'snoop-2.env')
        env2 = read_env_file(str(data_dir_path))
        assert env2 == env2_test
    write_env_file(str(tmpdir), env2)
    with open(str(data_dir_path / 'snoop-2.env')) as env2_test_file, \
            open(str(tmpdir / c.env_file_name)) as env_file:
        env2_test_content = env2_test_file.read()
        env_content = env_file.read()
        assert env2_test_content == env_content
