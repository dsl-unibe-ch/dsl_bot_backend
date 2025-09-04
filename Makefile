lint:
	@echo $@
	.venv/bin/python -m ruff format app demo tests
	@echo $@
	.venv/bin/python -m ruff check --fix app demo tests

run_demo:
	@echo $@
	@PYTHONPATH=$(shell pwd) python demo/demo.py