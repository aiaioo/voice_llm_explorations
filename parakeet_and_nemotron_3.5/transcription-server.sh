#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/parakeet-server" \
  --model "$SCRIPT_DIR/models/nemotron-3.5-asr-streaming-0.6b-q5_k.gguf" \
  --threads "$(sysctl -n hw.ncpu)" \
  --host "${HOST:-127.0.0.1}" \
  --port "${PORT:-8080}"
