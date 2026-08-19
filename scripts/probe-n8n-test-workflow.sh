#!/bin/sh
set -eu

response_file=$(mktemp)
status=$(curl -sS -o "$response_file" -w '%{http_code}' \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  --data-binary @/app/automations/test-automation/workflow.json \
  http://n8n:5678/api/v1/workflows)
printf 'STATUS=%s\n' "$status"
cat "$response_file"
rm -f "$response_file"
