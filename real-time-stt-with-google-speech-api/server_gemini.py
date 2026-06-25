import asyncio
import json
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from google.api_core.exceptions import Cancelled, DeadlineExceeded, OutOfRange
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechAsyncClient
from google.cloud.speech_v2.types import cloud_speech

load_dotenv()

app = FastAPI()
STATIC_DIR = Path(__file__).parent / "static"
SAMPLE_RATE = 16000
PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = "us-central1"
RECOGNIZER = f"projects/{PROJECT_ID}/locations/{LOCATION}/recognizers/_"


def _make_streaming_config() -> cloud_speech.StreamingRecognitionConfig:
    return cloud_speech.StreamingRecognitionConfig(
        config=cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=SAMPLE_RATE,
                audio_channel_count=1,
            ),
            language_codes=["en-US"],
            model="chirp_2",
        ),
        streaming_features=cloud_speech.StreamingRecognitionFeatures(
            interim_results=True,
        ),
    )


async def _run_recognition(
    audio_q: asyncio.Queue,
    websocket: WebSocket,
) -> None:
    client = SpeechAsyncClient(
        client_options=ClientOptions(api_endpoint=f"{LOCATION}-speech.googleapis.com")
    )
    streaming_config = _make_streaming_config()

    done = False
    while not done:
        stop = asyncio.Event()

        async def audio_gen():
            yield cloud_speech.StreamingRecognizeRequest(
                recognizer=RECOGNIZER,
                streaming_config=streaming_config,
            )
            while not stop.is_set():
                try:
                    chunk = await asyncio.wait_for(audio_q.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                if chunk is None:
                    stop.set()
                    return
                yield cloud_speech.StreamingRecognizeRequest(audio=chunk)

        try:
            async for response in await client.streaming_recognize(requests=audio_gen()):
                for result in response.results:
                    if not result.alternatives:
                        continue
                    transcript = result.alternatives[0].transcript
                    if result.is_final:
                        await websocket.send_text(json.dumps({
                            "type": "final",
                            "transcript": transcript,
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "interim",
                            "transcript": transcript,
                        }))
        except (DeadlineExceeded, OutOfRange):
            # streaming limit hit — reconnect transparently
            pass
        except Cancelled:
            done = True
        except Exception as e:
            try:
                await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
            except Exception:
                pass
            done = True

        if stop.is_set():
            done = True


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

    _, pending = await asyncio.wait(
        [recv_task, recog_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


async def test_connection() -> None:
    """Send a few hundred ms of silence through streaming_recognize to verify
    the gRPC connection, credentials, regional endpoint, and chirp_2 model."""
    import sys

    print(f"Endpoint  : {LOCATION}-speech.googleapis.com")
    print(f"Recognizer: {RECOGNIZER}")
    print(f"Model     : chirp_2")
    print()

    client = SpeechAsyncClient(
        client_options=ClientOptions(api_endpoint=f"{LOCATION}-speech.googleapis.com")
    )
    streaming_config = _make_streaming_config()

    # 1 second of silence: 16000 samples × 2 bytes each
    silence = bytes(SAMPLE_RATE * 2)
    chunk_bytes = SAMPLE_RATE * 2 // 10  # 100 ms per chunk

    async def _requests():
        yield cloud_speech.StreamingRecognizeRequest(
            recognizer=RECOGNIZER,
            streaming_config=streaming_config,
        )
        for i in range(0, len(silence), chunk_bytes):
            yield cloud_speech.StreamingRecognizeRequest(audio=silence[i : i + chunk_bytes])

    try:
        async for _ in await client.streaming_recognize(requests=_requests()):
            pass  # silence produces no transcript; receiving any response is fine
        print("PASS — gRPC connection to Google Speech API is working.")
    except Exception as exc:
        print(f"FAIL — {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_connection())
    else:
        uvicorn.run(app, host="127.0.0.1", port=8000)
