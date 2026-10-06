#!/bin/bash
# Ex:
# ./ollama_pull_models.sh

models=(
"llama3.2:3b" # 2G
"gemma4:12b" # 8G
"llama3.2-vision:11b" # 8G
"nomic-embed-text-v2-moe:latest" # 1G
"tev1:4b" # 5G
"lfm2.5:8b" # 5G
"qwen3-embedding:8b" # 5G
"embeddinggemma-2:740m" # 1G
"qwen3-vl:8b" # 6G
"nimble:9b" # 10G
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

