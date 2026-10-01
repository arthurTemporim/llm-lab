#!/bin/bash
# scripts/generate_localai_key.sh

TARGET_ENV=$1

if [ ! -f "$TARGET_ENV" ]; then
    echo "[scripts] generating secure API key for LocalAI..."
    # Generate a random 32-character hex string
    RANDOM_KEY=$(openssl rand -hex 32)
    echo "LOCALAI_API_KEY=sk-$RANDOM_KEY" > "$TARGET_ENV"
    echo "[scripts] created $TARGET_ENV"
else
    echo "[scripts] $TARGET_ENV already exists. Skipping generation."
fi
