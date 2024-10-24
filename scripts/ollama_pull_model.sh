#!/bin/bash
# Ex:
# ./ollama_pull_model.sh


model_name="llama3.2"
url="http://localhost:11434"
url="$url/api/pull"

curl "$url" -d "{ \"name\": \"$model_name\" }"

