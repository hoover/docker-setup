## Docker scripts for Hoover
This repository contains a [Docker Compose](https://docs.docker.com/compose/)
configuration for [Hoover](https://hoover.github.io).

### Installation
These instructions have been tested on Debian Jessie.

1. Increase `vm.max_map_count` to at least 262144, to make elasticsearch happy
   - see [the official documentation][] for details.

  [the official documentation]: https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html#docker-cli-run-prod-mode

2. Install docker:

    ```shell
    apt-get install -y apt-transport-https ca-certificates curl gnupg2 software-properties-common python3.6 python3-pip
    pip3 install -r requirements.txt
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y docker-ce
    service docker start
    curl -L https://github.com/docker/compose/releases/download/1.22.0/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ```

3. Clone the repo and set up folders:

    ```shell
    git clone https://github.com/hoover/docker-setup /opt/hoover
    cd /opt/hoover
    mkdir -p volumes volumes/metrics volumes/metrics/users volumes/search-es-snapshots volumes/search-es/data collections
    chmod 777 volumes/search-es-snapshots volumes/search-es/data
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

        127.0.0.1 snoop.hoover.example.com
        127.0.0.1 hoover.example.com

5. Spin up the docker containers, run migrations, create amdin user:

    ```shell
    docker-compose run --rm search ./manage.py migrate
    docker-compose run --rm search ./manage.py createsuperuser
    docker-compose run --rm ui npm run build
    docker-compose run --rm search ./manage.py collectstatic --noinput
    docker-compose up -d
    ```

6. Import the test dataset:

    ```shell
    git clone https://github.com/hoover/testdata collections/testdata
    python3 ./createcollection.py -c testdata
    ```

### Configuring two-factor authentication
Since hoover-search has built-in support for TOTP two-factor authentication,
you just need to enable the module by adding a line to `search.env`:

```env
DOCKER_HOOVER_TWOFACTOR_ENABLED=on
```

Then generate an invitation for your user (replace `admin` with your username):

```shell
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

    ```shell
    docker-compose run --rm snoop--testdata ./manage.py createocrsource myocr /opt/hoover/collections/testdata/ocr/myocr
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

When creating collections or updating settings use the `-d` option. E.g.:
```shell
python3 ./createcollection.py -c <collection_name> -d
python3 ./updatesettings.py -c <collection_name> -d
```

It will generate the following code in the docker-compose.override.yml:
```yaml
  snoop-rabbitmq:
    ports:
      - "5672:5672"

  snoop-tika:
    ports:
      - "9998:9998"

  search-pg:
    ports:
      - "5432:5432"

  search-es:
    ports:
      - "9200:9200"

  ui:
    volumes:
      - ../ui:/opt/hoover/ui:cached

  search:
    volumes:
      - ../search:/opt/hoover/search:cached
```

For each collection it will add the following setting:
```yaml
  snoop-worker--testdata:
    volumes:
      - ../snoop2:/opt/hoover/snoop:cached
  snoop--testdata:
    volumes:
      - ../snoop2:/opt/hoover/snoop:cached
```

This will mount the code repositories inside the docker containers to run the
local development code.


### Docker images
Docker-hub builds images based on the Hoover GitHub repos triggered by pushes
to the master branches: [snoop2][], [search][], [ui][].

[snoop2]: https://hub.docker.com/r/liquidinvestigations/hoover-snoop2/
[search]: https://hub.docker.com/r/liquidinvestigations/hoover-search/
[ui]: https://hub.docker.com/r/liquidinvestigations/hoover-ui/

You can also build images locally. For example, the snoop2 image:

```shell
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
To create a collection, copy the original files in the following folder:
`collections/<collection_name>/data`

Then run the following command:
```shell
python3 ./createcollection.py -c <collection_name>
```

The script will ask you to run additional commands if it ran succesfully:
```shell
# run migrations
docker-compose run --rm snoop--<collection_name> ./manage.py migrate
# reset stats index
docker-compose run --rm snoop--<collection_name> ./manage.py resetstatsindex
# create collection inside the snoop docker image
docker-compose run --rm snoop--<collection_name> ./manage.py createcollection <collection_name> /opt/hoover/collections/<collection_name>/data
# add collection to search
docker-compose run --rm search ./manage.py addcollection <collection_name> http://snoop--<collection_name>/collections/<collection_name>/json --public
# add ocr source
docker-compose run --rm snoop--<collection_name> ./manage.py createocrsource ocr-name /opt/hoover/collections/<collection_name>/ocr-data
```

The `createcollection` docker command for snoop will set up a new collection in the
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

1. Export the search index:
```shell
docker-compose run --rm -T snoop--<collection_name> ./manage.py exportcollectionindex <collection_name> | gzip -1 > <collection_name>-index.tgz
```

2. Run the following command to stop docker-compose:
```shell
docker-compose down
```

3. Copy the directory `volumes/snoop-pg--<collection_name>`

4. Copy the directory `snoop-blobs/<collection_name>`

5. Run the following command to start docker-compose:
```shell
docker-compose up -d
```

Importing:

1. Create a new collection <collection_name> (see above)

2. Run the following command to stop docker-compose:
```shell
docker-compose down
```

3. Copy the Postgresql data directory to directory `volumes/snoop-pg--<collection_name>`

4. Copy the blobs to the directory `snoop-blobs/<collection_name>`

5. Run the following command to start docker-compose:
```shell
docker-compose up -d
```

6. Wait about 1 minute for docker to start and then import the search index:
```shell
docker-compose run --rm -T snoop--<collection_name> ./manage.py importcollectionindex <collection_name> < <collection_name>-index.tgz
```

### Deleting a collection
```shell
python3 ./removecollection.py -c <collection_name>
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


## Adding custom settings for docker services
To add custom settings to docker services create a file `docker-custom-services.yml` in the
`templates` directory and add services with custom settings there in yml format. E.g.:
```yaml
  search-es:
    environment:
      ES_JAVA_OPTS: -Xms2g -Xmx2g
```

After that run the update script:
```shell
python3 ./updatesettings.py -c <collection_name>
```
