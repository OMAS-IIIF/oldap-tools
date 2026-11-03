IMAGE = lrosenth/oldap-tools
PLATFORMS = linux/amd64,linux/arm64

VERSION = $(shell git describe --tags --abbrev=0)
PYPI_VERSION = $(shell git describe --tags --abbrev=0 | sed 's/^v//')

.PHONY: help
help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  show-version       Show current version"
	@echo "  bump-patch-level   increase patch level of version number and push"
	@echo "  bump-minor-level   increase patch level of version number and push"
	@echo "  bump-major-level   increase patch level of version number and push"
	@echo "  docker-build       Disabled here; use the Jena candidate workflow"
	@echo "  dump-fasnacht      dump fasnacht data"
	@echo "  load-fasnacht      load fasnacht data"


.PHONY: bump-patch-level
bump-patch-level:
	poetry run bump-my-version bump patch
	git push

.PHONY: bump-minor-level
bump-minor-level:
	poetry run bump-my-version bump minor
	git push

.PHONY: bump-major-level
bump-major-level:
	poetry run bump-my-version-version bump major
	git push

.PHONY: dump-fasnacht
dump-fasnacht:
	poetry run oldap-tools -u rosenth -p RioGrande project dump --out fasnacht.trig.gz fasnacht

.PHONY: load-fasnacht
load-fasnacht:
	poetry run oldap-tools -u rosenth -p RioGrande project load --inf fasnacht.trig.gz

.PHONY: show-version
show-version:
	@echo "VERSION=${VERSION}"

# Normal GraphDB/PyPI publication is disabled in this migration checkout.
# Build the source-matched Jena candidates through sibling oldap-setup.
.PHONY: ensure-pypi-release docker-build
ensure-pypi-release:
	@echo "Normal release publication is disabled in this migration checkout. Use oldap-setup/scripts/jena-images.py (see its README)." >&2
	@exit 1
docker-build:
	@echo "Normal release publication is disabled in this migration checkout. Use oldap-setup/scripts/jena-images.py (see its README)." >&2
	@exit 1
