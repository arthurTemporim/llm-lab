#!/bin/bash
# Ex:
# ./ollama_send_pronpt.sh


model_name="llama3.2"
url="http://localhost:11434"
prompt="Why the sky is blue?"
stream="false"


url="$url/api/generate"
curl "$url" -d "{ \"model\": \"$model_name\", \
                  \"prompt\": \"$prompt\",    \
                  \"stream\": $stream         \
                }"
