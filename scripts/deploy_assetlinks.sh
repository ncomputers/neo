#!/bin/bash
set -euo pipefail

# Deploy the assetlinks.json file to the production server.
# Requires the environment variable ASSETLINKS_HOST to be set and SSH access configured.

if [ -z "${ASSETLINKS_HOST:-}" ]; then
  echo "ASSETLINKS_HOST not set" >&2
  exit 1
fi

scp static/.well-known/assetlinks.json "$ASSETLINKS_HOST:/var/www/html/.well-known/assetlinks.json"
