#!/bin/sh

# Follow the steps below to finish the collection creation:
echo "Starting with added containers using docker-compose..."
docker-compose up -d
echo "Waiting for PostgreSQL to start..."
docker-compose run --rm snoop--{{ collection_name }} /wait
echo "Initializing the collection database, index, running dispatcher..."
docker-compose run --rm snoop--{{ collection_name }} ./manage.py initcollection
echo "Adding the collection to search..."
docker-compose run --rm search ./manage.py addcollection {{ collection_name }} --index {{ collection_index }} http://snoop--{{ collection_name }}/collection/json
echo "Done."
