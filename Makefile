PYTHON ?= python3
DIST_DIR ?= $(CURDIR)/python/dist
VERSION ?= $(shell $(PYTHON) -c 'import tomllib; print(tomllib.load(open("python/pyproject.toml", "rb"))["project"]["version"])')
TEST_ARGS ?=

.PHONY: help test test-unit test-oidc test-vpn build package-check check publish

help:
	@printf '%s\n' \
	  'Targets:' \
	  '  test           Run the three SDK test suites' \
	  '  test-unit      Run unit tests (options: TEST_ARGS="-t selector")' \
	  '  test-oidc      Run the OIDC integration suite' \
	  '  test-vpn       Run the WireGuard integration suite' \
	  '  build          Build the Python wheel and source archive' \
	  '  package-check  Build and validate distribution artifacts' \
	  '  check          Run all tests and validate the package' \
	  '  publish        Verify and publish the current version to PyPI'

test: test-unit test-oidc test-vpn

test-unit:
	bash scripts/test-unit.sh $(TEST_ARGS)

test-oidc:
	bash scripts/test-oidc.sh $(TEST_ARGS)

test-vpn:
	bash scripts/test-vpn.sh $(TEST_ARGS)

build:
	$(PYTHON) -m build --outdir "$(DIST_DIR)" python

package-check:
	$(PYTHON) -m build --outdir "$(DIST_DIR)" python
	$(PYTHON) -m twine check "$(DIST_DIR)"/ttlama_sdk-$(VERSION)*

check: test package-check

publish: check
	@test -n "$${TWINE_PASSWORD:-}" || { printf 'TWINE_PASSWORD must contain a PyPI API token.\n' >&2; exit 1; }
	TWINE_USERNAME=__token__ $(PYTHON) -m twine upload --non-interactive --repository pypi "$(DIST_DIR)"/ttlama_sdk-$(VERSION)*