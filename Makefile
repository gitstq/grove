.PHONY: help install test check lint build clean run

PY ?= python3

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

install: ## Editable install (console script `grove`)
	$(PY) -m pip install -e .

test: ## Run the full unit-test suite
	$(PY) -m unittest discover -s tests -v

check: ## Byte-compile everything (syntax smoke test)
	$(PY) -m compileall -q src tests

build: check test ## Build wheel + sdist into dist/
	$(PY) -m pip install --quiet build
	$(PY) -m build

wheel: check ## Build a wheel without the `build` package
	$(PY) -m pip wheel . -w dist --no-deps

run: ## Run Grove directly from source, e.g. `make run ARGS="list"`
	PYTHONPATH=src $(PY) -m grove $(ARGS)

clean: ## Remove build artifacts and caches
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache __pycache__ \
		$(find . -name __pycache__ -type d)
