#!/bin/bash
# Ex:
# ./ollama_pull_model.sh


model_name="gemma2"
url="http://ollama:11434"
url="$url/api/pull"

curl "$url" -d "{ \"name\": \"$model_name\" }"

