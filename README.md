# Voice & LLM Explorations

A collection of experiments in real-time speech-to-text, voice chat, and audio translation using various cloud APIs and local models.

## Subprojects

| Subproject | Stack | What it does |
|---|---|---|
| [real-time-stt-using-assembly-ai](real-time-stt-using-assembly-ai/) | AssemblyAI, Flask, vanilla JS | Browser STT with speaker diarization and timestamps |
| [real-time-stt-with-google-speech-api](real-time-stt-with-google-speech-api/) | Google Cloud Speech, FastAPI, vanilla JS | CLI + browser STT; streaming (Chirp 2) and diarization modes |
| [chatting-with-gemini-live](chatting-with-gemini-live/) | Gemini Live API, Python, vanilla JS | Real-time voice/video chat with Gemini using ephemeral tokens |
| [translating-with-gemini-live](translating-with-gemini-live/) | Gemini Live API, Python, vanilla JS | Real-time spoken language translation via Gemini Live |
| [parakeet_and_nemotron_3.5](parakeet_and_nemotron_3.5/) | parakeet-cli/server, Nemotron 3.5 | Fully local offline STT; OpenAI-compatible HTTP server |

---

### [real-time-stt-using-assembly-ai](real-time-stt-using-assembly-ai/)

Browser-based live transcription using AssemblyAI's Universal-3 Pro streaming model. The Python backend mints a short-lived ephemeral token so the API key never reaches the browser. Audio goes straight from the browser to AssemblyAI over a WebSocket. Features speaker diarization with per-speaker colour coding and word-level timestamps.

**Quick start:**
```bash
cd real-time-stt-using-assembly-ai
pip install -r requirements.txt
echo "ASSEMBLYAI_API_KEY=your_key" > .env
python server.py          # http://localhost:8000
```

---

### [real-time-stt-with-google-speech-api](real-time-stt-with-google-speech-api/)

Three modes built on Google Cloud Speech-to-Text:

- **CLI** (`microphone_transcribe.py`) — mic → terminal, interim results, uses Speech v2 / Chirp 2
- **Streaming server** (`server_streaming.py`) — browser UI, real-time interim + final transcripts, auto-reconnects at the 5-minute gRPC limit
- **Diarization server** (`server_diarize.py`) — browser UI, batches 5-second audio segments, returns per-word speaker tags via Speech v1

Auth uses Google Application Default Credentials (ADC). See [CONFIGURATION.md](real-time-stt-with-google-speech-api/CONFIGURATION.md) for setup.

**Quick start:**
```bash
cd real-time-stt-with-google-speech-api
pip install -r requirements.txt
cp .env.example .env      # set GOOGLE_CLOUD_PROJECT
python server_streaming.py    # http://localhost:8000
```

---

### [chatting-with-gemini-live](chatting-with-gemini-live/)

Voice and video chat with Gemini using the Gemini Live API. The Python backend issues ephemeral tokens; the vanilla JS frontend connects directly to `generativelanguage.googleapis.com`, keeping media latency low. Supports custom tool definitions (function calling), device selection, and audio/video/text response modes.

Adapted from the [google-gemini/gemini-live-api-examples](https://github.com/google-gemini/gemini-live-api-examples) repository.

**Quick start:**
```bash
cd chatting-with-gemini-live
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key" > .env
uv run server.py          # http://localhost:8000
```

---

### [translating-with-gemini-live](translating-with-gemini-live/)

Real-time spoken language translation using the Gemini Live API. Same architecture as `chatting-with-gemini-live` (ephemeral tokens, direct browser WebSocket) but configured to demonstrate Gemini Live's translation capabilities. Also adapted from the google-gemini examples repository.

**Quick start:**
```bash
cd translating-with-gemini-live
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key" > .env
uv run server.py          # http://localhost:8000
```

---

### [parakeet_and_nemotron_3.5](parakeet_and_nemotron_3.5/)

Fully local, offline speech transcription using `parakeet-cli` and `parakeet-server` with the Nemotron 3.5 ASR streaming model (`nemotron-3.5-asr-streaming-0.6b-q5_k.gguf`). No cloud credentials required. Provides three shell-script entry points:

| Script | What it does |
|---|---|
| `transcribe.sh <file.wav>` | One-shot batch transcription |
| `transcribe-stream.sh <file.wav>` | Streaming transcription with EOU markers |
| `transcription-server.sh` | OpenAI-compatible `POST /v1/audio/transcriptions` server |

**Quick start:**
```bash
cd parakeet_and_nemotron_3.5
# download parakeet-cli / parakeet-server binaries and the model — see README
./transcribe.sh audio.wav
```
