#!/bin/bash
# Ex:
# ./ollama_pull_model.sh

# Sizes in GB (disk), as reported by Ollama.
# nimble and tev1 are decision models (use /v1/systemone, not chat).
models=(
"llama3.2:3b" # 2.0 GB
"gemma4:12b" # 8.0 GB
"nomic-embed-text-v2-moe:latest" # 1.0 GB
"tev1:4b" # 4.6 GB
"lfm2.5:8b" # 5.2 GB
"qwen3-embedding:8b" # 4.7 GB
"embeddinggemma:300m" # 0.6 GB
"qwen3-vl:8b" # 6.2 GB
"nimble:9b" # 9.5 GB
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

