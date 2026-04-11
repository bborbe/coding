SHELL := /bin/bash

.PHONY: precommit
precommit: check-links check-json

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
	@echo "plugin.json OK"
