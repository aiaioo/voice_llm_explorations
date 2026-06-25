const SPEAKER_COLORS = [
    '#4FC3F7', // blue
    '#81C784', // green
    '#FFB74D', // orange
    '#F06292', // pink
    '#CE93D8', // purple
    '#80CBC4', // teal
];

// Inlined so no separate fetch is needed and no optional-chaining in worklet scope.
const WORKLET_SOURCE = `
class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._phase = 0;
        this._buf = [];
    }

    process(inputs) {
        var input = inputs[0];
        if (!input || !input.length) return true;

        var numCh  = input.length;
        var frames = input[0].length;
        var ratio  = 16000 / sampleRate;

        for (var i = 0; i < frames; i++) {
            var s = 0;
            for (var c = 0; c < numCh; c++) s += input[c][i];
            s /= numCh;

            this._phase += ratio;
            if (this._phase >= 1) {
                this._phase -= 1;
                this._buf.push(s);

                if (this._buf.length >= 1600) {
                    var pcm = new Int16Array(1600);
                    for (var j = 0; j < 1600; j++) {
                        var v = Math.max(-1, Math.min(1, this._buf[j]));
                        pcm[j] = v < 0 ? v * 32768 : v * 32767;
                    }
                    this.port.postMessage(pcm.buffer, [pcm.buffer]);
                    this._buf = [];
                }
            }
        }
        return true;
    }
}
registerProcessor('audio-processor', AudioProcessor);
`;

let ws = null, audioCtx = null, worklet = null, micStream = null;
let segments = [], interim = '';

const transcriptEl = document.getElementById('transcript');
const statusEl     = document.getElementById('status');
const toggleBtn    = document.getElementById('btn-toggle');
const clearBtn     = document.getElementById('btn-clear');

toggleBtn.addEventListener('click', () => ws ? stop() : start());
clearBtn.addEventListener('click', () => { segments = []; interim = ''; render(); });

// ── connection ────────────────────────────────────────────────────────────────

async function start() {
    toggleBtn.disabled = true;
    setStatus('connecting', 'Connecting...');

    // AudioContext + worklet must be set up inside the user-gesture call stack.
    try {
        audioCtx = new AudioContext();
        await audioCtx.resume();
        const blob = new Blob([WORKLET_SOURCE], { type: 'application/javascript' });
        const url  = URL.createObjectURL(blob);
        await audioCtx.audioWorklet.addModule(url);
        URL.revokeObjectURL(url);
    } catch (err) {
        setStatus('error', 'Worklet failed: ' + err.message);
        audioCtx && audioCtx.close();
        audioCtx = null;
        toggleBtn.disabled = false;
        return;
    }

    ws = new WebSocket(`ws://${location.host}/ws`);
    ws.binaryType = 'arraybuffer';

    ws.onopen  = setupMic;
    ws.onclose = () => { stop(); setStatus('idle', 'Ready'); };
    ws.onerror = () => setStatus('error', 'WebSocket error');
    ws.onmessage = e => handle(JSON.parse(e.data));
}

async function setupMic() {
    try {
        micStream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
        });

        const src = audioCtx.createMediaStreamSource(micStream);
        worklet = new AudioWorkletNode(audioCtx, 'audio-processor');
        worklet.port.onmessage = e => {
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(e.data);
        };
        src.connect(worklet);
        // intentionally not connecting worklet → destination (avoids feedback)

        setStatus('active', 'Listening...');
        toggleBtn.textContent = 'Stop';
        toggleBtn.classList.add('active');
        toggleBtn.disabled = false;
    } catch (err) {
        setStatus('error', err.message);
        ws && ws.close();
        ws = null;
        toggleBtn.disabled = false;
    }
}

function stop() {
    worklet && worklet.disconnect();
    audioCtx && audioCtx.close();
    micStream && micStream.getTracks().forEach(t => t.stop());
    if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    ws = null; audioCtx = null; worklet = null; micStream = null;

    toggleBtn.textContent = 'Start';
    toggleBtn.classList.remove('active');
    toggleBtn.disabled = false;
    setStatus('idle', 'Ready');
}

// ── transcript events ─────────────────────────────────────────────────────────

function handle(msg) {
    if (msg.type === 'interim') {
        interim = msg.transcript;
    } else if (msg.type === 'final') {
        interim = '';
        if (msg.words && msg.words.length) {
            segments.push(...groupBySpeaker(msg.words));
        } else if (msg.transcript) {
            segments.push({ tag: 0, text: msg.transcript });
        }
    } else if (msg.type === 'error') {
        setStatus('error', msg.message);
    }
    render();
}

function groupBySpeaker(words) {
    const groups = [];
    let cur = null;
    for (const w of words) {
        if (!cur || cur.tag !== w.speaker_tag) {
            if (cur) groups.push(cur);
            cur = { tag: w.speaker_tag, text: w.word };
        } else {
            cur.text += ' ' + w.word;
        }
    }
    if (cur) groups.push(cur);
    return groups;
}

// ── rendering ─────────────────────────────────────────────────────────────────

function render() {
    if (!segments.length && !interim) {
        transcriptEl.innerHTML = '<p class="empty">Press <strong>Start</strong> to begin transcribing.</p>';
        return;
    }

    let html = '';
    for (const seg of segments) {
        const color = seg.tag > 0
            ? SPEAKER_COLORS[(seg.tag - 1) % SPEAKER_COLORS.length]
            : '#757575';
        const label = seg.tag > 0 ? `Speaker&nbsp;${seg.tag}` : 'Unknown';
        html += `<div class="seg">
            <span class="lbl" style="color:${color}">${label}</span>
            <span class="txt">${esc(seg.text)}</span>
        </div>`;
    }

    if (interim) {
        html += `<div class="seg interim">
            <span class="lbl">&#8230;</span>
            <span class="txt">${esc(interim)}</span>
        </div>`;
    }

    transcriptEl.innerHTML = html;
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function esc(t) {
    return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function setStatus(state, text) {
    statusEl.textContent = text;
    statusEl.className = 'status ' + state;
}
