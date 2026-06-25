// Mixes browser mic to mono, downsamples to 16 kHz, emits 100 ms Int16 chunks.
const TARGET_RATE = 16000;
const CHUNK_SAMPLES = 1600; // 100 ms @ 16 kHz

class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        // phase accumulator for downsampling (output / input ratio)
        this._phase = 0;
        this._buf = [];
    }

    process(inputs) {
        const input = inputs[0];
        if (!input?.length) return true;

        const numCh = input.length;
        const frames = input[0].length;
        const ratio = TARGET_RATE / sampleRate; // < 1 (downsampling)

        for (let i = 0; i < frames; i++) {
            // mix to mono
            let s = 0;
            for (let c = 0; c < numCh; c++) s += input[c][i];
            s /= numCh;

            this._phase += ratio;
            if (this._phase >= 1) {
                this._phase -= 1;
                this._buf.push(s);

                if (this._buf.length >= CHUNK_SAMPLES) {
                    const pcm = new Int16Array(CHUNK_SAMPLES);
                    for (let j = 0; j < CHUNK_SAMPLES; j++) {
                        const v = Math.max(-1, Math.min(1, this._buf[j]));
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
