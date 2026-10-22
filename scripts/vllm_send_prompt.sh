#!/bin/bash
# Checks a running vLLM server: health, the served model and one chat completion.
# Reads the port and API key from modules/vllm/.env. Override with VLLM_URL and VLLM_API_KEY.
# Ex:
# ./vllm_send_prompt.sh
# ./vllm_send_prompt.sh "Why the sky is blue?"
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
get() { grep -E "^$1=" "$root/modules/vllm/.env" 2>/dev/null | cut -d= -f2- || true; }

port="$(get VLLM_HOST_PORT)"
url="${VLLM_URL:-http://localhost:${port:-8000}}"
api_key="${VLLM_API_KEY:-$(get VLLM_API_KEY)}"
prompt="${1:-Why the sky is blue?}"
auth=(-H "Authorization: Bearer $api_key")

echo "Health: $url/health"
curl -sf "$url/health" && echo "ok"

model_name="$(curl -sSf "${auth[@]}" "$url/v1/models" | jq -r '.data[0].id')"
echo "Model served: $model_name"

# Thinking models spend tokens on reasoning, so keep max_tokens high.
jq -n --arg model "$model_name" --arg prompt "$prompt" \
  '{model: $model, max_tokens: 1024, messages: [{role: "user", content: $prompt}]}' |
  curl -sSf "$url/v1/chat/completions" "${auth[@]}" -H "Content-Type: application/json" -d @- |
  jq '{message: .choices[0].message, usage: .usage}'
