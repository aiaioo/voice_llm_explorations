#!/usr/bin/env bash
set -euo pipefail

curl -s -F "file=@${1:?Usage: test-server.sh <audio.wav>}" \
  "http://localhost:8080/v1/audio/transcriptions"
echo
