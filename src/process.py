import subprocess
from subprocess import CalledProcessError


def run(cmd, **kwargs):
    """Run the given command in a subprocess and return the captured output."""

    kwargs.setdefault('shell', True)
    kwargs.setdefault('stderr', subprocess.STDOUT)
    return subprocess.check_output(cmd, **kwargs).decode('latin1')


def ensure_docker_setup_stopped():
    output = run('docker ps --filter "name=docker-setup_search"')
    if 'docker-setup_search' in output:
        print('Stopping docker-compose...')
        print(run('docker-compose down'))


def ensure_docker_running(*args, collection=None):
    output = run('docker ps --filter "name=docker-setup_search"')
    if 'docker-setup_search' not in output:
        print('Starting docker-compose...')
        print(run('docker-compose up -d' + ' '.join(args)))
        print('Waiting for search service...')
        print(run('docker-compose run --rm search /wait'))
        if collection:
            print(f'Waiting for collection "{collection}" service')
            print(run(f'docker-compose run --rm snoop--{collection} /wait'))


def exit_on_exception(f):
    def decorator(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except CalledProcessError as e:
            print(e.output.decode('latin1'))
            exit(e.returncode)

    return decorator
