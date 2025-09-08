lint:
	@echo $@
	.venv/bin/python -m ruff format app demo tests
	@echo $@
	.venv/bin/python -m ruff check --fix app demo tests

run-demo:
	@echo $@
	@PYTHONPATH=$(shell pwd) python demo/demo.py


VERSION=$(shell grep '^version' pyproject.toml | head -1 | cut -d '"' -f2)

build-image:
	@echo $@
	VERSION=$(VERSION) docker compose build

compose-up:
	@echo $@
	VERSION=$(VERSION) docker compose up -d

compose-down:
	@echo $@
	VERSION=$(VERSION) docker compose down