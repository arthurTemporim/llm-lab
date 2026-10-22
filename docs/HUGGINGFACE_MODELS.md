# Hugging Face models

Candidate models from Hugging Face for the [vLLM](../modules/vllm/README.md) module: five picks each for chat, vision, decisions, speech-to-text, text-to-speech and embeddings, with parameters, size and what fits on a 12 GB GPU. The models already served through LiteLLM and Ollama are in [MODELS.md](MODELS.md).

Data snapshot: **2026-10-21**, read from the Hugging Face API (parameters, file sizes, license, context, architecture, downloads and likes). Counters change daily. Picks are a judgement based on popularity, recency, license and whether vLLM can load the repo. They are not benchmarked here.

## Read this first

- **Target GPU:** RTX 3060, 12 GB. vLLM needs compute capability 7.5 or newer, so it **cannot use the Tesla P4** (6.1). The module pins one card with `VLLM_GPU_ID`.
- **One model per vLLM process.** Change `VLLM_MODEL` and `VLLM_EXTRA_ARGS` in `modules/vllm/.env`, then `make vllm`.
- **Only safetensors models load in vLLM.** The most downloaded uncensored models right now are GGUF only (for example the Qwen3.8-27B uncensored/heretic builds, 1-2.5 million downloads). Those are for Ollama or llama.cpp, not for this module.
- **Not run on a GPU yet.** Sizes come from the repo metadata, VRAM figures are estimates, and "vLLM support" comes from vLLM's supported-models page. Test each model once and adjust.

### VRAM estimate

`VRAM ≈ parameters × bytes per weight + KV cache + about 1 GB`

| Format | Bytes per weight | How to get it in vLLM |
|---|---|---|
| bf16 / fp16 | 2 | Default for most repos |
| fp8 | 1 | `--quantization fp8` quantizes a bf16 repo while loading |
| 4-bit | about 0.55 | `--quantization bitsandbytes` on load (slower), or a ready AWQ/GPTQ repo |

The KV cache grows with `VLLM_MAX_MODEL_LEN`. With `VLLM_GPU_MEMORY_UTILIZATION=0.90` about 10.8 GB of the card is usable. The "12 GB" column below is that estimate.

## Chat

| # | Model | Params | Weights (HF) | Context | License | 12 GB GPU | Notes |
|---|---|---|---|---|---|---|---|
| 1 | [huihui-ai/Huihui-gemma-4-12B-it-abliterated](https://huggingface.co/huihui-ai/Huihui-gemma-4-12B-it-abliterated) | 11.96B | 23.9 GB bf16 | 131K | Apache 2.0 | 4-bit only (about 7 GB) | Abliterated Gemma 4, same base as the lab's `gemma4:12b`; also reads images. 226 likes. The architecture is named `Gemma4UnifiedForConditionalGeneration`, not the name on vLLM's list: test it. A ready 4-bit build exists ([nicklas373/...-AWQ](https://huggingface.co/nicklas373/Huihui-gemma-4-12B-it-abliterated-AWQ), 8.3 GB) but has no likes |
| 2 | [huihui-ai/Huihui-Qwen3.5-9B-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3.5-9B-abliterated) | 9.65B | 19.3 GB bf16 | 262K | Apache 2.0 | 4-bit (about 5.5 GB); fp8 is too tight | Abliterated Qwen 3.5 with vision, thinking model. 154 likes. Supported architecture |
| 3 | [dphn/Dolphin3.0-Llama3.1-8B](https://huggingface.co/dphn/Dolphin3.0-Llama3.1-8B) | 8.03B | 16.1 GB bf16 | 131K | Llama 3.1 | fp8 (about 9 GB) | Uncensored by fine-tuning: it follows your system prompt. 407 likes, plain Llama architecture, the safest fallback if another model fails to load |
| 4 | [NousResearch/Hermes-4-14B](https://huggingface.co/NousResearch/Hermes-4-14B) | about 14.8B (29.5 GB at 2 bytes) | 29.5 GB bf16 | 41K | Apache 2.0 | 4-bit (about 8 GB) | Few refusals by design, not abliterated. Qwen3 based, hybrid reasoning. 195 likes. The repo metadata has no parameter count; the figure is derived from the size |
| 5 | [cognitivecomputations/Dolphin-Mistral-24B-Venice-Edition](https://huggingface.co/cognitivecomputations/Dolphin-Mistral-24B-Venice-Edition) | 24.01B | 48.0 GB bf16 | 131K | Apache 2.0 | **No** (4-bit is about 13 GB + cache; needs 24 GB at 4-bit, 32+ GB at fp8) | Best quality of the five, for a bigger GPU. 757 likes |

For a bigger GPU also see [huihui-ai/Huihui-Qwen3.8-27B-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated) (27.78B, 55.6 GB, 600 likes, vision). Not for the 12 GB card.

## Vision (image reading)

| # | Model | Params | Weights (HF) | Context | License | 12 GB GPU | Notes |
|---|---|---|---|---|---|---|---|
| 1 | [huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated) | 8.77B | 17.5 GB bf16 | 262K | Apache 2.0 | fp8 (about 9 GB, set `VLLM_MAX_MODEL_LEN=4096`) | Best balance. Same family as the lab's `qwen3-vl:8b`. 219 likes |
| 2 | [huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated) | 4.44B | 8.9 GB bf16 | 262K | Apache 2.0 | **Yes**, bf16 fits (about 10 GB) or fp8 (about 5 GB) | Smallest and fastest; leaves room for long context and several images. 116 likes |
| 3 | [huihui-ai/Qwen2.5-VL-7B-Instruct-abliterated](https://huggingface.co/huihui-ai/Qwen2.5-VL-7B-Instruct-abliterated) | 8.29B | 16.6 GB bf16 | 128K | Apache 2.0 | fp8 (about 9 GB) | Older but the most downloaded (288K). Good at OCR and documents |
| 4 | [huihui-ai/Huihui-Qwen3-VL-8B-Thinking-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-8B-Thinking-abliterated) | 8.77B | 17.5 GB bf16 | 262K | Apache 2.0 | fp8 (about 9 GB) | Reasons before answering; use for charts and hard visual questions. Few downloads (105), 36 likes |
| 5 | [huihui-ai/Huihui-Qwen3.8-27B-abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated) | 27.78B | 55.6 GB bf16 | 262K | Apache 2.0 | **No** (needs 24 GB+ at 4-bit) | Top quality, 600 likes. Community AWQ builds exist, e.g. [twolven/Qwen3.8-27B-abliterated-AWQ-MTP](https://huggingface.co/twolven/Qwen3.8-27B-abliterated-AWQ-MTP) |

Chat picks 1 and 2 also read images.

## Decisions (routing, classification, yes/no gates)

These models output a label, a score or a yes/no, so "uncensored" does not apply. In the lab, `tev1:4b` and `nimble:9b` run in Ollama through LiteLLM's `/v1/systemone` endpoint ([MODELS.md](MODELS.md)). vLLM has no such endpoint: with vLLM, use a generative model and its structured output (choice) option to force one of your labels, then read the probabilities from the logprobs.

| # | Model | Params | Weights (HF) | Context | License | 12 GB GPU | vLLM | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | [bespokelabs/Bespoke-Nimble-9B](https://huggingface.co/bespokelabs/Bespoke-Nimble-9B) | 9B | 0.2 GB in the repo | about 8K | Apache 2.0 | n/a | No | Best accuracy in the lab's evals (94%). The repo holds only 0.2 GB, so it is not a standalone model: run it with Ollama (`nimble:9b`). 242 likes |
| 2 | [togethercomputer/Tev1-4B-experimental](https://huggingface.co/togethercomputer/Tev1-4B-experimental) | 4.66B | 9.3 GB bf16 | 262K | not stated | **Yes** (fp8 about 5 GB) | Yes (`Qwen3_5` architecture) | Same model as `tev1:4b`; keep inputs short (about 2K tokens, see [MODELS.md](MODELS.md)) |
| 3 | [togethercomputer/Tev1-0.8B-experimental](https://huggingface.co/togethercomputer/Tev1-0.8B-experimental) | 0.87B | 1.7 GB | n/a | not stated | **Yes** (about 2.5 GB) | Probably (same family) | Smallest decision model, for very cheap gates. 20 likes |
| 4 | [MoritzLaurer/deberta-v3-large-zeroshot-v2.0](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0) | 0.44B | 0.9 GB fp16 | 512 | MIT | **Yes** (or CPU) | No (DeBERTa) | Classic zero-shot classifier: you pass labels, it scores each. 149K downloads. Run it with `transformers` in a notebook |
| 5 | [MoritzLaurer/bge-m3-zeroshot-v2.0](https://huggingface.co/MoritzLaurer/bge-m3-zeroshot-v2.0) | 0.57B | 1.1 GB fp16 | n/a | MIT | **Yes** (or CPU) | No | Multilingual zero-shot classifier and longer inputs than #4. 103K downloads |

## Speech-to-text (STT)

vLLM serves Whisper-style models at `/v1/audio/transcriptions`. Uncensoring does not apply.

| # | Model | Params | Weights (HF) | License | 12 GB GPU | vLLM | Notes |
|---|---|---|---|---|---|---|---|
| 1 | [openai/whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo) | 0.81B | 1.6 GB fp16 | MIT | **Yes** (about 3 GB) | Yes | Default choice: multilingual, close to large-v3 quality at a fraction of the cost. 6M downloads |
| 2 | [openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3) | 1.54B | about 3.1 GB fp16 (the repo is 18.5 GB because it holds several formats) | Apache 2.0 | **Yes** (about 4 GB) | Yes | Highest Whisper accuracy, slower than the turbo. 6,676 likes |
| 3 | [Qwen/Qwen3-ASR-1.7B](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) | 2.35B | 4.7 GB bf16 | Apache 2.0 | **Yes** (about 6 GB) | Yes (`Qwen3ASR`) | Newer non-Whisper model, 1.26M downloads |
| 4 | [mistralai/Voxtral-Mini-3B-2507](https://huggingface.co/mistralai/Voxtral-Mini-3B-2507) | 4.68B | about 9.4 GB bf16 (repo 18.7 GB holds F32 + BF16) | Apache 2.0 | fp8 (about 6 GB); bf16 is too tight | Yes | Transcribes and also answers questions about the audio. 131K context |
| 5 | [nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) | 0.63B | 2.5 GB fp32 | CC-BY-4.0 | **Yes** (about 3 GB) | **No** (NeMo) | Very fast, European languages. Run it with NVIDIA NeMo, not vLLM. 624K downloads |

## Text-to-speech (TTS)

**vLLM does not serve text-to-speech models** (none are on its supported list). These run with their own Python packages or another server, so they are listed here for the lab but are not loaded by `VLLM_MODEL`. The weights have no content filter; clone only voices you have the right to use.

| # | Model | Params | Weights (HF) | License | 12 GB GPU | Notes |
|---|---|---|---|---|---|---|
| 1 | [Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice) | 1.92B | 4.5 GB bf16 | Apache 2.0 | **Yes** (about 6 GB) | Best overall quality and the most liked (2,157). 2M downloads. Smaller 0.6B and a VoiceDesign variant exist |
| 2 | [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | 82M | under 1 GB | Apache 2.0 | **Yes**, runs on CPU too | Tiny and fast, 10.5M downloads, fixed voices (no cloning). Best for real-time |
| 3 | [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox) | not in metadata | 10.7 GB repo | MIT | **Yes** (small model, about 4-6 GB) | Zero-shot voice cloning with emotion control. 1.77M downloads |
| 4 | [nari-labs/Dia-1.6B](https://huggingface.co/nari-labs/Dia-1.6B) | 1.61B | 6.4 GB fp32 | Apache 2.0 | **Yes** (about 7 GB) | Multi-speaker dialogue with non-verbal sounds (laughs, coughs). 2,931 likes |
| 5 | [bosonai/higgs-tts-3-4b](https://huggingface.co/bosonai/higgs-tts-3-4b) | 4.65B | 9.3 GB bf16 | "other": read it | Tight (about 10-11 GB) | Large expressive model, 815 likes. License is not a standard one |

Not listed on purpose: [SWivid/F5-TTS](https://huggingface.co/SWivid/F5-TTS) (886K downloads) is CC-BY-NC: non-commercial only.

## Embeddings

vLLM serves embeddings with `--runner pooling` at `/v1/embeddings`. Uncensoring does not apply. The lab already has `qwen3-embedding:8b`, `nomic-embed-text-v2-moe` and `embeddinggemma:300m` in Ollama ([MODELS.md](MODELS.md)). Never mix vectors from different models in one index.

| # | Model | Params | Weights (HF) | Dimensions | Context | License | 12 GB GPU | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | [Qwen/Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B) | 7.57B | 15.1 GB bf16 | 4096 | 41K | Apache 2.0 | fp8 (about 9 GB) | Best quality, multilingual. 2M downloads |
| 2 | [Qwen/Qwen3-Embedding-4B](https://huggingface.co/Qwen/Qwen3-Embedding-4B) | 4.02B | 8.0 GB bf16 | 2560 | 41K | Apache 2.0 | **Yes**, bf16 (about 9 GB) | Same family, best fit for 12 GB |
| 3 | [Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | 0.6B | 1.2 GB bf16 | 1024 | 33K | Apache 2.0 | **Yes** (about 2 GB) | Light default, 8.5M downloads |
| 4 | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | about 0.57B | 2.3 GB | 1024 | 8K | MIT | **Yes** (about 3 GB) | Dense, sparse and multi-vector search in one model; 31M downloads. Check that your vLLM version lists `XLMRobertaModel` for pooling; if not, use it through Ollama |
| 5 | [Qwen/Qwen3-VL-Embedding-2B](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B) | 2.13B | 4.3 GB bf16 | see the model card | 262K | Apache 2.0 | **Yes** (about 6 GB) | Embeds text **and images** in one space, for image search |

## Using them in the lab

Download the models you want first with `scripts/vllm_pull_model.sh` (edit its list; it prints each size and the total). Then set these in `modules/vllm/.env` and run `make vllm`. Clients send the Hugging Face id as `model`.

| Goal | `VLLM_MODEL` | `VLLM_EXTRA_ARGS` | Endpoint |
|---|---|---|---|
| Chat (default) | `huihui-ai/Huihui-Qwen3.5-4B-abliterated` | `--quantization fp8` | `/v1/chat/completions` |
| Bigger chat in 4-bit | `huihui-ai/Huihui-Qwen3.5-9B-abliterated` | `--quantization bitsandbytes` | `/v1/chat/completions` |
| Vision | `huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated` | `--quantization fp8` (and `VLLM_MAX_MODEL_LEN=4096`) | `/v1/chat/completions` with an `image_url` part |
| Speech-to-text | `openai/whisper-large-v3-turbo` | empty | `/v1/audio/transcriptions` |
| Embeddings | `Qwen/Qwen3-Embedding-4B` | `--runner pooling` | `/v1/embeddings` |

```bash
curl http://localhost:8000/v1/audio/transcriptions \
  -H "Authorization: Bearer $VLLM_API_KEY" \
  -F model=openai/whisper-large-v3-turbo -F file=@sample.wav
```

Rules of thumb:

- One model at a time. To use two (for example chat and embeddings) switch `VLLM_MODEL`, or keep the small one in Ollama.
- Thinking models (Qwen 3.5, Qwen3-VL Thinking) spend tokens on reasoning: leave `max_tokens` high, as in [MODELS.md](MODELS.md).
- If a model fails to start, read `make vllm-logs`: the usual causes are out of memory (lower `VLLM_MAX_MODEL_LEN` or quantize) and an architecture vLLM does not know.
- Ollama and vLLM both reserve VRAM on the same card. Stop one before starting the other.

## Sources

Hugging Face model pages linked above and the Hugging Face API on 2026-10-21. vLLM: [GPU requirements](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/) (compute capability 7.5+), [supported models](https://docs.vllm.ai/en/latest/models/supported_models/).
