lint:
	@echo $@
	.venv/bin/python -m ruff format app demo tests
	@echo $@
	.venv/bin/python -m ruff check --fix app demo tests