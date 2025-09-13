
PYTHON := $(firstword $(wildcard .venv/bin/python) $(wildcard .venv/Scripts/python.exe) python)

lint:
	@echo $@
	$(PYTHON) -m ruff format app demo tests
	@echo $@
	$(PYTHON) -m ruff check --fix app demo tests
	

generate-assessment-dataset:
	@echo $@
	@PYTHONPATH=$(shell pwd) python scripts/generate_assessment_dataset.py

run-demo:
	@echo $@
	@PYTHONPATH=$(shell pwd) python demo/demo.py


.PHONY: scrape-unibe-innovation
scrape-unibe-innovation:
	@echo $@
	@rm -rf crawler/jobs/innovation
	@rm -f  crawler/data/raw/innovation.jsonl
	@PYTHONPATH=$(shell pwd) scrapy runspider crawler/unibe_crawler.py -a config=crawler/configs/innovation.yml -o crawler/data/raw/innovation.jsonl -s JOBDIR=crawler/jobs/innovation

convert-mht-to-txt:
	@echo $@
	@PYTHONPATH=$(shell pwd) python crawler/one_note_mht_reader.py crawler/data/raw/Notizbuch_fuer_Ideenlabor.mht crawler/data/raw/Notizbuch_fuer_Ideenlabor.txt

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

unit-tests:
	@echo $@
	@PYTHONPATH=$(shell pwd) pytest -v tests/unit/