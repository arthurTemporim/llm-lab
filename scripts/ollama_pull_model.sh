#!/bin/bash
# Ex:
# ./ollama_pull_models.sh

models=(
"llama3.2"
"gemma3n"
"llama3.2-vision"
"gpt-oss:20b"
"nomic-embed-text"
)
stream=false
url="http://localhost:11435"

for model_name in "${models[@]}"; do
  echo "Pulling model: $model_name from $url"
  curl "$url/api/pull" -d "{\"name\":\"$model_name\", \"stream\":$stream}"
  echo ""
done

echo "Listing current local models on $url"
curl "$url/api/tags"

