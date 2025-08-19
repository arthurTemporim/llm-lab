#!/bin/bash
# Ex:
# ./ollama_pull_models.sh

models=(
"llama3.2"
"gemma3n"
"llama3.2-vision"
"nomic-embed-text"
"qwen3:8b"
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

