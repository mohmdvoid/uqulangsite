# uqulang.com — everything a contributor needs.
#
# Requirements: Python 3.9+. `make setup` creates a local .venv with the one
# build dependency (Markdown); nothing is installed system-wide.

VENV ?= .venv
PYTHON := $(shell [ -x $(VENV)/bin/python ] && echo $(VENV)/bin/python || echo python3)
PORT ?= 4173

.PHONY: help setup build check serve dist clean

help:
	@echo "make setup   create .venv and install build dependencies"
	@echo "make build   regenerate the site from src/"
	@echo "make check   verify generated output, links, headings, metadata"
	@echo "make serve   build, then serve on http://localhost:$(PORT)"
	@echo "make dist    minify and precompress into dist/ for deployment"
	@echo "make clean   remove generated files"
	@echo ""
	@echo "using: $(PYTHON)"

setup:
	@python3 -m venv $(VENV)
	@$(VENV)/bin/pip install --quiet --upgrade pip
	@$(VENV)/bin/pip install --quiet -r requirements.txt
	@echo "ready — run 'make serve'"

build:
	@$(PYTHON) tools/build.py

check: build
	@$(PYTHON) tools/build.py --check
	@$(PYTHON) tools/check_links.py

serve: build
	@$(PYTHON) tools/serve.py --port $(PORT)

dist: check
	@$(PYTHON) tools/postprocess.py

clean:
	@rm -rf dist assets/css/site.*.css sitemap.xml search-index.json feed.xml
	@rm -f 404.html index.html
	@rm -rf ar blog docs install universities
	@rm -f 500.html
	@echo "generated files removed — run 'make build' to restore them"
