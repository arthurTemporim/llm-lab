#!/bin/bash
# Ex:
# ./ollama_list_models.sh


url="http://localhost:11434"


url="$url/api/tags"
curl "$url" | jq
