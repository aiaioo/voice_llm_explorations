"""
WebSocket smoke tests for server_diarize.py — no audio file required.

Tests:
  1. 3 s of 440 Hz sine (pure tone — no transcript expected)
  2. Immediate close with empty buffer
  3. 6 s of sine crossing the 5-second segment boundary

Usage:
    python ws_verify.py [ws://127.0.0.1:8000/ws]
"""
import asyncio
import json
import math
import struct
import sys

import websockets

SAMPLE_RATE = 16000
CHUNK = 3200  # 100 ms @ 16 kHz 16-bit mono
URI = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8000/ws"


def sine_pcm(duration_s: float, freq: float = 440) -> bytes:
    n = int(SAMPLE_RATE * duration_s)
    return struct.pack(
        f"<{n}h",
        *(int(32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)) for i in range(n)),
    )


async def test_tone():
    print("=== TEST 1: 3 s of 440 Hz sine (no transcript expected) ===")
    async with websockets.connect(URI) as ws:
        audio = sine_pcm(3.0)
        for i in range(0, len(audio), CHUNK):
            await ws.send(audio[i : i + CHUNK])
            await asyncio.sleep(0.01)
        await ws.close()
        msgs = []
        try:
            async for msg in ws:
                msgs.append(json.loads(msg))
        except Exception:
            pass
    print(f"  Messages: {msgs if msgs else '(none — expected for pure tone)'}")


async def test_empty():
    print("=== TEST 2: immediate close with empty buffer ===")
    async with websockets.connect(URI) as ws:
        await ws.close()
        msgs = []
        try:
            async for msg in ws:
                msgs.append(json.loads(msg))
        except Exception:
            pass
    print(f"  Messages: {msgs if msgs else '(none — expected, nothing to flush)'}")


async def test_segment_boundary():
    print("=== TEST 3: 6 s of sine — crosses 5-second segment boundary ===")
    msgs = []
    async with websockets.connect(URI) as ws:
        audio = sine_pcm(6.0)
        for i in range(0, len(audio), CHUNK):
            await ws.send(audio[i : i + CHUNK])
            await asyncio.sleep(0.01)
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=15)
            msgs.append(json.loads(msg))
        except asyncio.TimeoutError:
            pass
        await ws.close()
        try:
            async for msg in ws:
                msgs.append(json.loads(msg))
        except Exception:
            pass
    print(f"  Messages: {msgs if msgs else '(none)'}")
    if msgs:
        print("  Segment boundary fired correctly.")


async def main():
    print(f"Target: {URI}\n")
    await test_tone()
    await test_empty()
    await test_segment_boundary()
    print("\nDone.")


asyncio.run(main())
