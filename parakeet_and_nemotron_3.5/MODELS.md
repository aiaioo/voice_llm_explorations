# Models

## Installed model

### nemotron-3.5-asr-streaming-0.6b (q5_k)

**File:** `models/nemotron-3.5-asr-streaming-0.6b-q5_k.gguf` (748 MB)
**Source:** [mudler/parakeet-cpp-gguf](https://huggingface.co/mudler/parakeet-cpp-gguf) on Hugging Face
**Original checkpoint:** [nvidia/nemotron-3.5-asr-streaming-0.6b](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b)
**License:** OpenMDW-1.1

#### Architecture

| Property | Value |
|----------|-------|
| Architecture | RNNT (RNN-Transducer) |
| Parameters | ~0.6B |
| Encoder | FastConformer, 24 layers, d_model=1024, 8 attention heads |
| Mel features | 128 mel bins, n_fft=512, window=400, hop=160 |
| Vocabulary | 13,087 tokens |
| Subsampling | 8x (256 channels) |
| Attention context | [56, 3] chunked_limited (causal) |
| Streaming | Enabled — chunk sizes [25, 32], shift [25, 32], pre-encode cache [0, 9] |

#### Key capabilities

- **Multilingual** — supports 40+ locales. Select with `--lang <locale>` (e.g. `en-US`, `fr-FR`). Defaults to `auto`.
- **Prompt-conditioned** — a learned language prompt vector is injected into the encoder at inference time, allowing a single model weight file to serve all languages.
- **Offline and streaming** — the same model runs both `transcribe` (whole-file) and `transcribe --stream` (cache-aware chunk-by-chunk) modes. Transcripts are validated byte-for-byte identical to NVIDIA's NeMo reference implementation at WER 0.
- **End-of-utterance detection** — in streaming mode, the model emits `<EOU>` (end of utterance) and `<EOB>` (back-channel) tokens at speech boundaries. The decoder state is reset at each `<EOU>` so multi-sentence audio is handled correctly.

#### Why this model was chosen

The Nemotron 3.5 is the **only model in the parakeet.cpp ecosystem that supports both streaming and multilingual transcription**. The other parakeet models are English-only and do not have cache-aware streaming. It was chosen specifically because:

1. The `--stream` mode was a target use case, and Nemotron 3.5 is the only supported streaming model beyond `parakeet_realtime_eou_120m-v1`.
2. The 40+ language support makes it more broadly useful than the English-only alternatives.
3. At 0.6B parameters it is a practical size for CPU inference.

The `q5_k` quantization was selected as the best balance of quality and size for a CPU-only x86_64 binary. It is near-lossless (WER 0 vs NeMo on English) at roughly half the size of f16, and smaller than q8_0 while retaining more precision than q4_k.

#### Available quantizations

| Variant | Size | Quality |
|---------|------|---------|
| f16 | 1.48 GB | Highest — near-lossless |
| q8_0 | 984 MB | Near-lossless |
| **q5_k** | **785 MB** | **Installed — near-lossless** |
| q6_k | 856 MB | Near-lossless |
| q4_k | 718 MB | Smallest — minor WER cost |

#### Performance notes

- On a 4-core x86_64 CPU, a ~6 second clip takes approximately 20 seconds to transcribe with `--threads 4`.
- The large vocabulary (13,087 tokens) makes the RNNT joint network expensive on CPU. Always pass `--threads N` where N is your core count.
- GPU acceleration (Metal on Apple Silicon, CUDA on NVIDIA) would significantly reduce latency but is not available on this x86_64 binary.

---

## Alternative streaming-capable models

Only two models in the parakeet.cpp model library support cache-aware streaming:

### parakeet_realtime_eou_120m-v1

**Source:** [nvidia/parakeet_realtime_eou_120m-v1](https://huggingface.co/nvidia/parakeet_realtime_eou_120m-v1)
**Architecture:** RNNT, streaming, ~120M parameters
**Language:** English only
**Streaming:** Yes — cache-aware with EOU detection

The lightweight streaming alternative. At 120M parameters it is roughly 5x smaller than Nemotron 3.5, which means much faster CPU inference. It also emits `<EOU>` / `<EOB>` boundary tokens. The tradeoff is English-only support and lower accuracy on harder content.

Download the q5_k variant (~200 MB estimated):
```sh
curl -L "https://huggingface.co/mudler/parakeet-cpp-gguf/resolve/main/parakeet_realtime_eou_120m-v1-q5_k.gguf" \
  -o models/parakeet_realtime_eou_120m-v1-q5_k.gguf
```

---

## Non-streaming models (reference)

These models do not support `--stream` but offer fast, accurate offline transcription. All are English-only.

| Model | Type | Size | Notes |
|-------|------|------|-------|
| parakeet-tdt_ctc-110m | Hybrid TDT+CTC | 110M | Fastest; good accuracy |
| parakeet-tdt-0.6b-v2 | TDT | 0.6B | Strong English accuracy |
| parakeet-tdt-0.6b-v3 | TDT | 0.6B | Multilingual (25 European languages), offline only |
| parakeet-tdt-1.1b | TDT | 1.1B | Best English accuracy |
| parakeet-tdt_ctc-1.1b | Hybrid TDT+CTC | 1.1B | Best English accuracy + CTC fallback |
| parakeet-ctc-0.6b | CTC | 0.6B | CTC decoder only |
| parakeet-ctc-1.1b | CTC | 1.1B | CTC decoder only |
| parakeet-rnnt-0.6b | RNNT | 0.6B | Standard RNNT, offline |
| parakeet-rnnt-1.1b | RNNT | 1.1B | Standard RNNT, offline |

All are available as GGUF (f16, q8_0, q5_k, q6_k, q4_k) from [mudler/parakeet-cpp-gguf](https://huggingface.co/mudler/parakeet-cpp-gguf).
