#!/usr/bin/env bash

ECHO_PREFIX="[drucker-dashboard example]: "

set -e
set -u

echo "$ECHO_PREFIX Start.."

pip install -r requirements.txt

pip install -r ./drucker-grpc-proto/requirements.txt
sh ./drucker-grpc-proto/run_codegen.sh

python app.py