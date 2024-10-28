#!/bin/bash
# Ex:
# ./ollama_pull_model.sh


model_name="gemma2"
url="http://localhost:11435"
url="$url/api/pull"

curl "$url" -d "{ \"name\": \"$model_name\" }"

