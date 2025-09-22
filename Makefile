
PYTHON := $(firstword $(wildcard .venv/bin/python) $(wildcard .venv/Scripts/python.exe) python)
VERSION=$(shell grep '^version' pyproject.toml | head -1 | cut -d '"' -f2)

lint:
	@echo $@
	$(PYTHON) -m ruff format app demo tests scripts
	@echo $@
	$(PYTHON) -m ruff check --fix app demo tests scripts
	

generate-assessment-dataset:
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) python scripts/generate_assessment_dataset.py


run-demo:
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) python demo/demo.py


.PHONY: scrape-unibe-innovation
scrape-unibe-innovation:
	@echo $@
	@rm -rf scripts/crawler/jobs/innovation
	@rm -f  scripts/crawler/data/raw/innovation.jsonl
	@PYTHONPATH=$(shell pwd) scrapy runspider scripts/crawler/unibe_crawler.py -a config=scripts/crawler/configs/innovation.yml -o scripts/crawler/data/raw/innovation.jsonl -s JOBDIR=scripts/crawler/jobs/innovation

convert-mht-to-txt-innovation:
	@echo $@
	@PYTHONPATH=$(shell pwd) python scripts/crawler/one_note_mht_reader.py scripts/crawler/data/raw/Notizbuch_fuer_Ideenlabor.mht scripts/crawler/data/raw/Notizbuch_fuer_Ideenlabor.txt


build-image-dev:
	@echo $@
	@ENV=dev VERSION=$(VERSION) docker compose build

build-image-prod:
	@echo $@
	@ENV=prod VERSION=$(VERSION) docker compose build

compose-up-dev:
	@echo $@
	@ENV=dev VERSION=$(VERSION) docker compose up -d

compose-up-prod:
	@echo $@
	@ENV=prod VERSION=$(VERSION) docker compose up -d

compose-down-dev:
	@echo $@
	@ENV=dev VERSION=$(VERSION) docker compose down

compose-down-prod:
	@echo $@
	@ENV=prod VERSION=$(VERSION) docker compose down

unit-tests:
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) pytest -v tests/unit/

e2e-tests:
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) pytest -v tests/e2e/