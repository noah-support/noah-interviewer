#!/bin/bash

docker build -t interview-db .
docker run --name interview-db -d -p 5434:5432 -v postgres-data-2:/var/lib/postgresql/data interview-db