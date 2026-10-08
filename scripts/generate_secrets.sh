#!/usr/bin/env bash
# Replaces every CHANGE_ME value (comments are skipped) in the given .env files
# with random hex, a different one each time.
# Ex: ./scripts/generate_secrets.sh modules/langfuse/.env
set -euo pipefail

for file in "$@"; do
  while grep -q '^[^#]*CHANGE_ME' "$file"; do
    # 64 hex chars, which also fits ENCRYPTION_KEY
    sed -i "/^[^#]*CHANGE_ME/{s/CHANGE_ME/$(openssl rand -hex 32)/;:a;n;ba}" "$file"
  done
done
