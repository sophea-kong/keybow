#!/bin/bash
set -euo pipefail

BASE_TAG=${BASE_TAG:-bionic}
PLATFORM=${PLATFORM:-}

NO_CACHE=""
for arg in "$@"; do
    case "$arg" in
        --no-cache) NO_CACHE="--no-cache" ;;
        --arm64) PLATFORM="linux/arm64"; BASE_TAG="bionic-arm64" ;;
        --platform=*) PLATFORM="${arg#*=}" ;;
        *) echo "[build.sh] unknown option: $arg"; exit 1 ;;
    esac
done

PLATFORM_ARG=""
if [ -n "${PLATFORM}" ]; then
    PLATFORM_ARG="--platform ${PLATFORM}"
    echo "[build.sh] platform=${PLATFORM} base_tag=${BASE_TAG}"
fi

# Build base simulator image. If remote base pull fails, allow fallback only when
# a local krpc/intball-simulator:latest image already exists.
if docker build $NO_CACHE $PLATFORM_ARG --build-arg BASE_TAG=${BASE_TAG} -t krpc/intball-simulator:latest -f docker/Dockerfile.krpc-base .; then
	echo "[build.sh] built krpc/intball-simulator:latest"
else
	echo "[build.sh] WARN: failed to build krpc/intball-simulator:latest"
	if docker image inspect krpc/intball-simulator:latest >/dev/null 2>&1; then
		echo "[build.sh] reuse local cached image: krpc/intball-simulator:latest"
	else
		echo "[build.sh] ERROR: no local fallback image available"
		exit 1
	fi
fi

docker build $NO_CACHE $PLATFORM_ARG -t krpc/krpc-replay:latest -f docker/Dockerfile.krpc-replay .
echo "[build.sh] built krpc/krpc-replay:latest"
