SHELL := /bin/bash

.PHONY: precommit
precommit: check-links check-json

.PHONY: release-check
release-check: precommit check-versions
	@echo "ready to release"

.PHONY: check-links
check-links:
	@bash scripts/check-links.sh

.PHONY: check-json
check-json:
	@echo "Validating plugin JSON..."
	@python3 -m json.tool .claude-plugin/plugin.json > /dev/null
	@python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
	@echo "plugin.json + marketplace.json OK"

.PHONY: check-versions
check-versions:
	@bash scripts/check-versions.sh

.PHONY: build-index
build-index:
	@python3 scripts/build-index.py > rules/index.json
	@echo "rules/index.json updated"
