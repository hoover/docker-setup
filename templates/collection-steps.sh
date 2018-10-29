#!/bin/sh

# Follow the steps below to finish the collection creation:
echo "Starting with added containers using docker-compose..."
docker-compose up -d
echo "Waiting for PostgreSQL to start..."
docker-compose run --rm snoop--{{ collection_name }} /wait
echo "Creating the data model..."
docker-compose run --rm snoop--{{ collection_name }} ./manage.py migrate
echo "Creating collection within Snoop..."
docker-compose run --rm snoop--{{ collection_name }} ./manage.py createcollection {{ collection_name }} /opt/hoover/collections/{{ collection_name }}
echo "Adding the collection to search..."
docker-compose run --rm search ./manage.py addcollection {{ collection_name }} --index {{ collection_index }} http://snoop--{{ collection_name }}/collections/{{ collection_name }}/json
echo "Done."
