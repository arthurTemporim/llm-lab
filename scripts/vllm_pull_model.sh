#!/bin/bash
# Downloads Hugging Face models into the vLLM cache volume, so `make vllm` starts without
# waiting for the download. Needs Docker only (no GPU, vLLM does not have to be running).
# Re-running skips files that are already complete. Remove a model you no longer want
# from the list and free its space with `docker volume rm vllm_huggingface` (after `make down-vllm`).
# Ex:
# ./vllm_pull_model.sh

# "<repo> <size in GB>" per line. Size = safetensors + config/tokenizer files, from the
# Hugging Face API on 2026-10-21. Details: docs/HUGGINGFACE_MODELS.md
models=(
"huihui-ai/Huihui-Qwen3.5-4B-abliterated 9.10"             # chat
"huihui-ai/Huihui-Qwen3-VL-4B-Instruct-abliterated 8.89"   # vision
"togethercomputer/Tev1-4B-experimental 9.34"               # decisions
"Qwen/Qwen3-ASR-1.7B 4.70"                                 # speech-to-text
"Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice 4.52"                # text-to-speech (not served by vLLM)
"Qwen/Qwen3-VL-Embedding-2B 4.27"                          # embeddings
)

set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
volume=vllm_huggingface # <compose project>_<volume> of modules/vllm
image=vllm/vllm-openai:v0.32.0 # same image as modules/vllm/docker-compose.yml

# HF_TOKEN is only needed for gated repos
HF_TOKEN="$(grep -E '^HF_TOKEN=' "$root/modules/vllm/.env" 2>/dev/null | cut -d= -f2- || true)"
export HF_TOKEN

# Created with the labels Docker Compose uses, so `make vllm` adopts it without a warning.
docker volume create \
  --label com.docker.compose.project=vllm \
  --label com.docker.compose.volume=huggingface \
  "$volume" > /dev/null

total=$(printf '%s\n' "${models[@]}" | awk '{s+=$2} END {printf "%.2f", s}')
echo "Models to download: ${#models[@]}, total $total GB (less for files already in the cache)"

for entry in "${models[@]}"; do
  read -r repo size <<< "$entry"
  echo ""
  echo "Downloading model: $repo ($size GB)"
  docker run --rm -e HF_TOKEN -v "$volume":/root/.cache/huggingface \
    --entrypoint python3 "$image" -c '
import sys
from huggingface_hub import snapshot_download
snapshot_download(sys.argv[1], ignore_patterns=["*.bin", "*.pt", "*.pth", "*.onnx", "*.gguf", "*.h5", "*.msgpack"])
' "$repo"
done

echo ""
echo "Total listed: $total GB"
echo -n "Cache volume size now (all cached models): "
docker run --rm -v "$volume":/root/.cache/huggingface --entrypoint du "$image" -sh /root/.cache/huggingface | cut -f1
echo "Set VLLM_MODEL in modules/vllm/.env to one of these repos, then run: make vllm"
