"""
WebSocket test client for server_gemini.py.
Connects to ws://127.0.0.1:8766/ws, sends 3 seconds of a 440 Hz tone
(which won't produce a transcript but proves the stream stays open),
then sends silence while waiting for any response or clean close.
"""
import asyncio
import json
import math
import struct
import sys

import websockets


SAMPLE_RATE = 16000
CHUNK_SAMPLES = 1600  # 100 ms


def _tone_chunk(freq_hz: float = 440.0, amplitude: float = 0.3) -> bytes:
    """Generate one 100 ms chunk of a sine wave as 16-bit PCM."""
    samples = []
    for i in range(CHUNK_SAMPLES):
        v = amplitude * math.sin(2 * math.pi * freq_hz * i / SAMPLE_RATE)
        samples.append(int(max(-32768, min(32767, v * 32767))))
    return struct.pack(f"<{CHUNK_SAMPLES}h", *samples)


def _silence_chunk() -> bytes:
    return bytes(CHUNK_SAMPLES * 2)


async def run_test() -> None:
    url = "ws://127.0.0.1:8766/ws"
    print(f"Connecting to {url} ...")

    messages_received = []
    disconnected_early = False

    try:
        async with websockets.connect(url, open_timeout=5) as ws:
            print("Connected. Sending audio ...")

            async def send_audio():
                # 3 s of tone followed by 2 s of silence
                for _ in range(30):
                    await ws.send(_tone_chunk())
                    await asyncio.sleep(0.1)
                for _ in range(20):
                    await ws.send(_silence_chunk())
                    await asyncio.sleep(0.1)

            async def recv_messages():
                nonlocal disconnected_early
                try:
                    async for raw in ws:
                        msg = json.loads(raw)
                        messages_received.append(msg)
                        tag = msg.get("type", "?")
                        text = msg.get("transcript") or msg.get("message") or ""
                        print(f"  [{tag}] {text!r}")
                except websockets.ConnectionClosed as e:
                    if e.code not in (1000, 1001):  # abnormal close
                        disconnected_early = True
                        print(f"  Connection closed unexpectedly: code={e.code} reason={e.reason!r}")

            send_task = asyncio.create_task(send_audio())
            recv_task = asyncio.create_task(recv_messages())

            await send_task
            # Give the server 2 s to flush any final results
            await asyncio.sleep(2)
            recv_task.cancel()
            await asyncio.gather(recv_task, return_exceptions=True)

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)

    print()
    if disconnected_early:
        print("FAIL — server closed the connection unexpectedly (immediate disconnect bug still present).")
        sys.exit(1)
    else:
        print(f"PASS — stream stayed open for 5 s. {len(messages_received)} message(s) received.")
        if any(m.get("type") == "error" for m in messages_received):
            errors = [m for m in messages_received if m.get("type") == "error"]
            print(f"  ⚠  Server sent {len(errors)} error message(s):")
            for e in errors:
                print(f"     {e.get('message')}")


if __name__ == "__main__":
    asyncio.run(run_test())
