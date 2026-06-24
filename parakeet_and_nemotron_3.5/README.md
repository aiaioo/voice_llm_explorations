# parakeet.cpp Shell Scripts

These scripts wrap `parakeet-cli` and `parakeet-server` with the Nemotron 3.5
model (`nemotron-3.5-asr-streaming-0.6b-q5_k.gguf`) and auto-detect the CPU
thread count. All scripts must be run from the project root or any directory —
paths are resolved relative to the script location.

## Prerequisites

- `parakeet-cli` and `parakeet-server` binaries in the project root
- `models/nemotron-3.5-asr-streaming-0.6b-q5_k.gguf` downloaded
- Audio files must be WAV format (mono or stereo, any sample rate — resampled
  to 16 kHz automatically)

---

## transcribe.sh — Offline transcription

Transcribes a WAV file in one shot after the full audio has been read.

```sh
./transcribe.sh <audio.wav>
```

**Example:**
```sh
./transcribe.sh audio.wav
# The quick brown fox jumps over the lazy dog. Automatic speech recognition is working correctly.
```

Use this when you want the complete transcript returned as a single result.
Slower on large files than streaming, but the output is cleaner (no chunk
boundaries).

---

## transcribe-stream.sh — Cache-aware streaming transcription

Feeds audio through the model in small chunks and prints tokens to stdout as
each chunk is processed, simulating real-time transcription. Also emits
`[EOU @ Xs]` markers where the model detects utterance boundaries.

```sh
./transcribe-stream.sh <audio.wav>
```

**Example:**
```sh
./transcribe-stream.sh audio.wav
# [stream] The quick brown fox jumps over the lazy dog. [EOU @ 2.34s] Automatic speech recognition is working correctly.
# [stream:final] The quick brown fox jumps over the lazy dog. Automatic speech recognition is working correctly.
```

The `[stream:final]` line at the end contains the complete transcript for easy
capture. This mode requires a streaming-capable model (Nemotron 3.5 qualifies).

---

## transcription-server.sh — Start the OpenAI-compatible HTTP server

Starts `parakeet-server`, which exposes a `POST /v1/audio/transcriptions`
endpoint compatible with the OpenAI audio transcription API.

```sh
./transcription-server.sh
```

The server listens on `127.0.0.1:8080` by default. Override with environment
variables:

```sh
PORT=9090 ./transcription-server.sh
HOST=0.0.0.0 PORT=8080 ./transcription-server.sh   # expose to the network
```

The server runs in the foreground. Press `Ctrl+C` to stop it.

---

## test-server.sh — Send a WAV file to the running server

POSTs a WAV file to the local server and prints the JSON response. The server
must already be running (see `transcription-server.sh` above).

```sh
./test-server.sh <audio.wav>
```

**Example:**
```sh
./test-server.sh audio.wav
# {"text":"The quick brown fox jumps over the lazy dog. Automatic speech recognition is working correctly."}
```

To target a different host or port, set the URL directly in the curl call or
edit the script.
