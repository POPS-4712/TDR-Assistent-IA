#!/bin/sh
set -eu

workflow_id="$1"
response_file=$(mktemp)
status=$(curl -sS -o "$response_file" -w '%{http_code}' \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  "http://n8n:5678/api/v1/executions?workflowId=${workflow_id}&limit=5")
printf 'STATUS=%s\n' "$status"
cat "$response_file"
rm -f "$response_file"
