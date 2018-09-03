from collections import OrderedDict
from pathlib import Path
import pytest

from src.common import get_collections_data, write_python_settings_file
import src.common as c


@pytest.fixture
def data_dir_path():
    return Path(__file__).absolute().parent / 'data'


def test_get_collections_data(data_dir_path):
    c.docker_file_name = str(data_dir_path / 'docker-compose-clean.yml')
    collections, snoop_port, pg_port, for_dev = get_collections_data()
    assert collections == OrderedDict((
        ('testdata1', {'profiling': False, 'for_dev': False}),
        ('testdata2', {'profiling': False, 'for_dev': False})))
    assert snoop_port == 45027
    assert pg_port == 5433
    assert for_dev == 0

    c.docker_file_name = str(data_dir_path / 'docker-compose-profiling.yml')
    collections, snoop_port, pg_port, for_dev = get_collections_data()
    assert collections == OrderedDict((
        ('testdata1', {'profiling': True, 'for_dev': False}),
        ('testdata2', {'profiling': True, 'for_dev': False})))
    assert snoop_port == 45027
    assert pg_port == 5433
    assert for_dev == 0

    c.docker_file_name = str(data_dir_path / 'docker-compose-dev.yml')
    collections, snoop_port, pg_port, for_dev = get_collections_data()
    assert collections == OrderedDict((
        ('testdata1', {'profiling': False, 'for_dev': True}),
        ('testdata2', {'profiling': False, 'for_dev': True})))
    assert snoop_port == 45027
    assert pg_port == 5435
    assert for_dev == 2


def test_write_python_settings_file(tmpdir):
    collection = 'testdata'

    write_python_settings_file(collection, str(tmpdir), profiling=False, for_dev=False)
    with open(str(tmpdir / 'snoop-settings.py')) as settings_file:
        settings = settings_file.read()
        assert 'PROFILING_ENABLED' not in settings
        assert 'REMOTE_DEBUG_ENABLED' not in settings

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
