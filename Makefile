
VERSION = $(shell git describe --tags --abbrev=0)

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
