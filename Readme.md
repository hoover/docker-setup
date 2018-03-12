## Docker scripts for Hoover
This repository contains a [Docker Compose](https://docs.docker.com/compose/)
configuration for [Hoover](https://hoover.github.io).

### Installation
These instructions have been tested on Debian Jessie.

1. Increase `vm.max_map_count` to at least 262144, to make elasticsearch happy
   - see [the official documentation][] for details.

  [the official documentation]: https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode

2. Install docker:

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

3. Clone the repo and set up folders:

    ```bash
    git clone https://github.com/hoover/docker-setup /opt/hoover
    cd /opt/hoover
    mkdir volumes volumes/metrics volumes/metrics/users collections
    ```

4. Create configuration files:

    * `/opt/hoover/snoop.env`:

        ```env
        DOCKER_HOOVER_SNOOP_SECRET_KEY=some-random-secret
        DOCKER_HOOVER_SNOOP_DEBUG=on
        DOCKER_HOOVER_SNOOP_BASE_URL=http://snoop.hoover.example.com
        ```

    * `/opt/hoover/search.env`:

        ```env
        DOCKER_HOOVER_SEARCH_SECRET_KEY=some-random-secret
        DOCKER_HOOVER_SEARCH_DEBUG=on
        DOCKER_HOOVER_BASE_URL=http://hoover.example.com
        ```

5. Spin up the docker containers, run migrations, create amdin user:

    ```bash
    docker-compose run --rm snoop ./manage.py migrate
    docker-compose run --rm search ./manage.py migrate
    docker-compose run --rm search ./manage.py createsuperuser
    docker-compose run --rm ui node build.js
    docker-compose run --rm search ./manage.py collectstatic --noinput
    docker-compose up -d
    ```

6. Import the test dataset:

    ```bash
    git clone https://github.com/hoover/testdata collections/testdata
    docker-compose run --rm snoop ./manage.py createcollection testdata /opt/hoover/collections/testdata/data
    docker-compose run --rm snoop ./manage.py rundispatcher

    # wait for jobs to finish, i.e. when this command stops printing messages:
    docker-compose logs -f snoop-worker

    docker-compose run --rm search ./manage.py addcollection testdata http://snoop/collections/testdata/json --public
    docker-compose run --rm search ./manage.py resetindex testdata
    docker-compose run --rm search ./manage.py update -v2 testdata
    ```


### Configuring two-factor authentication
Since hoover-search has built-in support for TOTP two-factor authentication,
you just need to enable the module by adding a line to `search.env`:

```env
DOCKER_HOOVER_TWOFACTOR_ENABLED=on
```

Then generate an invitation for your user (replace `admin` with your username):

```bash
docker-compose run --rm search ./manage.py invite admin
```


### Importing OCR'ed documents
The OCR process (Optical Character Recognition – extracting machine-readable
text from scanned documents) is done external to Hoover, using e.g. Tesseract.
Try the Python pypdftoocr package. The resulting OCR'ed documents should be PDF
files whose filename is the MD5 checksum of the _original_ document, e.g.
`d41d8cd98f00b204e9800998ecf8427e.pdf`. Put all the OCR'ed files in a folder
(we'll call it _ocr foler_ below) and follow these steps to import them into
Hoover:

* The _ocr folder_ should be in a path accessible to the hoover docker images,
  e.g. in the shared "collections" folder, `/opt/hoover/collections/ocr/myocr`.

* Register _ocr folder_ as a source for OCR named `myocr` (choose any name you
  like):

    ```
    docker-compose run --rm snoop ./manage.py createocrsource myocr /opt/hoover/collections/ocr/myocr
    ```

* Import the OCR'ed files:

    ```
    docker-compose run --rm snoop ./manage.py rundispatcher
    # wait for jobs to finish
    ```

* Re-index the collection:

    ```
    docker-compose run --rm search ./manage.py update -v2 mycol
    ```
