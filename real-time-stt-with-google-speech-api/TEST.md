# Testing

Two tests are available. Run them in order: the gRPC test is fast and confirms the
foundation; the WebSocket test exercises the full server stack.

---

## 1. gRPC connection test — `python server_gemini.py test`

### What it covers

Verifies everything between the server and Google's Speech API without starting the
HTTP/WebSocket server:

| Check | Detail |
|---|---|
| ADC credentials | `~/.config/gcloud/application_default_credentials.json` is valid and not expired |
| Quota project | Billing is correctly attributed to `GOOGLE_CLOUD_PROJECT` |
| Regional endpoint | `us-central1-speech.googleapis.com` is reachable |
| Recognizer path | `projects/<id>/locations/us-central1/recognizers/_` is accepted |
| `chirp_2` model | The model is available and accepts streaming requests |
| Streaming protocol | `streaming_recognize` opens, accepts audio, and closes cleanly |

It does **not** test transcript quality — it sends 1 second of silence, which
produces no results.

### How to run

```bash
python server_gemini.py test
```

### Expected output (pass)

```
Endpoint  : us-central1-speech.googleapis.com
Recognizer: projects/premium-apex-438701-g0/locations/us-central1/recognizers/_
Model     : chirp_2

PASS — gRPC connection to Google Speech API is working.
```

### Common failures

| Error | Likely cause |
|---|---|
| `google.auth.exceptions.DefaultCredentialsError` | ADC not configured — run `gcloud auth application-default login` |
| `PermissionDenied` | Speech API not enabled, or quota project wrong — check `GOOGLE_CLOUD_PROJECT` in `.env` |
| `NotFound` / `InvalidArgument` on model | `chirp_2` not available in `us-central1` for your project — try changing `LOCATION` in `server_gemini.py` |
| `DeadlineExceeded` / connection timeout | Network/firewall blocking `us-central1-speech.googleapis.com:443` |

---

## 2. WebSocket end-to-end test — `ws_test.py`

### What it covers

Connects to the running server's WebSocket endpoint and exercises the full path:
browser → server → Google Speech API → server → client.

| Check | Detail |
|---|---|
| Server accepts WebSocket connections | `ws://127.0.0.1:8766/ws` upgrades correctly |
| Audio pipeline | Binary PCM frames flow from client through to `streaming_recognize` |
| Stream stability | Connection stays open for 5 s without being closed by the server |
| Error messages | Any `{"type": "error"}` frames from the server are printed and flagged |
| Reconnect loop | Server's `DeadlineExceeded`/`OutOfRange` handler is not triggered within 5 s |

It sends 3 seconds of a 440 Hz sine tone followed by 2 seconds of silence. Neither
produces a transcript — the pass condition is that the stream **stays open**, not
that words appear. To test actual transcription, speak into the browser UI.

### Prerequisites

The `websockets` package is required and is not in `requirements.txt`:

```bash
pip install websockets
```

The server must be running in another terminal before you start the test:

```bash
python server_gemini.py
```

### How to run

```bash
python ws_test.py
```

### Expected output (pass)

```
Connecting to ws://127.0.0.1:8766/ws ...
Connected. Sending audio ...

PASS — stream stayed open for 5 s. 0 message(s) received.
```

Zero messages is correct — silence and a pure tone produce no transcript.

### Output when the server sends an error but stays connected

The test still passes, but the error is surfaced:

```
PASS — stream stayed open for 5 s. 1 message(s) received.
  ⚠  Server sent 1 error message(s):
     <error text from Google API>
```

### Output when the server disconnects immediately (fail)

```
Connected. Sending audio ...
  Connection closed unexpectedly: code=1006 reason=''
FAIL — server closed the connection unexpectedly (immediate disconnect bug still present).
```

This was the original symptom that prompted these tests. If you see it again, run
the gRPC test first to isolate whether the problem is in the Google API layer or the
WebSocket layer.

---

## Audio format

Both tests use the same format that the browser's AudioWorklet sends:

- Encoding: **LINEAR16** (signed 16-bit PCM, little-endian)
- Sample rate: **16 000 Hz**
- Channels: **1 (mono)**
- Chunk size: **1 600 samples = 100 ms per frame**
