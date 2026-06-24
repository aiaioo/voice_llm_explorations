"""
Real-time speech-to-text using AssemblyAI Streaming API.

Usage:
    pip install flask requests python-dotenv
    python server.py

Then open http://localhost:8000 in a browser.

Endpoints
---------
GET /       → serves the single-page transcription UI
GET /token  → returns a short-lived AssemblyAI streaming token (JSON)

The browser opens a WebSocket directly to AssemblyAI using that token,
so the API key never leaves the server.
"""

import os
import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify
from urllib.parse import urlencode

load_dotenv()

app = Flask(__name__)
API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")


@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")


@app.route("/token")
def get_token():
    """Issue a short-lived AssemblyAI streaming token to the browser."""
    if not API_KEY:
        return jsonify({"error": "ASSEMBLYAI_API_KEY environment variable is not set"}), 500
    try:
        resp = requests.get(
            "https://streaming.assemblyai.com/v3/token?" + urlencode({
                # expires_in_seconds is the redemption window (API max: 600 s).
                # Once the WebSocket opens, the session runs for max_session_duration_seconds.
                "expires_in_seconds": 600,
                "max_session_duration_seconds": 1800,  # 30-minute session cap
            }),
            headers={"Authorization": API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as exc:
        return jsonify({"error": str(exc)}), 502


# ---------------------------------------------------------------------------
# Single-page front-end
# ---------------------------------------------------------------------------

HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Live Transcription</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0d0d12;
      color: #e2e2e8;
      height: 100dvh;
      display: flex;
      justify-content: center;
    }

    .app {
      width: 100%;
      height: 100dvh;
      display: flex;
      flex-direction: column;
      padding: 24px 1cm 32px;
      gap: 16px;
    }

    header h1 {
      text-align: center;
      font-size: 2rem;
      font-weight: 700;
      color: #e8e8ff;
      letter-spacing: -0.01em;
    }

    /* ── Transcript panel ───────────────────────────────────────────────── */
    #panel {
      flex: 1;
      min-height: 0;           /* allow flex child to shrink below content size */
      background: #16162a;
      border: 1px solid #3a3a60;
      border-radius: 16px;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    #panel::-webkit-scrollbar          { width: 6px; }
    #panel::-webkit-scrollbar-track    { background: transparent; }
    #panel::-webkit-scrollbar-thumb    { background: #3a3a60; border-radius: 3px; }

    #placeholder {
      margin: auto;
      text-align: center;
      color: #5a5a80;
      user-select: none;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 14px;
    }

    #placeholder p { font-size: 0.9rem; line-height: 1.7; }

    #turns { display: flex; flex-direction: column; gap: 10px; }

    .turn {
      font-size: 1rem;
      line-height: 1.8;
      color: #e0e0f0;
      padding-left: 14px;
      border-left: 3px solid #6366f1;
      animation: fadein 0.18s ease;
    }

    @keyframes fadein {
      from { opacity: 0; transform: translateY(4px); }
      to   { opacity: 1; transform: none; }
    }

    #partial {
      display: none;           /* shown only when partial text is present */
      font-size: 1rem;
      line-height: 1.8;
      color: #7878a0;
      font-style: italic;
      padding-left: 14px;
      border-left: 3px dashed #44446a;
      margin-top: 10px;
    }

    /* ── Controls ───────────────────────────────────────────────────────── */
    .controls {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      padding-top: 4px;
    }

    #mic-btn {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      border: none;
      background: #6366f1;
      color: #ffffff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 24px rgba(99, 102, 241, 0.5);
      transition: background 0.2s, box-shadow 0.2s, transform 0.1s;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }

    #mic-btn:focus-visible {
      outline: 2px solid #a5b4fc;
      outline-offset: 4px;
    }

    #mic-btn:hover:not(:disabled) {
      background: #4f46e5;
      box-shadow: 0 4px 32px rgba(99, 102, 241, 0.7);
      transform: scale(1.05);
    }

    #mic-btn:active:not(:disabled) {
      transform: scale(0.97);
    }

    #mic-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }

    #mic-btn.connecting {
      background: #d97706;
      box-shadow: 0 4px 24px rgba(217, 119, 6, 0.5);
    }

    #mic-btn.recording {
      background: #ef4444;
      box-shadow: 0 4px 24px rgba(239, 68, 68, 0.5);
      animation: pulse-glow 1.8s ease-in-out infinite;
    }

    @keyframes pulse-glow {
      0%, 100% { box-shadow: 0 4px 24px rgba(239, 68, 68, 0.5), 0 0 0 0    rgba(239, 68, 68, 0.4); }
         50%   { box-shadow: 0 4px 24px rgba(239, 68, 68, 0.5), 0 0 0 18px rgba(239, 68, 68, 0);   }
    }

    #status {
      font-size: 0.75rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #6060a0;
    }

    #status.ok    { color: #4ade80; }
    #status.error { color: #f87171; }
  </style>
</head>
<body>
<div class="app">
  <header><h1>Live Transcription</h1></header>

  <div id="panel">
    <div id="placeholder">
      <!-- microphone outline -->
      <svg width="38" height="38" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.4"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8"  y1="23" x2="16" y2="23"/>
      </svg>
      <p>Tap the microphone to begin.<br>Your transcript will appear here.</p>
    </div>

    <div id="turns"></div>
    <div id="partial"></div>
  </div>

  <div class="controls">
    <button id="mic-btn" aria-label="Toggle microphone">
      <!-- idle: microphone icon -->
      <svg id="icon-mic" width="26" height="26" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.9"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8"  y1="23" x2="16" y2="23"/>
      </svg>
      <!-- recording: stop (square) icon -->
      <svg id="icon-stop" width="26" height="26" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.9"
           stroke-linecap="round" stroke-linejoin="round"
           style="display:none">
        <rect x="5" y="5" width="14" height="14" rx="2"/>
      </svg>
    </button>
    <div id="status">Click to start</div>
  </div>
</div>

<script>
// ── DOM refs ──────────────────────────────────────────────────────────────────
const micBtn      = document.getElementById('mic-btn');
const statusEl    = document.getElementById('status');
const panelEl     = document.getElementById('panel');
const turnsEl     = document.getElementById('turns');
const partialEl   = document.getElementById('partial');
const placeholder = document.getElementById('placeholder');
const iconMic     = document.getElementById('icon-mic');
const iconStop    = document.getElementById('icon-stop');

// ── App state ─────────────────────────────────────────────────────────────────
// 'idle' | 'connecting' | 'recording' | 'stopping'
let appState    = 'idle';
let ws          = null;
let audioCtx    = null;
let mediaStream = null;
let workletNode = null;

// ── AudioWorklet source (loaded as blob URL so no extra file is needed) ───────
const WORKLET_SRC = `
class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Buffer up to 800 samples (~50 ms at 16 kHz) before sending a chunk.
    // Keeps WebSocket message rate manageable while staying below 50 ms.
    this._buf = new Float32Array(800);
    this._pos = 0;
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;
    let src = 0;
    while (src < ch.length) {
      const room = 800 - this._pos;
      const n    = Math.min(room, ch.length - src);
      this._buf.set(ch.subarray(src, src + n), this._pos);
      this._pos += n;
      src       += n;
      if (this._pos === 800) {
        // Convert Float32 [-1, 1] → Int16 PCM and send as binary frame
        const pcm = new Int16Array(800);
        for (let i = 0; i < 800; i++) {
          pcm[i] = Math.max(-32768, Math.min(32767, this._buf[i] * 32767 | 0));
        }
        this.port.postMessage(pcm.buffer, [pcm.buffer]);
        this._pos = 0;
      }
    }
    return true;
  }
}
registerProcessor('pcm-processor', PCMProcessor);
`;

// ── Helpers ───────────────────────────────────────────────────────────────────
function setStatus(msg, cls = '') {
  statusEl.textContent = msg;
  statusEl.className   = cls;
}

function scrollToBottom() {
  panelEl.scrollTop = panelEl.scrollHeight;
}

function addFinalTurn(text) {
  if (!text || !text.trim()) return;
  placeholder.style.display = 'none';
  const p = document.createElement('p');
  p.className   = 'turn';
  p.textContent = text;
  turnsEl.appendChild(p);
  scrollToBottom();
}

function setPartial(text) {
  partialEl.textContent  = text || '';
  partialEl.style.display = text ? '' : 'none';
  if (text) scrollToBottom();
}

function applyState(s) {
  appState = s;

  const busy      = s === 'connecting' || s === 'stopping';
  const recording = s === 'recording';

  micBtn.disabled = busy;
  micBtn.classList.toggle('recording',  recording);
  micBtn.classList.toggle('connecting', s === 'connecting');

  iconMic.style.display  = recording ? 'none' : '';
  iconStop.style.display = recording ? ''     : 'none';

  if (s === 'idle')       { setStatus('Click to start'); }
  if (s === 'connecting') { setStatus('Connecting…'); }
  if (s === 'recording')  { setStatus('Recording', 'ok'); placeholder.style.display = 'none'; }
  if (s === 'stopping')   { setStatus('Stopping…'); }
}

// ── Session start ─────────────────────────────────────────────────────────────
async function startSession() {
  applyState('connecting');
  try {
    // 1. Fetch ephemeral token from our Python backend
    const tokenRes  = await fetch('/token');
    const tokenData = await tokenRes.json();
    if (tokenData.error) throw new Error(tokenData.error);
    const { token } = tokenData;

    // 2. Request microphone (mono, with echo/noise suppression)
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });

    // 3. AudioContext at 16 kHz (matches AssemblyAI's recommended sample rate)
    audioCtx = new AudioContext({ sampleRate: 16000 });

    // 4. Load inline PCM worklet via blob URL (no extra file needed)
    const blob    = new Blob([WORKLET_SRC], { type: 'application/javascript' });
    const blobUrl = URL.createObjectURL(blob);
    await audioCtx.audioWorklet.addModule(blobUrl);
    URL.revokeObjectURL(blobUrl);

    // 5. Open WebSocket directly to AssemblyAI with the token
    //    The Python server never sees raw audio — it only issues the token.
    const params = new URLSearchParams({
      token,
      speech_model: 'universal-3-5-pro',
      sample_rate:  String(audioCtx.sampleRate),
    });
    ws = new WebSocket('wss://streaming.assemblyai.com/v3/ws?' + params);

    ws.onopen = () => {
      // Wire mic → worklet → MediaStreamDestination (keeps graph alive, no speaker output)
      const source  = audioCtx.createMediaStreamSource(mediaStream);
      workletNode   = new AudioWorkletNode(audioCtx, 'pcm-processor');
      const sink    = audioCtx.createMediaStreamDestination();
      source.connect(workletNode);
      workletNode.connect(sink);

      // Forward each PCM chunk to AssemblyAI as a binary WebSocket frame
      workletNode.port.onmessage = ({ data }) => {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(data);
      };

      applyState('recording');
    };

    ws.onmessage = ({ data }) => handleServerMessage(JSON.parse(data));
    ws.onerror   = ()         => { setStatus('WebSocket error', 'error'); cleanup(); };
    ws.onclose   = ()         => { if (appState !== 'idle') cleanup(); };

  } catch (err) {
    setStatus(err.message, 'error');
    cleanup();
  }
}

// ── Session stop ──────────────────────────────────────────────────────────────
function stopSession() {
  if (appState !== 'recording') return;
  applyState('stopping');

  // Stop mic immediately
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null; }
  if (workletNode) { workletNode.disconnect(); workletNode = null; }

  // Ask AssemblyAI to flush in-flight audio and close the session.
  // We wait for the Termination message before calling cleanup() so we
  // don't drop the final transcript.
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'Terminate' }));
  } else {
    cleanup();
  }
}

// ── Message handler ───────────────────────────────────────────────────────────
function handleServerMessage(msg) {
  switch (msg.type) {

    case 'Begin':
      // Session is live — nothing extra to display
      break;

    case 'SpeechStarted':
      // Model detected speech; first Turn message follows shortly
      break;

    case 'Turn':
      // A turn is complete when both end_of_turn AND turn_is_formatted are true.
      // Until then, update the partial transcript in place.
      if (msg.end_of_turn && msg.turn_is_formatted) {
        addFinalTurn(msg.transcript);
        setPartial('');
      } else {
        setPartial(msg.transcript);
      }
      break;

    case 'Termination':
      // Server has flushed everything; safe to close now
      cleanup();
      break;

    case 'Error':
      setStatus('Error ' + msg.error_code + ': ' + msg.error, 'error');
      cleanup();
      break;
  }
}

// ── Cleanup ───────────────────────────────────────────────────────────────────
function cleanup() {
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); }
  if (workletNode) { workletNode.disconnect(); }
  if (audioCtx)   { audioCtx.close(); }
  if (ws) {
    ws.onclose = null;  // prevent re-entrant cleanup
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  }
  mediaStream = workletNode = audioCtx = ws = null;
  setPartial('');
  applyState('idle');
}

// ── Button ────────────────────────────────────────────────────────────────────
micBtn.addEventListener('click', () => {
  if      (appState === 'idle')      startSession();
  else if (appState === 'recording') stopSession();
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
