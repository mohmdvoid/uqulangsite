# uqulang.com — everything a contributor needs. Python 3.9+, nothing else.

PYTHON ?= python3
PORT ?= 4173

.PHONY: help build check serve clean

help:
	@echo "make build   regenerate the site from src/"
	@echo "make check   verify generated output, links, headings, metadata"
	@echo "make serve   build, then serve on http://localhost:$(PORT)"
	@echo "make clean   remove generated files"

build:
	@$(PYTHON) tools/build.py

check: build
	@$(PYTHON) tools/build.py --check
	@$(PYTHON) tools/check_links.py

serve: build
	@echo "http://localhost:$(PORT)"
	@$(PYTHON) -m http.server $(PORT)

clean:
	@rm -rf assets/css/site.*.css sitemap.xml search-index.json
	@rm -f 404.html index.html
	@rm -rf ar blog docs install universities
	@echo "generated files removed — run 'make build' to restore them"
