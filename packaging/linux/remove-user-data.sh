#!/bin/sh
set -eu

if [ "${1:-}" != "--confirm-remove-data" ]; then
  echo "Refusing to remove data. Re-run with --confirm-remove-data after confirming you want to delete local profiles, configuration, backups and dedicated service volumes." >&2
  exit 1
fi
exec /opt/automation-center/automation-center remove-data --confirm-remove-data
