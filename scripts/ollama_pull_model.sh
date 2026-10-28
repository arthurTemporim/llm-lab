#!/usr/bin/env bash
# Ex:
# ./ollama_pull_model.sh

# "<model> <size in GB>" per line. Size = disk, as reported by Ollama.
# nimble and tev1 are decision models (use /v1/systemone, not chat).
models=(
"llama3.2:3b 2.0"
"gemma4:12b 8.0"
"tev1:4b 4.6"
"qwen3-embedding:8b 4.7"
"qwen3-vl:8b 6.2"
"nimble:9b 9.5"
)
stream=false
url="http://localhost:11434"

total=$(printf '%s\n' "${models[@]}" | awk '{s+=$2} END {printf "%.1f", s}')
echo "Models to pull: ${#models[@]}, total $total GB (less for models already pulled)"

for entry in "${models[@]}"; do
  read -r model_name size <<< "$entry"
  echo "Pulling model: $model_name ($size GB) from $url"
  curl "$url/api/pull" -d "{\"name\":\"$model_name\", \"stream\":$stream}"
  echo ""
done

echo "Total listed: $total GB"
echo "Listing current local models on $url"
curl "$url/api/tags"

