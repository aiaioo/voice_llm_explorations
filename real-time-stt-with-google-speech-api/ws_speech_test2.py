"""
Send a raw PCM audio file over the WebSocket and collect the full transcript.

Receives messages concurrently while sending, then waits after sending
completes so the server has time to flush the final segment. Prefer this
over ws_speech_test.py when you need to see all results.

Usage:
    python ws_speech_test2.py <audio.raw> [ws://127.0.0.1:8000/ws]

The audio file must be 16 kHz, 16-bit signed little-endian, mono PCM.
Convert with ffmpeg:
    ffmpeg -i input.wav -ar 16000 -ac 1 -f s16le audio.raw
"""
import asyncio
import json
import sys

import websockets

CHUNK = 3200  # 100 ms @ 16 kHz 16-bit mono
WAIT_AFTER_SEND = 20  # seconds to wait for the final segment result

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

AUDIO_FILE = sys.argv[1]
URI = sys.argv[2] if len(sys.argv) > 2 else "ws://127.0.0.1:8000/ws"


async def main():
    with open(AUDIO_FILE, "rb") as f:
        audio = f.read()
    print(f"Audio: {len(audio)} bytes ({len(audio) / 32000:.1f} s)")
    print(f"Target: {URI}\n")

    msgs = []

    async def recv_loop(ws):
        try:
            async for raw in ws:
                msg = json.loads(raw)
                print(f"  <- {msg}")
                msgs.append(msg)
        except Exception as e:
            print(f"  recv done: {e}")

    async with websockets.connect(URI) as ws:
        recv_task = asyncio.create_task(recv_loop(ws))

        for i in range(0, len(audio), CHUNK):
            await ws.send(audio[i : i + CHUNK])
            await asyncio.sleep(0.01)

        print(f"All audio sent. Waiting up to {WAIT_AFTER_SEND} s for remaining transcript...")
        await asyncio.sleep(WAIT_AFTER_SEND)
        recv_task.cancel()

    print(f"\nTotal messages: {len(msgs)}")


asyncio.run(main())
