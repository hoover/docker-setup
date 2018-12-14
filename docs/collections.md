# Working with collections


## Creating a collection
To create a collection, copy the original files in the following folder:
`collections/<collection_name>/data`

Then run the following command:
```shell
./createcollection -c <collection_name>
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

## Monitoring snoop workers
Collections for which automatic indexing was enabled can be monitored using the
[flower](https://flower.readthedocs.io/en/latest/) tool. Run `./listcollections`
to see the settings for all collections. If the automatic indexing was enabled
then in the output an URL to the flower tool will be printed. The output should
look like this:
```1. FL15
  - profiling: False
  - development: False
  - auto-indexing: True
  - image: liquidinvestigations/hoover-snoop2
  - stats: disabled
  - snoop admin URL: http://localhost:45025
  - flower URL: http://localhost:15555
```

## Disable/enable kibana stats
By default kibana stats are disabled when creating a new collection. They can be
enabled/disabled using `./updatesettings`:
```./updatesettings --enable-stats [<collection1>, <collection2>..]
./updatesettings --disable-stats [<collection1>, <collection2>..]
```
The list of collections is optional. If no list was supplied then all collections
will have kibana enabled/disabled.

Kibana stats can also be enabled at collection cretion time:
```./createcollection -c <collection> --stats
```

## Exporting and importing collections
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

## Deleting a collection
```shell
./removecollection -c <collection_name>
```

This will delete the collection and associated files and directories, the
elasticsearch index, and all tasks directly linked to the collection. It does
NOT delete any blobs or tasks potentially shared with other collections, i.e.
tasks that only handle content from specific blobs.


## Monitoring snoop processing of a collection
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
