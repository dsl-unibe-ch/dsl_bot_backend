lint:
	@echo $@
	.venv/bin/python -m ruff format projects tests/projects/my_project
	@echo $@
	.venv/bin/python -m ruff check --fix projects tests/projects/my_project