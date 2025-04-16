#!/bin/bash
# Ex:
# ./ollama_pull_models.sh
# Example of models, but it can use more than 10G in total
#models=(
#"llama3.2"
#"mistral"
#"deepseek-r1"
#"deepseek-coder-v2"
#"mxbai-embed-large"
#"nomic-embed-text"
#)

models=(
"llama3.2"
"gemma3"
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

