SHELL := /bin/bash

.PHONY: precommit
precommit: check-links check-json check-versions

.PHONY: check-links
check-links:
	@echo "Checking links in README.md and llms.txt..."
	@EXIT=0; \
	for file in README.md llms.txt; do \
		while read -r link; do \
			target=$${link%%#*}; \
			[ -z "$$target" ] && continue; \
			if [ ! -e "$$target" ]; then \
				echo "BROKEN: $$file -> $$link"; \
				EXIT=1; \
			fi; \
		done < <(grep -oP '\]\(\K[^)]+' "$$file" 2>/dev/null | grep -v '^http' | grep -v '^mailto:'); \
	done; \
	if [ "$$EXIT" -eq 1 ]; then exit 1; fi; \
	echo "All links OK"

.PHONY: check-json
check-json:
	@echo "Validating plugin JSON..."
	@python3 -m json.tool .claude-plugin/plugin.json > /dev/null
	@python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
	@echo "plugin.json + marketplace.json OK"

.PHONY: check-versions
check-versions:
	@echo "Checking version alignment..."
	@CHANGELOG_VER=$$(grep -m1 -oE '^## v[0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md | sed 's/^## v//'); \
	PLUGIN_VER=$$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['version'])"); \
	MARKETPLACE_META_VER=$$(python3 -c "import json; print(json.load(open('.claude-plugin/marketplace.json'))['metadata']['version'])"); \
	MARKETPLACE_PLUGIN_VER=$$(python3 -c "import json; print(json.load(open('.claude-plugin/marketplace.json'))['plugins'][0]['version'])"); \
	echo "  CHANGELOG.md (top):                $$CHANGELOG_VER"; \
	echo "  plugin.json:                       $$PLUGIN_VER"; \
	echo "  marketplace.json metadata:         $$MARKETPLACE_META_VER"; \
	echo "  marketplace.json plugins[0]:       $$MARKETPLACE_PLUGIN_VER"; \
	if [ "$$CHANGELOG_VER" != "$$PLUGIN_VER" ] || [ "$$CHANGELOG_VER" != "$$MARKETPLACE_META_VER" ] || [ "$$CHANGELOG_VER" != "$$MARKETPLACE_PLUGIN_VER" ]; then \
		echo "MISMATCH: all four versions must equal CHANGELOG top entry ($$CHANGELOG_VER)"; \
		exit 1; \
	fi; \
	echo "All versions aligned at $$CHANGELOG_VER"
