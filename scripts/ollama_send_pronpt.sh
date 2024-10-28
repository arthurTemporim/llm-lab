#!/bin/bash
# Ex:
# ./ollama_send_pronpt.sh


model_name="gemma2"
url="http://ollama:11434"
prompt="Why the sky is blue?"
stream="false"


url="$url/api/generate"
curl "$url" -d "{ \"model\": \"$model_name\", \
                  \"prompt\": \"$prompt\",    \
                  \"stream\": $stream         \
                }"
