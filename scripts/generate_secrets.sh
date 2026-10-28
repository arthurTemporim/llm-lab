#!/usr/bin/env bash
# Replaces every placeholder (comments are skipped) in the given .env files with a random value,
# a different one each time:
#   CHANGE_ME_PASSWORD  15-char password (letters and digits, safe in connection strings)
#   CHANGE_ME_HEX24     24 hex chars (Garage key id, after its "GK" prefix)
#   CHANGE_ME           64 hex chars (API keys and secrets; also fits ENCRYPTION_KEY)
# Ex: ./scripts/generate_secrets.sh modules/langfuse/.env
set -euo pipefail

# sha256 of random bytes, base64, first 15 chars. Retried until it mixes upper, lower and digits,
# which apps with password rules (Hatchet) require.
password() {
  local p=""
  until [[ $p =~ [A-Z] && $p =~ [a-z] && $p =~ [0-9] ]]; do
    p="$(head -c 32 /dev/urandom | sha256sum | base64 -w0)"
    p="${p:0:15}"
  done
  echo "$p"
}

fill() { # <file> <placeholder> <generator command...>
  local file="$1" placeholder="$2"
  shift 2
  while grep -q "^[^#]*$placeholder" "$file"; do
    sed -i "/^[^#]*$placeholder/{s/$placeholder/$("$@")/;:a;n;ba}" "$file"
  done
}

for file in "$@"; do
  # Longest placeholders first: CHANGE_ME is a prefix of the others
  fill "$file" CHANGE_ME_PASSWORD password
  fill "$file" CHANGE_ME_HEX24 openssl rand -hex 12
  fill "$file" CHANGE_ME openssl rand -hex 32
done
