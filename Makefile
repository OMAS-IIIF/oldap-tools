
VERSION = $(shell git describe --tags --abbrev=0)

.PHONY: bump-patch-level
bump-patch-level:
	poetry run bump2version patch
	git push

.PHONY: bump-minor-level
bump-minor-level:
	poetry run bump2version minor
	git push

.PHONY: bump-major-level
bump-major-level:
	poetry run bump2version major
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
