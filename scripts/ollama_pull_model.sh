#!/bin/bash
# Ex:
# ./ollama_pull_models.sh

models=(
"llama3.2:3b"
"gemma4:12b"
"llama3.2-vision:11b"
"nomic-embed-text-v2-moe:latest"
"tev1:4b"
"lfm2.5:8b"
"qwen3-embedding:8b"
"qwen3-vl:8b"
)
stream=false
url="http://localhost:11434"

for model_name in "${models[@]}"; do
  echo "Pulling model: $model_name from $url"
  curl "$url/api/pull" -d "{\"name\":\"$model_name\", \"stream\":$stream}"
  echo ""
done

echo "Listing current local models on $url"
curl "$url/api/tags"

