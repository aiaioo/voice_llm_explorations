# Real-time Speech-to-Text using AssemblyAI

A browser-based live transcription app built with a Python/Flask backend and a vanilla JavaScript front-end. Speak into your microphone and watch your words appear on screen in real time, labelled by speaker with timestamps.

**Author:** Claude Sonnet 4.6 (Anthropic)

---

## What it does

- **Live transcription** — streams microphone audio directly to AssemblyAI's Universal-3 Pro Streaming model and displays each turn of speech as it is finalised.
- **Speaker diarization** — automatically identifies and labels distinct speakers (`Speaker A`, `Speaker B`, …), each with its own colour, so you can follow multi-person conversations at a glance.
- **Timestamps** — every finalised turn shows its start and end time (e.g. `0:03.2 – 0:11.7`) derived from word-level timing data returned by the API.
- **Partial transcripts** — in-progress speech appears in real time as italic placeholder text while AssemblyAI is still processing, then snaps into a final turn when the speaker pauses.
- **Secure by design** — the API key never leaves the server. The browser fetches a short-lived ephemeral token from the Flask backend, then opens a WebSocket connection directly to AssemblyAI's endpoint using that token. Raw audio is never routed through the Python server.

---

## Architecture

```
Browser                               AssemblyAI
───────                               ──────────
Microphone
  │ getUserMedia
  ▼
AudioContext (16 kHz)
  │ AudioWorklet (PCM processor)
  │ Float32 → Int16, 800-sample chunks
  │
  │  1. GET /token ──────────► Flask (server.py)
  │  ◄── { token } ───────────     │
  │                                │ GET https://streaming.assemblyai.com/v3/token
  │                                ◄── { token }
  │
  │  2. WSS (token in query string) ──────────────► wss://streaming.assemblyai.com/v3/ws
  │     Binary PCM frames ─────────────────────────►
  │  ◄── Turn / SpeechStarted / Termination ────────
  │
  ▼
Transcript panel (HTML)
```

---

## Getting started

### Prerequisites

- Python 3.8+
- An [AssemblyAI API key](https://www.assemblyai.com/dashboard/api-keys)
- A working microphone

### Installation

```bash
git clone https://github.com/aiaioo/voice_llm_explorations.git
cd voice_llm_explorations/real-time-stt-using-assembly-ai

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Create a `.env` file in this directory:

```
ASSEMBLYAI_API_KEY=your_api_key_here
```

### Run

```bash
python server.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser, click the microphone button, and start speaking.

---

## How it works

### Backend (`server.py`)

The Flask server exposes two endpoints:

| Route | Description |
|-------|-------------|
| `GET /` | Serves the single-page HTML/JS front-end |
| `GET /token` | Calls AssemblyAI's token API and returns a short-lived streaming token |

The token has a redemption window of 600 seconds and allows sessions up to 30 minutes long (`max_session_duration_seconds=1800`). Tokens are one-time-use — once the WebSocket opens, the token is consumed.

### Front-end (embedded in `server.py`)

The entire UI is a single HTML page with inline CSS and JavaScript — no build step, no dependencies, no bundler.

**Audio pipeline:**

1. `getUserMedia` requests mono microphone access with echo and noise cancellation.
2. An `AudioContext` is created at 16 kHz.
3. An `AudioWorklet` processor (`PCMProcessor`) buffers incoming Float32 samples into 800-sample chunks (~50 ms), converts them to 16-bit signed integers, and posts each chunk as an `ArrayBuffer` to the main thread.
4. The main thread forwards each chunk as a binary WebSocket frame to AssemblyAI.

**Transcript rendering:**

- Partial turns (`end_of_turn: false`) are shown as italic placeholder text, updated in place.
- A turn is finalised when `end_of_turn: true` **and** `turn_is_formatted: true` — at that point it is committed to the panel as a permanent entry.
- Each entry shows a coloured speaker badge, the start–end timestamp, and the transcript text.
- The panel auto-scrolls to the latest entry.

### AssemblyAI features used

| Feature | Parameter |
|---------|-----------|
| Universal-3 Pro Streaming model | `speech_model=universal-3-5-pro` |
| Speaker diarization | `speaker_labels=true` |
| Ephemeral token auth | `GET /v3/token` + token as query param |

---

## Speaker colours

Speakers are assigned colours in order of first appearance:

| Speaker | Colour |
|---------|--------|
| A | Indigo |
| B | Emerald |
| C | Amber |
| D | Rose |
| E | Cyan |
| F | Violet |
| G | Pink |
| H | Lime |

---

## Notes

- Speaker accuracy improves over the course of a session as AssemblyAI accumulates voice embedding context. Expect better labels after ~30 seconds per speaker.
- Sessions are billed on WebSocket open time, not audio sent. The app always sends a `Terminate` message on stop and waits for the `Termination` response before closing, ensuring the final transcript is not dropped and the session is closed cleanly.
- The `AudioWorklet` code is loaded via a Blob URL so no additional files are needed — the entire app is self-contained in `server.py`.
