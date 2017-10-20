## Docker scripts for Hoover
This repository contains a [Docker Compose](https://docs.docker.com/compose/)
configuration for [Hoover](https://hoover.github.io).

### Installation
These instructions have been tested on Debian Jessie.

1. Install docker:

    ```bash
    apt-get install -y apt-transport-https ca-certificates curl gnupg2 software-properties-common
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y docker-ce
    service docker start
    curl -L https://github.com/docker/compose/releases/download/1.13.0/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ```

2. Clone the repo and set up folders:

    ```bash
    git clone https://github.com/hoover/docker-setup /opt/hoover
    cd /opt/hoover
    mkdir volumes volumes/metrics volumes/metrics/users volumes/cache volumes/cache/archive volumes/cache/msg volumes/cache/pst collections
    ```

3. Create configuration files:

    * `/opt/hoover/snoop.env`:

        ```env
        DOCKER_HOOVER_SNOOP_SECRET_KEY=some-random-secret
        DOCKER_HOOVER_SEARCH_DEBUG=on
        ```

    * `/opt/hoover/search.env`:

        ```env
        DOCKER_HOOVER_SEARCH_SECRET_KEY=some-random-secret
        DOCKER_HOOVER_SEARCH_DEBUG=on
        DOCKER_HOOVER_BASE_URL=http://hoover.example.com
        ```

    * `/opt/hoover/nginx.env`:

        ```env
        NGINX_SERVER_NAME=hoover.example.com
        ```

4. Spin up the docker containers, run migrations, create amdin user:

    ```bash
    docker-compose run --rm snoop ./manage.py migrate
    docker-compose run --rm search ./manage.py migrate
    docker-compose run --rm search ./manage.py createsuperuser
    docker-compose run --rm ui node build.js
    docker-compose run --rm search ./manage.py collectstatic --noinput
    docker-compose up -d
    ```

5. Import the test dataset:

    ```bash
    git clone https://github.com/hoover/testdata collections/testdata
    docker-compose run --rm snoop ./manage.py createcollection /opt/hoover/collections/testdata/data testdata testdata testdata testdata
    docker-compose run --rm snoop ./manage.py resetindex testdata
    docker-compose run --rm snoop ./manage.py walk testdata
    docker-compose run --rm snoop ./manage.py digestqueue
    docker-compose run --rm snoop ./manage.py worker digest
    docker-compose run --rm search ./manage.py addcollection testdata http://snoop/testdata/json
    docker-compose run --rm search ./manage.py update -v2 testdata
    ```
