# Collections


## Creating a collection
To create a collection, copy the original files in the following folder:
`collections/<collection_name>/data`

Then run the following command:
```shell
./createcollection -c <collection_name>
```

The script will ask you to run additional commands if it ran successfully:

1. Start added containers using docker-compose  
```shell
$ docker-compose up -d
```

2. Wait for PostgreSQL startup:  
```shell
$ docker-compose run --rm snoop--<collection_name>/wait
```

3. Initialize the collection database, index, and run dispatcher:  
```shell
$ docker-compose run --rm snoop--<collection_name> ./manage.py initcollection
``` 

4. Add the collection to search (--public is optional):  
```shell
$ docker-compose run --rm search ./manage.py addcollection <collection_name> --index <collection_name> http://snoop--<collection_name> /collection/json --public
```

The `initcollection` docker command for snoop will create the database and an elasticsearch index, and it will trigger "walk" tasks to analyze the collection's contents. As the files get processed they will show up in the search results.

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
```shell
./createcollection -c <collection> --stats
```

## Exporting and importing collections
Snoop2 provides commands to export and import collection database records,
blobs, and elasticsearch indexes. The collection name must be the same - this
limitation could be lifted if the elasticsearch import code is modified to
rename the index on import.


#### Exporting a collection 

In order to work with a snoop collection within another hoover setup, it does not suffice to move collection files. The indexing work which is done when adding a collection needs to be exported from the corresponding snoop2 container as well.

This is done by running the following command, which stores the index in an archive.
***Note***
*Hoover must be running, so execute `docker-compose up -d` and wait a few seconds if Hoover is currently not running.*

```shell
docker-compose run --rm -T snoop--<collection_name> ./manage.py exportindex | gzip -1 > <collection_name>-index.tgz
```
afterwards, use

```shell
docker-compose down
```
in order to stop hoover.  
Then you can safely copy the folders, which are needed for importing a collection
`./snoop-blobs/<collection_name>`
`./volumes/snoop-pg--<collection_name>`

**Note:**
*The actual files, stored at `./collections/<collection_name>` are not necessarily needed.*


#### Importing a Collection

Quick Recap: In order to import a snoop2 collection into hoover, you need:

1. The collection index, as a .tgz archive, named `<collection_name>-index.tgz`

2. The blob folder, which you have copied from `./snoop-blobs/<collection_name>` when you have exported the collection 

3. The database folder you have copied from `./volumes/snoop-pg--<collection_name>` when you have exported the collection

Copy the folders into their respective paths and put the collection index into your hoover directory.
Create a new directory `./collection/<collection_name>` (If you have access to the actual data, you can also copy them in here)

Afterwards run the python script for creating a new collection. 
```shell
./createcollection -c <collection_name>
```
**Note:**
*If this gives you a `ModuleNotFoundError` error, it is likely that you didn't install all requirements necessary for hoover to work, or you've forgot to activate your python virtual environment.*

The script will leave you with a shell script or which needs to be run in order to finalize collection creation (and will also print instructions into your shell). We do not want to run this script, since it would mean indexing the collection, which we don't want to do. 

Run the following commands one after another. It will create the collection and import the index from file instead of running indexing again.


1. start hoover again and spin up the containers for the new collection  
    ```shell
    $ docker-compose up -d
    ```

2. wait for the database  
    ```shell
    $ docker-compose run --rm snoop--<collection_name> /wait
    ```

3. create the data model in the snoop container  
    ```shell
    $ docker-compose run --rm snoop--<collection_name> ./manage.py migrate
    ```

4. import the index  
    ```shell
    $ docker-compose run -T  --rm snoop--<collection_name> ./manage.py importindex < <collection_name>-index.tgz
    ```

5. add the collection to search  
    ```shell
    $ docker-compose run --rm search ./manage.py addcollection <collection_name>--index <collection_name> http://snoop--<collection_name>/collection/json --public
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
