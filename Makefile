PYTHON := $(firstword $(wildcard .venv/bin/python) $(wildcard .venv/Scripts/python.exe) python)
VERSION=$(shell grep '^version' pyproject.toml | head -1 | cut -d '"' -f2)

lint:
	@echo $@
	$(PYTHON) -m ruff format app demo tests scripts
	@echo $@
	$(PYTHON) -m ruff check --fix app demo tests scripts

etl-pipeline-azure-search:
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) python scripts/rag_data/etl_azure_search.py	

generate-assessment-dataset:
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) python scripts/assessment_data/generate_assessment_dataset.py

run-demo: build-image-dev compose-down-dev compose-up-dev
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
	@ENV=dev; \
	. ./.env.$${ENV}; \
	ENV=$${ENV} VERSION=$(VERSION) AZURE_CONTAINER_REGISTRY_LOGIN_SERVER=$${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER} docker compose --project-name kioskbot-backend-$${ENV} build

build-image-prod:
	@ENV=prod; \
	. ./.env.$${ENV}; \
	ENV=$${ENV} VERSION=$(VERSION) AZURE_CONTAINER_REGISTRY_LOGIN_SERVER=$${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER} docker compose --project-name kioskbot-backend-$${ENV} build

compose-up-dev:
	@echo $@
	@ENV=dev; \
	. ./.env.$${ENV}; \
	ENV=$${ENV} VERSION=$(VERSION) AZURE_CONTAINER_REGISTRY_LOGIN_SERVER=$${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER} docker compose --project-name kioskbot-backend-$${ENV} up -d

compose-up-prod:
	@echo $@
	@ENV=prod; \
	. ./.env.$${ENV}; \
	ENV=$${ENV} VERSION=$(VERSION) AZURE_CONTAINER_REGISTRY_LOGIN_SERVER=$${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER} docker compose --project-name kioskbot-backend-$${ENV} up -d

compose-down-dev:
	@echo $@
	@ENV=dev; \
	. ./.env.$${ENV}; \
	ENV=$${ENV} VERSION=$(VERSION) AZURE_CONTAINER_REGISTRY_LOGIN_SERVER=$${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER} docker compose --project-name kioskbot-backend-$${ENV} down

compose-down-prod:
	@echo $@
	@ENV=prod; \
	. ./.env.$${ENV}; \
	ENV=$${ENV} VERSION=$(VERSION) AZURE_CONTAINER_REGISTRY_LOGIN_SERVER=$${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER} docker compose --project-name kioskbot-backend-$${ENV} down

push-image-dev:
	@ENV=dev; \
	. ./.env.$${ENV}; \
	read -p "Username: " USERNAME; \
	read -s -p "Password: " PASSWORD; echo; \
	echo $$PASSWORD | docker login $${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER} -u $$USERNAME --password-stdin; \
	if ! docker manifest inspect $${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api:${VERSION}-$${ENV} >/dev/null 2>&1; then \
		echo "Image does not exist in registry, pushing..."; \
		docker push $${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api:${VERSION}-$${ENV}; \
	else \
		echo "Image already exists in registry, skipping push."; \
	fi

push-image-prod:
	@ENV=prod; \
	. ./.env.$${ENV}; \
	read -p "Username: " USERNAME; \
	read -s -p "Password: " PASSWORD; echo; \
	echo $$PASSWORD | docker login $${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER} -u $$USERNAME --password-stdin; \
	if ! docker manifest inspect $${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api:${VERSION}-$${ENV} >/dev/null 2>&1; then \
		echo "Image does not exist in registry, pushing..."; \
		docker push $${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api:${VERSION}-$${ENV}; \
	else \
		echo "Image already exists in registry, skipping push."; \
	fi

unit-tests: build-image-dev compose-down-dev compose-up-dev
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) pytest -v tests/unit/

e2e-tests: build-image-dev compose-down-dev compose-up-dev
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) pytest -v tests/e2e/


# ---- config ----
TF      ?= terraform
TF_DIR  ?= scripts/terraform/azure
ENV     ?= dev
TFVARS  ?= environments/$(ENV).tfvars
AZ_SUBSCRIPTION_ID ?= $(shell az account show --query id -o tsv 2>/dev/null)

# ---- phony targets ----
.PHONY: help login set-sub init workspace plan apply destroy output fmt validate clean

help:
	@echo "Usage:"
	@echo "  make login                 # az login"
	@echo "  make set-sub               # set Azure subscription (needs AZ_SUBSCRIPTION_ID)"
	@echo "  make init                  # terraform init"
	@echo "  make workspace ENV=dev     # select/create workspace"
	@echo "  make plan ENV=dev          # plan with environments/dev.tfvars"
	@echo "  make apply ENV=dev         # apply with environments/dev.tfvars"
	@echo "  make destroy ENV=dev       # destroy with environments/dev.tfvars"
	@echo "  make output                # show outputs"
	@echo "  make fmt validate          # housekeeping"
	@echo "  make clean                 # remove local tf state/cache"

az-login:
	az login

az-set-subscription:
	@if [ -n "$(AZ_SUBSCRIPTION_ID)" ]; then \
		echo "Setting subscription to $(AZ_SUBSCRIPTION_ID)"; \
		az account set --subscription "$(AZ_SUBSCRIPTION_ID)"; \
	else \
		echo "AZ_SUBSCRIPTION_ID not set; skipping az account set"; \
	fi

az-get-tenant-id:
	@az account show --query tenantId -o tsv
	

terraform-init:
	$(TF) -chdir=$(TF_DIR) init -upgrade

terraform-workspace:
	@$(TF) -chdir=$(TF_DIR) workspace select $(ENV) >/dev/null 2>&1 || \
	$(TF) -chdir=$(TF_DIR) workspace new $(ENV)

terraform-workspace-dev:
	@$(MAKE) terraform-workspace ENV=dev

terraform-workspace-prod:
	@$(MAKE) terraform-workspace ENV=prod

terraform-require-tfvars:
	@test -f "$(TF_DIR)/$(TFVARS)" || (echo "ERROR: missing $(TF_DIR)/$(TFVARS)"; exit 1)

terraform-plan: terraform-require-tfvars terraform-workspace
	$(TF) -chdir=$(TF_DIR) plan -var-file=$(TFVARS) -out=$(ENV).plan

terraform-plan-dev:
	@$(MAKE) terraform-plan ENV=dev

terraform-plan-prod:
	@$(MAKE) terraform-plan ENV=prod

terraform-apply: 
	@test -f "${TF_DIR}/${ENV}.plan" || { echo "No plan at ${TF_DIR}/${ENV}.plan. Run 'make terraform-plan-${ENV}' first."; exit 1; }
	$(TF) -chdir=$(TF_DIR) apply -auto-approve ${ENV}.plan

terraform-apply-dev:
	@$(MAKE) terraform-apply ENV=dev

terraform-apply-prod:
	@$(MAKE) terraform-apply ENV=prod

terraform-destroy: terraform-require-tfvars terraform-workspace
	$(TF) -chdir=$(TF_DIR) destroy -auto-approve -var-file=$(TFVARS)

terraform-destroy-dev:
	@$(MAKE) terraform-destroy ENV=dev

terraform-destroy-prod:
	@$(MAKE) terraform-destroy ENV=prod

terraform-output:
	@$(TF) -chdir=$(TF_DIR) workspace select $(ENV) >/dev/null 2>&1 || \
	  { echo "Workspace '$(ENV)' not found. Run plan/apply first."; exit 1; }
	$(TF) -chdir=$(TF_DIR) output -json

terraform-output-var:
	@$(TF) -chdir=$(TF_DIR) workspace select $(ENV) >/dev/null 2>&1 || \
	  { echo "Workspace '$(ENV)' not found. Run plan/apply first."; exit 1; }
	@$(TF) -chdir=$(TF_DIR) output -json | jq -r '.${VAR}.value'

terraform-output-dev:  
	@$(MAKE) terraform-output ENV=dev

terraform-output-prod: 
	@$(MAKE) terraform-output ENV=prod

terraform-fmt:
	$(TF) -chdir=$(TF_DIR) fmt -recursive

terraform-validate:
	$(TF) -chdir=$(TF_DIR) validate
