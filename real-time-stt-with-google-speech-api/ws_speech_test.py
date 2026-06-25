"""
Send a raw PCM audio file over the WebSocket and print the transcript.

Closes the connection immediately after sending — only receives messages
that arrive before the close completes. Use ws_speech_test2.py to wait
for the full transcript after sending.

Usage:
    python ws_speech_test.py <audio.raw> [ws://127.0.0.1:8000/ws]

The audio file must be 16 kHz, 16-bit signed little-endian, mono PCM.
Convert with ffmpeg:
    ffmpeg -i input.wav -ar 16000 -ac 1 -f s16le audio.raw
"""
import asyncio
import json
import sys

import websockets

CHUNK = 3200  # 100 ms @ 16 kHz 16-bit mono

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
    async with websockets.connect(URI) as ws:
        for i in range(0, len(audio), CHUNK):
            await ws.send(audio[i : i + CHUNK])
            await asyncio.sleep(0.01)
        await ws.close()
        try:
            async for msg in ws:
                msgs.append(json.loads(msg))
        except Exception:
            pass

    print("Messages from server:")
    for m in msgs:
        print(f"  {m}")
    if not msgs:
        print("  (none — transcript may have been cut off by early close; use ws_speech_test2.py)")


asyncio.run(main())
