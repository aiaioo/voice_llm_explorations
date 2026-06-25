"""
Probe: send less than one segment's worth of audio, then close immediately.

Verifies that the server flushes its buffer on disconnect and the API call
fires (visible in server logs as "Waiting for background tasks to complete"
on shutdown). The transcript cannot be delivered to the caller because the
WebSocket is already closed — this is expected behavior.

Usage:
    python ws_close_probe.py <audio.raw> [ws://127.0.0.1:8000/ws]

The audio file must be 16 kHz, 16-bit signed little-endian, mono PCM.
Convert with ffmpeg:
    ffmpeg -i input.wav -ar 16000 -ac 1 -f s16le audio.raw
"""
import asyncio
import json
import sys

import websockets

CHUNK = 3200       # 100 ms @ 16 kHz 16-bit mono
CLIP_BYTES = 96000  # first 3 s — stays below the 5-s segment boundary

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

AUDIO_FILE = sys.argv[1]
URI = sys.argv[2] if len(sys.argv) > 2 else "ws://127.0.0.1:8000/ws"


async def main():
    with open(AUDIO_FILE, "rb") as f:
        audio = f.read()[:CLIP_BYTES]
    print(f"Audio: {len(audio)} bytes ({len(audio) / 32000:.1f} s)")
    print(f"Target: {URI}\n")

    msgs = []

    async with websockets.connect(URI) as ws:
        async def recv_loop():
            try:
                async for raw in ws:
                    msgs.append(json.loads(raw))
            except Exception:
                pass

        recv_task = asyncio.create_task(recv_loop())
        for i in range(0, len(audio), CHUNK):
            await ws.send(audio[i : i + CHUNK])
            await asyncio.sleep(0.01)

        print("Closing immediately (before 5-s segment boundary)...")
        await ws.close()
        await asyncio.sleep(2)
        recv_task.cancel()

    if msgs:
        print(f"Messages received: {msgs}")
    else:
        print("No messages received (expected — WebSocket closed before server could reply).")
        print("Check server logs: 'Waiting for background tasks to complete' confirms the API call fired.")


asyncio.run(main())
