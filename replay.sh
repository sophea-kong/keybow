#!/bin/sh
export PLAY_RATE=${1:-1}
export START_TIME=${2:-0}

docker compose -f docker-compose.replay.yaml up --abort-on-container-exit --exit-code-from krpc
docker compose -f docker-compose.replay.yaml down
