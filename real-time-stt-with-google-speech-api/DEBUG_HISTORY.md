# Debug History

## Session: instant-disconnect on connect (2026-06-25)

**Symptom:** Browser connects, shows "Listening...", then immediately disconnects and
reverts to "Ready" with no error visible.

---

### Bug 1 — Wrong location in recognizer path

**File:** `server_streaming.py`

```python
# before
RECOGNIZER = f"projects/{PROJECT_ID}/locations/global/recognizers/_"

# after
LOCATION = "us-central1"
RECOGNIZER = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/_"
```

`chirp_2` is a regional model and is not available at the `global` endpoint. The
Google API rejected the streaming config immediately, causing `_run_recognition` to
exit, which closed the WebSocket before any audio was processed.

Spotted by comparing against the working `microphone_transcribe.py`, which used
`us-central1`.

---

### Bug 2 — Missing regional gRPC endpoint on the async client

**File:** `server_streaming.py`

```python
# before
client = SpeechAsyncClient()

# after
client = SpeechAsyncClient(
    client_options=ClientOptions(api_endpoint=f"{LOCATION}-speech.googleapis.com")
)
```

Without `ClientOptions`, the async client connects to the global gRPC endpoint
(`speech.googleapis.com`) instead of `us-central1-speech.googleapis.com`. Combined
with Bug 1, the API call failed before receiving a single audio frame.

Again spotted by comparing with `microphone_transcribe.py`, which passed
`ClientOptions(api_endpoint=f"{LOCATION}-speech.googleapis.com")` to its
`SpeechClient`.

---

### Bug 3 — `await` incorrectly removed from `streaming_recognize` call

**File:** `server_streaming.py`

```python
# original (correct)
async for response in await client.streaming_recognize(requests=audio_gen()):

# incorrectly changed to
async for response in client.streaming_recognize(requests=audio_gen()):

# reverted back to
async for response in await client.streaming_recognize(requests=audio_gen()):
```

After fixing Bugs 1 and 2, a probe in `test_connection` gave an ambiguous signal
and led to a wrong conclusion that `streaming_recognize` returned an async iterator
directly (no `await` needed). Removing the `await` introduced a new crash:

```
[error] "'async for' requires an object with __aiter__ method, got coroutine"
```

`streaming_recognize` on `SpeechAsyncClient` is a coroutine — it must be awaited
to obtain the async iterator of responses. The `await` was correct in the original
code. This bug was caught by the WebSocket end-to-end test (`ws_test.py`) before it
could be mistaken for a fix.

---

### How the bugs were found

- Bugs 1 & 2 were found by code inspection — diffing `server_streaming.py` against the
  known-working `microphone_transcribe.py`.
- Bug 3 was introduced during debugging and caught by the live WebSocket test
  (`ws_test.py`), which checks that the server stream stays open for 5 seconds
  without an error frame or abnormal close.
