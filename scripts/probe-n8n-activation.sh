#!/bin/sh
set -eu

workflow_id="$1"
response_file=$(mktemp)
status=$(curl -sS -o "$response_file" -w '%{http_code}' \
  -X POST \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  "http://n8n:5678/api/v1/workflows/${workflow_id}/activate")
printf 'STATUS=%s\n' "$status"
cat "$response_file"
rm -f "$response_file"
