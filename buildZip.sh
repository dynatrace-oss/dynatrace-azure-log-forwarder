#!/bin/bash
publish_archive="publish.zip"

if ! command -v zip &> /dev/null
then
    echo "zip could not be found"
    exit 1
fi

rm -f "$publish_archive"
sh version.sh
zip -rq "$publish_archive" logs_ingest requirements.txt host.json