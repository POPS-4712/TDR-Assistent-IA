#!/bin/sh
set -eu

if [ -z "${N8N_API_KEY:-}" ]; then
  echo "BACKEND_KEY_STATE=MISSING"
  exit 0
fi

status=$(curl -sS -o /dev/null -w '%{http_code}' \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" \
  'http://n8n:5678/api/v1/workflows?limit=1')

echo "N8N_PUBLIC_API_STATUS=${status}"
