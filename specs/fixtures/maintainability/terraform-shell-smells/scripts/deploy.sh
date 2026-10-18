#!/usr/bin/env bash
set -euo pipefail

terraform init -input=false
terraform apply -auto-approve || true
