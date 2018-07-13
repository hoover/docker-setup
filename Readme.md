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
    mkdir volumes volumes/metrics volumes/metrics/users volumes/search-es-snapshots collections
    chmod 777 volumes/search-es-snapshots
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

    For local development, add the following to `/etc/hosts` to make the base URLs resolve to localhost:

        ```
          127.0.0.1 snoop.hoover.example.com
          127.0.0.1 hoover.example.com
        ```

5. Spin up the docker containers, run migrations, create amdin user:

    ```bash
    docker-compose run --rm snoop ./manage.py migrate
    docker-compose run --rm snoop ./manage.py resetstatsindex
    docker-compose run --rm search ./manage.py migrate
    docker-compose run --rm search ./manage.py createsuperuser
    docker-compose run --rm ui npm run build
    docker-compose run --rm search ./manage.py collectstatic --noinput
    docker-compose up -d
    ```

6. Import the test dataset:

    ```bash
    git clone https://github.com/hoover/testdata collections/testdata
    docker-compose run --rm snoop ./manage.py createcollection testdata /opt/hoover/collections/testdata/data

    # wait for jobs to finish, i.e. when this command stops printing messages:
    docker-compose logs -f snoop-worker

    docker-compose run --rm search ./manage.py addcollection testdata http://snoop/collections/testdata/json --public
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
  e.g. in the shared "collections" folder,
  `/opt/hoover/collections/testdata/ocr/myocr`.

* Register _ocr folder_ as a source for OCR named `myocr` (choose any name you
  like):

    ```
    docker-compose run --rm snoop ./manage.py createocrsource myocr /opt/hoover/collections/testdata/ocr/myocr
    # wait for jobs to finish
    ```


### Decrypting PGP emails
If you have access to PGP private keys, snoop can decrypt emails that were
encrypted for those keys. Import the keys into a gnupg home folder placed next
to the `docker-compose.yml` file. Snoop will automatically use this folder when
it encounters an encrypted email.

```shell
gpg --home gnupg --import < path_to_key_file
```

You may need to remove an existing but known password once and use this key instead.

```shell
gpg --home gnupg --export-options export-reset-subkey-passwd --export-secret-subkeys ABCDEF01 > path_to_key_nopassword
gpg --home gnupg --delete-secret-keys ABCDEF01
gpg --home gnupg --delete-key ABCDEF01
gpg --home gnupg --import < path_to_key_nopassword
```

### Development
Clone the code repositories:

```shell
git clone https://github.com/hoover/docker-setup
git clone https://github.com/hoover/snoop2
git clone https://github.com/hoover/search
git clone https://github.com/hoover/ui
```

Create a `docker-compose.override.yml` file in `docker-setup` with the
following content. It will mount the code repositories inside the docker
containers to run the local development code:

```yaml
version: "2"

services:

  snoop-worker:
    volumes:
      - ../snoop2:/opt/hoover/snoop

  snoop:
    volumes:
      - ../snoop2:/opt/hoover/snoop

  search:
    volumes:
      - ../search:/opt/hoover/search

  ui:
    volumes:
      - ../ui:/opt/hoover/ui
```


### Docker images
Docker-hub builds images based on the Hoover GitHub repos triggered by pushes
to the master branches: [snoop2][], [search][], [ui][].

[snoop2]: https://hub.docker.com/r/liquidinvestigations/hoover-snoop2/
[search]: https://hub.docker.com/r/liquidinvestigations/hoover-search/
[ui]: https://hub.docker.com/r/liquidinvestigations/hoover-ui/

You can also build images locally. For example, the snoop2 image:

```
cd snoop2
docker build . --tag snoop2
```

Then add this snippet to `docker-compose.override.yml` to test the image
locally, and run `docker-compose up -d` to (re)start the containers:

```yaml
version: "2"

services:

  snoop-worker:
    image: snoop2

  snoop:
    image: snoop2
```

### Testing
For Snoop and Search tests based on [pytest][] can be executed using this commands:

[pytest]: https://docs.pytest.org/en/latest/

```shell
docker-compose run --rm snoop pytest
docker-compose run --rm search pytest
```

The test definitions can be found in the `testsuite` folder of each project. Individual tests can be started
using:

```shell
docker-compose run --rm snoop pytest testsuite/test_tika.py
```

## Working with collections


### Creating a collection
To create a collection, copy the original files in a folder inside the
`collections` folder. Then run the `createcollection` command for snoop, and
the `addcollection` command for search. It will set up a new collection in the
snoop SQL database, create an elasticsearch index, and it will trigger "walk"
tasks to analyze the collection's contents. As the files get processed they
will show up in the search results.

In this example, we'll name the collection `foo`, and assume the data is copied
to the `collections/foo` directory. The final `--public` flag will make the
collection accessible to all users (or anybody who can access the server if
two-factor authentication is not enabled).

```shell
docker-compose run --rm snoop ./manage.py createcollection foo /opt/hoover/collections/foo
docker-compose run --rm search ./manage.py addcollection foo http://snoop/collections/foo/json --public
```


### Exporting and importing collections
Snoop2 provides commands to export and import collection database records,
blobs, and elasticsearch indexes. The collection name must be the same - this
limitation could be lifted if the elasticsearch import code is modified to
rename the index on import.

Exporting:

```shell
docker-compose run --rm -T snoop ./manage.py exportcollectiondb testdata | gzip -1 > testdata-db.tgz
docker-compose run --rm -T snoop ./manage.py exportcollectionindex testdata | gzip -1 > testdata-index.tgz
docker-compose run --rm -T snoop ./manage.py exportcollectionblobs testdata | gzip -1 > testdata-blobs.tgz
```

Importing:

```shell
docker-compose run --rm -T snoop ./manage.py importcollectiondb testdata < testdata-db.tgz
docker-compose run --rm -T snoop ./manage.py importcollectionindex testdata < testdata-index.tgz
docker-compose run --rm -T snoop ./manage.py importblobs < testdata-blobs.tgz
```

Note that the `importblobs` command doesn't expect a collection as argument;
the blobs have no connection to any particular collection.


### Deleting a collection
```shell
docker-compose run --rm snoop ./manage.py deletecollection testdata
```

This will delete the collection and associated files and directories, the
elasticsearch index, and all tasks directly linked to the collection. It does
NOT delete any blobs or tasks potentially shared with other collections, i.e.
tasks that only handle content from specific blobs.


### Monitoring snoop processing of a collection
Snoop provides an administration interface with statistics on the progress of
analysis on collections. It is exposed via docker on port 45023. To access it
you need to create an account:

```shell
docker-compose run --rm snoop ./manage.py createsuperuser
```

Sometimes it's necessary to rerun some snoop tasks. You can reschedule them
using this command:

```shell
docker-compose run --rm snoop ./manage.py retrytasks --func filesystem.walk --status pending
```

Both `--func` and `--status` are optional and serve to filter down the number
of tasks.
