SHELL := /bin/bash

.PHONY: precommit
precommit: check-links check-json check-index

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

.PHONY: check-index
check-index:
	@python3 scripts/build-index.py > /tmp/coding-rules-index-check.json
	@if ! diff -q rules/index.json /tmp/coding-rules-index-check.json > /dev/null 2>&1; then \
		echo "ERROR: rules/index.json is stale. Run 'make build-index' and commit the result."; \
		diff -u rules/index.json /tmp/coding-rules-index-check.json | head -40; \
		rm -f /tmp/coding-rules-index-check.json; \
		exit 1; \
	fi
	@rm -f /tmp/coding-rules-index-check.json
	@echo "rules/index.json up-to-date"
