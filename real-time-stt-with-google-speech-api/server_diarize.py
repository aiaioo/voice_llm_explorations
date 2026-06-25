import asyncio
import json
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from google.cloud import speech

load_dotenv()

app = FastAPI()
STATIC_DIR = Path(__file__).parent / "static"
SAMPLE_RATE = 16000

# Batch up to this many seconds of audio before sending to the API.
SEGMENT_SECONDS = 5
SEGMENT_BYTES = SAMPLE_RATE * 2 * SEGMENT_SECONDS  # 16-bit mono PCM


def _make_recognition_config() -> speech.RecognitionConfig:
    return speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE,
        language_code="en-US",
        diarization_config=speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=1,
            max_speaker_count=6,
        ),
    )


async def _transcribe_segment(
    client: speech.SpeechAsyncClient,
    audio_bytes: bytes,
    websocket: WebSocket,
) -> None:
    if not audio_bytes:
        return
    try:
        response = await client.recognize(
            config=_make_recognition_config(),
            audio=speech.RecognitionAudio(content=audio_bytes),
        )
        if not response.results:
            return
        # With diarization enabled, the last result re-gathers all words with
        # speaker_tag assigned. Earlier results have transcripts but no tags.
        alt = response.results[-1].alternatives[0]
        words = [{"word": w.word, "speaker_tag": w.speaker_tag} for w in alt.words]
        await websocket.send_text(json.dumps({
            "type": "final",
            "transcript": alt.transcript or " ".join(w["word"] for w in words),
            "words": words,
        }))
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass


async def _run_recognition(
    audio_q: asyncio.Queue,
    websocket: WebSocket,
) -> None:
    client = speech.SpeechAsyncClient()
    buffer = bytearray()

    while True:
        try:
            chunk = await asyncio.wait_for(audio_q.get(), timeout=float(SEGMENT_SECONDS))
        except asyncio.TimeoutError:
            # Silence gap — flush whatever has accumulated.
            if buffer:
                await _transcribe_segment(client, bytes(buffer), websocket)
                buffer.clear()
            continue

        if chunk is None:
            # WebSocket closed — flush and exit.
            if buffer:
                await _transcribe_segment(client, bytes(buffer), websocket)
            break

        buffer.extend(chunk)
        if len(buffer) >= SEGMENT_BYTES:
            await _transcribe_segment(client, bytes(buffer), websocket)
            buffer.clear()


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    audio_q: asyncio.Queue = asyncio.Queue()

    async def recv_audio() -> None:
        try:
            while True:
                data = await websocket.receive_bytes()
                await audio_q.put(bytes(data))
        except WebSocketDisconnect:
            pass
        finally:
            await audio_q.put(None)

    recv_task = asyncio.create_task(recv_audio())
    recog_task = asyncio.create_task(_run_recognition(audio_q, websocket))

    await asyncio.gather(recv_task, recog_task, return_exceptions=True)


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


async def test_connection() -> None:
    """Send a second of silence through recognize to verify credentials
    and that diarization config is accepted."""
    import sys

    print("API    : Speech-to-Text v1 (global endpoint)")
    print("Model  : latest_long (with speaker diarization)")
    print()

    client = speech.SpeechAsyncClient()
    silence = bytes(SAMPLE_RATE * 2)
    try:
        await client.recognize(
            config=_make_recognition_config(),
            audio=speech.RecognitionAudio(content=silence),
        )
        print("PASS — batch recognize with diarization config accepted.")
    except Exception as exc:
        print(f"FAIL — {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_connection())
    else:
        uvicorn.run(app, host="127.0.0.1", port=8000)
