#!/usr/bin/env bash
set -euo pipefail

terraform init -input=false
if ! terraform apply -auto-approve; then
  echo "order service deploy failed; the previous version stays live" >&2
  exit 1
fi
