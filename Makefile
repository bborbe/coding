SHELL := /bin/bash

.PHONY: precommit
precommit: check-links

.PHONY: check-links
check-links:
	@echo "Checking links in README.md and llms.txt..."
	@EXIT=0; \
	for file in README.md llms.txt; do \
		grep -oP '\]\(\K[^)]+' "$$file" 2>/dev/null | grep -v '^http' | grep -v '^#' | while read -r link; do \
			if [ ! -f "$$link" ]; then \
				echo "BROKEN: $$file -> $$link"; \
				EXIT=1; \
			fi; \
		done; \
	done; \
	if [ "$$EXIT" -eq 1 ]; then exit 1; fi
	@echo "All links OK"
