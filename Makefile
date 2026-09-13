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
	@echo "  docker-build       ensure PyPI release, build Docker image and push it"
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

# Docker installs the tagged package from PyPI, not from this working tree.
# Only a confirmed missing release triggers a fresh Poetry build/publication.
# Existing releases are reused; tag/version mismatch or network errors abort.
# Uses configured Poetry/PyPI credentials and never uploads stale dist/ files.
.PHONY: ensure-pypi-release docker-build
ensure-pypi-release:
	poetry run python scripts/ensure_pypi_release.py --version "$(PYPI_VERSION)"

docker-build: ensure-pypi-release
	docker buildx build --platform $(PLATFORMS) \
		--build-arg OLDAP_TOOLS_VERSION=$(PYPI_VERSION) \
		-t $(IMAGE):$(VERSION) \
		--push \
		.
