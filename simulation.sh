#!/bin/sh

docker compose -f docker-compose.yaml up --abort-on-container-exit --exit-code-from krpc
docker compose -f docker-compose.yaml down
