# Real-Time STT with Google Speech API

Real-time speech-to-text experiments using the Google Cloud Speech-to-Text API. Includes a CLI microphone transcriber and two browser-based WebSocket servers — one for low-latency streaming and one for speaker diarization.

## Modes

| Script | API | Model | Notes |
|---|---|---|---|
| `microphone_transcribe.py` | Speech v2 | Chirp 2 | CLI — mic → terminal, interim results |
| `server_streaming.py` | Speech v2 | Chirp 2 | Browser WebSocket, streaming with interim results |
| `server_diarize.py` | Speech v1 | latest_long | Browser WebSocket, batches 5 s segments, speaker diarization |

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`microphone_transcribe.py` also requires **PyAudio** and its system dependency PortAudio:

```bash
# macOS
brew install portaudio
pip install pyaudio
```

### 2. Google Cloud credentials

See [CONFIGURATION.md](CONFIGURATION.md) for the full ADC setup. In short:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
```

### 3. Environment variables

Copy `.env` and set your project ID:

```
GOOGLE_CLOUD_PROJECT=your-project-id
```

The `server_streaming.py` and `server_diarize.py` scripts load this automatically via `python-dotenv`.

## Usage

### CLI transcription

Streams microphone audio directly to Google Speech and prints transcripts to the terminal. Say "exit" or "quit" to stop.

```bash
python microphone_transcribe.py
```

### Streaming server (browser UI)

Serves a browser UI at `http://localhost:8000`. The browser captures microphone audio and sends it over a WebSocket. The server pipes it through the Speech v2 streaming API and sends back interim and final transcripts in real time.

```bash
python server_streaming.py
# optional connection test:
python server_streaming.py test
```

### Diarization server (browser UI)

Same browser UI, but uses the Speech v1 batch API with speaker diarization enabled. Audio is buffered in 5-second segments (or flushed on silence) before being sent to the API. Each response includes per-word speaker tags.

```bash
python server_diarize.py
# optional connection test:
python server_diarize.py test
```

## Architecture

```
Browser (getUserMedia)
  │  raw PCM (LINEAR16, 16 kHz, mono)
  │  WebSocket binary frames
  ▼
FastAPI server (uvicorn)
  │  asyncio.Queue
  ▼
Google Cloud Speech API
  │  transcripts (JSON)
  ▼
Browser (WebSocket text)
```

The `server_streaming.py` server transparently reconnects the gRPC stream when the 5-minute Google streaming limit is hit (`DeadlineExceeded` / `OutOfRange`).

## Audio format

All paths expect **16-bit mono PCM at 16 000 Hz** (`LINEAR16`). The browser `app.js` captures audio at this rate using the Web Audio API before sending it over the WebSocket.
