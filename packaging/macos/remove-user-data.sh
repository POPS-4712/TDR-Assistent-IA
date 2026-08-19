#!/bin/sh
set -eu

if [ "${1:-}" != "--confirm-remove-data" ]; then
  echo "Refusing to remove data. Re-run with --confirm-remove-data after confirming you want to delete local profiles, configuration, backups and dedicated service volumes." >&2
  exit 1
fi
APP_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
exec "$APP_ROOT/Automation Center.app/Contents/MacOS/AutomationCenter" remove-data --confirm-remove-data
