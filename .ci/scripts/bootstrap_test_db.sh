#!/usr/bin/env bash
set -euxo pipefail

# Start a Postgres container for tests and create testdb

docker run -d --name pgtest -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres postgres:16
for i in {1..40}; do (echo > /dev/tcp/127.0.0.1/5432) && break || sleep 0.5; done
PGPASSWORD=postgres createdb -h 127.0.0.1 -p 5432 -U postgres testdb
