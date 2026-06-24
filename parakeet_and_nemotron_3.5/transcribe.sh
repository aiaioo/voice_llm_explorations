#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/parakeet-cli" transcribe \
  --model "$SCRIPT_DIR/models/nemotron-3.5-asr-streaming-0.6b-q5_k.gguf" \
  --input "${1:?Usage: transcribe.sh <audio.wav>}" \
  --threads "$(sysctl -n hw.ncpu)"
