# Testing

Two tests are available. Run them in order: the gRPC test is fast and confirms the
foundation; the WebSocket test exercises the full server stack.

---

## 1. gRPC connection test — `python server_streaming.py test`

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
python server_streaming.py test
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
| `NotFound` / `InvalidArgument` on model | `chirp_2` not available in `us-central1` for your project — try changing `LOCATION` in `server_streaming.py` |
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
python server_streaming.py
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

---

# Testing server_diarize.py (batch mode)

Four dedicated scripts drive the `/ws` endpoint of `server_diarize.py`, which
uses the batch `recognize()` API instead of streaming. All scripts default to
`ws://127.0.0.1:8000/ws`; pass a different URI as the last argument to target
another host or port.

## Prerequisites

Start the server before running any script:

```bash
python server_diarize.py
```

### Built-in connection test

Verify credentials, regional endpoint, and the chirp_2 batch model without
starting the WebSocket server:

```bash
python server_diarize.py test
```

Expected output:

```
Endpoint  : us-central1-speech.googleapis.com
Recognizer: projects/<project-id>/locations/us-central1/recognizers/_
Model     : chirp_2 (batch)

PASS — batch recognize connection to Google Speech API is working.
```

### Preparing a real audio file

Three of the four scripts require a raw PCM file: 16 kHz, 16-bit signed
little-endian, mono (matching the format the browser AudioWorklet sends).

#### What was used during verification

The test file was derived from `../parakeet_and_nemotron_3.5/audio.wav`, a
~6-second clip that already contained suitable speech. Its original format:

| Property | Value |
|---|---|
| Codec | PCM 32-bit float little-endian (`pcm_f32le`) |
| Sample rate | 16 000 Hz |
| Channels | 1 (mono) |
| Duration | ~6.15 s |

Because the sample rate and channel count were already correct, ffmpeg only
needed to convert the sample format from 32-bit float to 16-bit signed integer,
and trim to exactly 6 seconds:

```bash
ffmpeg -i ../parakeet_and_nemotron_3.5/audio.wav \
       -ar 16000 \   # keep sample rate (no resampling needed)
       -ac 1 \       # keep mono (no downmix needed)
       -f s16le \    # output format: signed 16-bit little-endian raw PCM
       -t 6 \        # trim to 6 s (crosses the 5-s segment boundary)
       /tmp/speech_test.raw
```

The resulting file was 192 000 bytes (16 000 samples/s × 2 bytes/sample × 6 s).
The batch API transcribed it as:

```
the quick brown fox jumps over the lazy dog automatic speech recognition is
working correctly
```

Split across two `final` messages — one at the 5-second segment boundary and
one from the silence-timeout flush of the remaining ~1 second.

#### Converting your own file

The general-purpose command (resamples and downmixes as needed):

```bash
ffmpeg -i input.wav -ar 16000 -ac 1 -f s16le audio.raw
```

To trim to a specific duration, add `-t <seconds>` before the output path.
The output file will be exactly `sample_rate × 2 × duration` bytes.

---

## ws_verify.py — smoke tests (no audio file needed)

Runs three self-contained checks using synthesized sine-wave audio. Use this
first to confirm the server is up and the segment-boundary logic works before
reaching for real audio.

```bash
python ws_verify.py
# or against a different server:
python ws_verify.py ws://192.168.1.10:8000/ws
```

| Test | What it checks |
|---|---|
| 1 — pure tone (3 s) | Server does not crash on non-speech audio; no error messages |
| 2 — immediate close | Empty-buffer flush is safe |
| 3 — segment boundary (6 s) | Batch API fires at the 5-second mark and a `final` message arrives |

Sample output:

```
=== TEST 1: 3 s of 440 Hz sine (no transcript expected) ===
  Messages: (none — expected for pure tone)
=== TEST 2: immediate close with empty buffer ===
  Messages: (none — expected, nothing to flush)
=== TEST 3: 6 s of sine — crosses 5-second segment boundary ===
  Messages: [{'type': 'final', 'transcript': 'u'}]
  Segment boundary fired correctly.
```

The one-character transcript in Test 3 is the Speech API trying to interpret a
pure tone. Any non-error response confirms the batch call fired.

---

## ws_speech_test.py — basic real-audio send

Sends a full audio file and closes immediately after the last chunk. Only
messages that arrive before the close completes are captured.

```bash
python ws_speech_test.py audio.raw
```

Audio shorter than 5 seconds will likely produce no output because the
connection closes before the silence timeout fires the batch call. Switch to
`ws_speech_test2.py` in that case.

---

## ws_speech_test2.py — real-audio send with full transcript (preferred)

Sends the full audio file while concurrently receiving messages, then waits
20 seconds after the last chunk so the server can flush the final partial
segment. This is the most reliable way to see the complete transcript.

```bash
python ws_speech_test2.py audio.raw
```

Sample output for a 6-second clip:

```
Audio: 192000 bytes (6.0 s)
Target: ws://127.0.0.1:8000/ws

All audio sent. Waiting up to 20 s for remaining transcript...
  <- {'type': 'final', 'transcript': 'the quick brown fox jumps over the lazy dog'}
  <- {'type': 'final', 'transcript': 'automatic speech recognition is working correctly'}

Total messages: 2
```

Two messages appear because the 6-second clip crosses the 5-second boundary:
the first segment is sent at the boundary, and the remaining ~1 second is
flushed by the 5-second silence timeout.

---

## ws_close_probe.py — early-close behaviour

Sends the first 3 seconds of audio (below the 5-second segment boundary), then
closes immediately. Verifies that the server flushes its buffer on disconnect
and actually calls the batch API, even though the result cannot be returned.

```bash
python ws_close_probe.py audio.raw
```

Expected output:

```
Audio: 96000 bytes (3.0 s)
Closing immediately (before 5-s segment boundary)...
No messages received (expected — WebSocket closed before server could reply).
Check server logs: 'Waiting for background tasks to complete' confirms the API call fired.
```

The server log line `Waiting for background tasks to complete` (seen when you
stop the server with Ctrl-C shortly after this probe) confirms the API call
fired. The result cannot be delivered because the WebSocket is already closed —
this is expected behaviour.

---

## Segment timing summary

| Audio duration | Client stays open? | Result |
|---|---|---|
| < 5 s | Yes | Nothing delivered until the 5-second silence timeout fires |
| ≥ 5 s | Yes | `final` message at the boundary; remainder flushed on silence timeout |
| Any length | Closes early | Buffer flushed, API called, but transcript cannot be delivered |

The 5-second threshold is controlled by `SEGMENT_SECONDS` in `server_diarize.py`.
