#!/bin/bash
# Ex:
# ./ollama_pull_model.sh


model_name="llama3.2"
stream=false
url="http://localhost:11435"

echo "Ollama pulling $model_name on $url"
curl "$url/api/pull" -d "{\"name\":\"$model_name\", \"stream\":$stream}"
echo ""

echo "Ollama listing current local models on $url"
curl "$url/api/tags"
