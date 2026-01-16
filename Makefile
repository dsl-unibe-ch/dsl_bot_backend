PYTHON := $(firstword $(wildcard .venv/bin/python) $(wildcard .venv/Scripts/python.exe) python)
VERSION=$(shell grep '^version' pyproject.toml | head -1 | cut -d '"' -f2)
FE_DIR := ../kioskbot_frontend
FE_REPO := https://github.com/dsl-unibe-ch/kioskbot_frontend.git
FE_PORT := 5173

lint:
	@echo $@
	$(PYTHON) -m ruff format app demo tests scripts
	@echo $@
	$(PYTHON) -m ruff check --fix app demo tests scripts

etl-pipeline-azure-search-dev:
	@echo $@
	@ENV=dev PYTHONPATH=$(shell pwd) python scripts/rag_data/etl_azure_search.py	

etl-pipeline-azure-search-prod:
	@echo $@
	@ENV=prod PYTHONPATH=$(shell pwd) python scripts/rag_data/etl_azure_search.py

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

collect-urls-qse:
	@echo $@
	@rm -rf scripts/crawler/jobs/qse
	@rm -f  scripts/crawler/data/raw/qse.jsonl
	@rm -f  scripts/crawler/data/qse/url_list.jsonl
	@PYTHONPATH=$(shell pwd) scrapy runspider scripts/crawler/unibe_crawler.py -a config=scripts/crawler/configs/qse.yml -o scripts/crawler/data/qse/url_list.jsonl -s JOBDIR=scripts/crawler/jobs/qse

extract-content-qse:
	@echo $@	
	@rm -rf scripts/crawler/data/qse/qse_content.jsonl
	@rm -rf scripts/crawler/data/qse/processed_data.xlsx
	@PYTHONPATH=$(shell pwd) python scripts/crawler/url_content_extractor.py --jsonl_file scripts/crawler/data/qse/url_list.jsonl --customer_name qse
	@PYTHONPATH=$(shell pwd) python scripts/crawler/pdf_content_extractor.py --jsonl_file scripts/crawler/data/qse/url_list.jsonl --customer_name qse
	@ENV=dev PYTHONPATH=$(shell pwd) python scripts/crawler/post_processing.py

scrape-qse:
	@echo $@
	@make collect-urls-qse
	@make extract-content-qse

build-image-dev:
	@ENV=dev; \
	. ./.env.$${ENV}; \
	docker buildx build --platform linux/amd64,linux/arm64 \
	-t $${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api:$(VERSION)-$${ENV} \
	-f Dockerfile . --load

build-image-prod:
	@ENV=prod; \
	. ./.env.$${ENV}; \
	docker buildx build --platform linux/amd64,linux/arm64 \
	-t $${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api:$(VERSION)-$${ENV} \
	-f Dockerfile . --load

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


# ---- E2E Testing with Local FE and BE ----
.PHONY: setup-fe-local setup-be-local e2e-local2local stop-fe-local

# currently we are using the send-url branch of the frontend repository
setup-fe-local:
	@echo "Setting up Frontend for local E2E testing..."
	@if [ ! -d "$(FE_DIR)" ]; then \
		echo "Cloning frontend repository (send-url branch)..."; \
		git clone -b send-url $(FE_REPO) $(FE_DIR); \
	else \
		echo "Frontend repository already exists at $(FE_DIR)"; \
		echo "Pulling latest changes from send-url branch..."; \
		cd $(FE_DIR) && git fetch origin && git checkout send-url && git pull origin send-url || echo "Warning: Could not pull latest changes from send-url branch"; \
	fi
	@echo "Installing frontend dependencies..."
	@cd $(FE_DIR) && pnpm install
	@echo "Configuring PUBLIC_API environment variable..."
	@BACKEND_URL=$$(grep -E '^BACKEND_URL=' .env.dev | cut -d'=' -f2- | tr -d '"' | sed 's:/*$$::'); \
	echo "Detected BACKEND_URL: $$BACKEND_URL"; \
	if [ -f "$(FE_DIR)/.env" ]; then \
		grep -v '^PUBLIC_API=' "$(FE_DIR)/.env" > "$(FE_DIR)/.env.tmp" || true; \
		mv "$(FE_DIR)/.env.tmp" "$(FE_DIR)/.env"; \
	fi; \
	echo "PUBLIC_API=$$BACKEND_URL" >> "$(FE_DIR)/.env"
	@echo "Frontend setup complete!"

setup-be-local:
	@echo "Setting up Backend for local E2E testing..."
	@echo "Installing Chromium for Playwright..."
	@$(PYTHON) -m playwright install chromium
	@echo "Configuring .env.dev for local testing..."
	@grep -v '^FRONTEND_URL=' .env.dev > .env.dev.tmp || true
	@grep -v '^BACKEND_URL=' .env.dev.tmp > .env.dev.tmp2 || true
	@echo "FRONTEND_URL=http://localhost:$(FE_PORT)" >> .env.dev.tmp2
	@echo "BACKEND_URL=http://localhost:8000" >> .env.dev.tmp2
	@mv .env.dev.tmp2 .env.dev
	@rm -f .env.dev.tmp
	@echo "Backend E2E setup complete!"

stop-fe-local:
	@echo "Stopping frontend server..."
	@if [ -f .fe-server.pid ]; then \
		FE_PID=$$(cat .fe-server.pid); \
		if ps -p $$FE_PID > /dev/null 2>&1; then \
			echo "Killing frontend server process $$FE_PID..."; \
			kill $$FE_PID 2>/dev/null || true; \
			sleep 2; \
			kill -9 $$FE_PID 2>/dev/null || true; \
		fi; \
		rm -f .fe-server.pid; \
	fi
	@pkill -f "vite.*:$(FE_PORT)" 2>/dev/null || true
	@echo "Frontend server stopped."

e2e-local2local: setup-be-local setup-fe-local build-image-dev compose-down-dev compose-up-dev
	@echo "========================================"
	@echo "Local FE to Local BE E2E Test Workflow"
	@echo "========================================"
	@echo ""
	@echo "Stopping any existing frontend servers..."
	@$(MAKE) stop-fe-local
	@echo "Starting frontend server in background..."
	@(cd $(FE_DIR) && pnpm dev > $(shell pwd)/.fe-server.log 2>&1 & echo $$! > $(shell pwd)/.fe-server.pid)
	@echo "Waiting for frontend server to be ready..."
	@timeout=60; \
	while ! curl -s http://localhost:$(FE_PORT) > /dev/null 2>&1; do \
		timeout=$$((timeout - 1)); \
		if [ $$timeout -le 0 ]; then \
			echo "ERROR: Frontend server failed to start within 60 seconds"; \
			echo "Frontend server logs:"; \
			cat .fe-server.log 2>/dev/null || echo "No logs available"; \
			$(MAKE) stop-fe-local; \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@echo "Frontend server is ready!"
	@echo "Running E2E tests..."
	@ENV=dev PYTHONPATH=$(shell pwd) pytest -v tests/e2e/ || \
		(echo "Tests failed, cleaning up..."; $(MAKE) stop-fe-local; exit 1)
	@echo "Tests completed successfully!"
	@$(MAKE) stop-fe-local
	@rm -f .fe-server.log
	@echo ""
	@echo "========================================"
	@echo "Local FE to Local BE E2E Test Complete!"
	@echo "========================================"

# ---- E2E Testing with Local FE and Remote BE (AKS) ----
.PHONY: get-my-ip setup-aks-allow-my-ip deploy-be-remote get-aks-external-ip setup-fe-remote e2e-local2remote e2e-remote2remote

get-my-ip:
	@echo "Detecting your external IP..."
	@curl -s https://api.ipify.org

setup-aks-allow-my-ip:
	@echo "Setting up AKS to allow your IP for remote testing..."
	@MY_IP=$$(curl -s https://api.ipify.org); \
	echo "Your external IP: $$MY_IP"; \
	TFVARS_FILE=scripts/terraform/azure/environments/$(ENV).tfvars; \
	if [ ! -f "$$TFVARS_FILE" ]; then \
		echo "ERROR: $$TFVARS_FILE not found"; \
		exit 1; \
	fi; \
	echo "Updating $$TFVARS_FILE..."; \
	grep -v '^aks_allowed_external_ips' "$$TFVARS_FILE" > "$$TFVARS_FILE.tmp" || true; \
	echo 'aks_allowed_external_ips = ["'$$MY_IP'/32"]' >> "$$TFVARS_FILE.tmp"; \
	mv "$$TFVARS_FILE.tmp" "$$TFVARS_FILE"; \
	echo "Updated $$TFVARS_FILE with your IP: $$MY_IP/32"

deploy-be-remote:
	@echo "Deploying backend to AKS ($(ENV))..."
	@echo "Step 1: Planning Terraform..."
	@$(MAKE) terraform-plan-$(ENV)
	@echo "Step 2: Applying Terraform..."
	@$(MAKE) terraform-apply-$(ENV)
	@echo "Step 3: Building Docker image..."
	@$(MAKE) build-image-$(ENV)
	@echo "Step 4: Pushing Docker image..."
	@$(MAKE) push-image-$(ENV)
	@echo "Step 5: Upgrading Helm deployment..."
	@$(MAKE) helm-upgrade-$(ENV)
	@echo "Backend deployment to AKS is complete!"

get-aks-external-ip:
	@echo "Getting AKS external IP for $(ENV)..." >&2
	@KUBECONFIG_FILE=scripts/terraform/azure/outputs/$(ENV).kubeconfig; \
	if [ ! -f "$$KUBECONFIG_FILE" ]; then \
		echo "ERROR: $$KUBECONFIG_FILE not found. Run 'make kubeconfig-$(ENV)' first." >&2; \
		exit 1; \
	fi; \
	EXTERNAL_IP=$$(KUBECONFIG="$$KUBECONFIG_FILE" kubectl get svc -n kioskbot-$(ENV) -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].ip}' 2>/dev/null); \
	if [ -z "$$EXTERNAL_IP" ]; then \
		echo "ERROR: Could not find external IP. Make sure the service is deployed." >&2; \
		exit 1; \
	fi; \
	echo "$$EXTERNAL_IP"

update-apim-backend-url:
	@echo "Updating apim_backend_url for $(ENV)..." >&2
	@TFVARS_FILE=scripts/terraform/azure/environments/$(ENV).tfvars; \
	if [ ! -f "$$TFVARS_FILE" ]; then \
		echo "ERROR: $$TFVARS_FILE not found." >&2; \
		exit 1; \
	fi; \
	EXTERNAL_IP=$$($(MAKE) --no-print-directory get-aks-external-ip ENV=$(ENV)); \
	BACKEND_URL="http://$$EXTERNAL_IP:8000"; \
	echo "Setting apim_backend_url=$$BACKEND_URL"; \
	grep -v '^apim_backend_url' "$$TFVARS_FILE" > "$$TFVARS_FILE.tmp" || true; \
	echo "apim_backend_url = \"$$BACKEND_URL\"" >> "$$TFVARS_FILE.tmp"; \
	mv "$$TFVARS_FILE.tmp" "$$TFVARS_FILE"

setup-fe-remote:
	@echo "Setting up Frontend for remote backend testing ($(ENV))..."
	@if [ ! -d "$(FE_DIR)" ]; then \
		echo "Cloning frontend repository (send-url branch)..."; \
		git clone -b send-url $(FE_REPO) $(FE_DIR); \
	else \
		echo "Frontend repository already exists at $(FE_DIR)"; \
		echo "Pulling latest changes from send-url branch..."; \
		cd $(FE_DIR) && git fetch origin && git checkout send-url && git pull origin send-url || echo "Warning: Could not pull latest changes from send-url branch"; \
	fi
	@echo "Installing frontend dependencies..."
	@cd $(FE_DIR) && pnpm install
	@echo "Getting AKS external IP..."
	@EXTERNAL_IP=$$($(MAKE) --no-print-directory get-aks-external-ip ENV=$(ENV)); \
	echo "AKS External IP: $$EXTERNAL_IP"; \
	BACKEND_URL_REMOTE="http://$$EXTERNAL_IP:8000"; \
	echo "Configuring frontend to use remote backend: $$BACKEND_URL_REMOTE"; \
	if [ -f "$(FE_DIR)/.env" ]; then \
		grep -v '^PUBLIC_API=' "$(FE_DIR)/.env" > "$(FE_DIR)/.env.tmp" || true; \
		mv "$(FE_DIR)/.env.tmp" "$(FE_DIR)/.env"; \
	fi; \
	echo "PUBLIC_API=$$BACKEND_URL_REMOTE" >> "$(FE_DIR)/.env"
	@echo "Configuring backend .env.$(ENV) with FRONTEND_URL..."
	@grep -v '^FRONTEND_URL=' .env.$(ENV) > .env.$(ENV).tmp || true
	@echo "FRONTEND_URL=http://localhost:$(FE_PORT)" >> .env.$(ENV).tmp
	@grep -v '^BACKEND_URL=' .env.$(ENV).tmp > .env.$(ENV).tmp2 || true
	@EXTERNAL_IP=$$($(MAKE) --no-print-directory get-aks-external-ip ENV=$(ENV)); \
	echo "BACKEND_URL=http://$$EXTERNAL_IP:8000" >> .env.$(ENV).tmp2
	@mv .env.$(ENV).tmp2 .env.$(ENV)
	@rm -f .env.$(ENV).tmp
	@echo "Frontend setup for remote backend testing is complete!"

e2e-local2remote:
	@echo "========================================"
	@echo "Local FE to Remote BE E2E Test Workflow ($(ENV))"
	@echo "========================================"
	@echo ""
	@echo "Step 1/3: Setting up AKS to allow your IP..."
	@$(MAKE) setup-aks-allow-my-ip ENV=$(ENV)
	@echo ""
	@echo "Step 2/3: Deploying backend to AKS..."
	@$(MAKE) terraform-deploy-$(ENV)
	@echo ""
	@echo "Step 3/3: Running E2E tests..."
	@$(MAKE) setup-fe-remote ENV=$(ENV)
	@echo "Stopping any existing frontend servers..."
	@$(MAKE) stop-fe-local
	@echo "Starting frontend server in background..."
	@(cd $(FE_DIR) && pnpm dev > $(shell pwd)/.fe-server.log 2>&1 & echo $$! > $(shell pwd)/.fe-server.pid)
	@echo "Waiting for frontend server to be ready..."
	@timeout=60; \
	while ! curl -s http://localhost:$(FE_PORT) > /dev/null 2>&1; do \
		timeout=$$((timeout - 1)); \
		if [ $$timeout -le 0 ]; then \
			echo "ERROR: Frontend server failed to start within 60 seconds"; \
			echo "Frontend server logs:"; \
			cat .fe-server.log 2>/dev/null || echo "No logs available"; \
			$(MAKE) stop-fe-local; \
			exit 1; \
		fi; \
		sleep 1; \
	done
	@echo "Frontend server is ready!"
	@echo "Running E2E tests with local FE and remote BE..."
	@ENV=$(ENV) PYTHONPATH=$(shell pwd) pytest -v tests/e2e/ || \
		(echo "Tests failed, cleaning up..."; $(MAKE) stop-fe-local; exit 1)
	@$(MAKE) stop-fe-local
	@rm -f .fe-server.log
	@echo ""
	@echo "========================================"
	@echo "Local FE to Remote BE Test Complete!"
	@echo "========================================"

e2e-remote2remote:
	@echo "========================================"
	@echo "Remote FE to Remote BE E2E Test Workflow ($(ENV))"
	@echo "========================================"
	@echo ""
	@echo "Step 1/3: Setting up AKS to allow frontend IP..."
	@if [ -z "$(FRONTEND_IP)" ]; then \
		echo "ERROR: FRONTEND_IP is required. Usage: make e2e-remote2remote ENV=dev FRONTEND_IP=<ip> FRONTEND_URL=<url>"; \
		exit 1; \
	fi; \
	if [ -z "$(FRONTEND_URL)" ]; then \
		echo "ERROR: FRONTEND_URL is required. Usage: make e2e-remote2remote ENV=dev FRONTEND_IP=<ip> FRONTEND_URL=<url>"; \
		exit 1; \
	fi; \
	TFVARS_FILE=scripts/terraform/azure/environments/$(ENV).tfvars; \
	if [ ! -f "$$TFVARS_FILE" ]; then \
		echo "ERROR: $$TFVARS_FILE not found"; \
		exit 1; \
	fi; \
	echo "Updating $$TFVARS_FILE to allow frontend IP: $(FRONTEND_IP)"; \
	grep -v '^aks_allowed_external_ips' "$$TFVARS_FILE" > "$$TFVARS_FILE.tmp" || true; \
	echo 'aks_allowed_external_ips = ["$(FRONTEND_IP)/32"]' >> "$$TFVARS_FILE.tmp"; \
	mv "$$TFVARS_FILE.tmp" "$$TFVARS_FILE"; \
	echo "Updated $$TFVARS_FILE with frontend IP: $(FRONTEND_IP)/32"
	@echo ""
	@echo "Step 2/3: Deploying backend to AKS..."
	@$(MAKE) terraform-deploy-$(ENV)
	@echo ""
	@echo "Step 3/3: Running E2E tests..."
	@echo "Configuring test environment..."
	@EXTERNAL_IP=$$($(MAKE) --no-print-directory get-aks-external-ip ENV=$(ENV)); \
	echo "Frontend URL: $(FRONTEND_URL)"; \
	echo "Backend URL: http://$$EXTERNAL_IP:8000"; \
	grep -v '^FRONTEND_URL=' .env.$(ENV) > .env.$(ENV).tmp || true; \
	grep -v '^BACKEND_URL=' .env.$(ENV).tmp > .env.$(ENV).tmp2 || true; \
	echo "FRONTEND_URL=$(FRONTEND_URL)" >> .env.$(ENV).tmp2; \
	echo "BACKEND_URL=http://$$EXTERNAL_IP:8000" >> .env.$(ENV).tmp2; \
	mv .env.$(ENV).tmp2 .env.$(ENV); \
	rm -f .env.$(ENV).tmp
	@echo "Running E2E tests against remote FE and remote BE..."
	@ENV=$(ENV) PYTHONPATH=$(shell pwd) pytest -v tests/e2e/ || \
		(echo "Tests failed!"; exit 1)
	@echo ""
	@echo "========================================"
	@echo "Remote FE to Remote BE Test Complete! ✓"
	@echo "========================================"
	



load-tests-dev:
	@echo $@
	$(eval BACKEND_URL := $(shell grep -E '^BACKEND_URL=' .env.dev | cut -d'=' -f2- | tr -d '"' | sed 's:/*$$::'))
	@ENV=dev PYTHONPATH=$(shell pwd) locust -f tests/load_test/load_test.py --web-host 0.0.0.0 --host $(BACKEND_URL) -u 50 -r 5 --run-time 3m

# ---- config ----
TF      ?= terraform
TF_DIR  ?= scripts/terraform/azure
ENV     ?= dev
TFVARS  ?= environments/$(ENV).tfvars
AZ_SUBSCRIPTION_ID ?= $(shell az account show --query id -o tsv 2>/dev/null)
ifdef USERPROFILE # if the system is Windows
KUBE_HOME := $(subst \,/,$(USERPROFILE))
KUBECONFIG ?= $(KUBE_HOME)/.kube/config
else # else (the system is not Windows)
KUBECONFIG ?= $(HOME)/.kube/config
endif
DASHBOARD_CHART_VERSION = 7.14.0

# ---- phony targets ----
.PHONY: help login set-sub init workspace plan apply destroy output fmt validate clean

help:
	@echo "Usage:"
	@echo "  make login                 # az login"
	@echo "  make set-subscription               # set Azure subscription (needs AZ_SUBSCRIPTION_ID)"
	@echo "  make init                  # terraform init"
	@echo "  make workspace ENV=dev     # select/create workspace"
	@echo "  make plan ENV=dev          # plan with environments/dev.tfvars"
	@echo "  make apply ENV=dev         # apply with environments/dev.tfvars"
	@echo "  make destroy ENV=dev       # destroy with environments/dev.tfvars"
	@echo "  make output                # show outputs"
	@echo "  make kubeconfig ENV=dev    # write kubeconfig file from TF output"
	@echo "  make k8s-create-namespace-dev   # create K8s namespace (dev)"
	@echo "  make k8s-create-namespace-prod  # create K8s namespace (prod)"
	@echo "  make k8s-create-secrets-dev     # create K8s secrets from .env (dev)"
	@echo "  make k8s-create-secrets-prod    # create K8s secrets from .env (prod)"
	@echo "  make helm-install-dev      # install Helm chart to K8s (dev)"
	@echo "  make helm-install-prod     # install Helm chart to K8s (prod)"
	@echo "  make helm-upgrade-dev      # upgrade Helm release (dev)"
	@echo "  make helm-upgrade-prod     # upgrade Helm release (prod)"
	@echo "  make helm-uninstall-dev    # uninstall Helm release (dev)"
	@echo "  make helm-uninstall-prod   # uninstall Helm release (prod)"
	@echo "  make fmt validate          # housekeeping"
	@echo "  make clean                 # remove local tf state/cache"
	@echo "\nE2E Testing (Local FE + Local BE):"
	@echo "  make e2e-local2local       # Run complete E2E test (setup + run + cleanup)"
	@echo "  make setup-fe-local        # Setup frontend for E2E testing"
	@echo "  make setup-be-local        # Setup backend for E2E testing"
	@echo "  make stop-fe-local         # Stop frontend development server"
	@echo "\nE2E Testing (Local FE + Remote BE on AKS):"
	@echo "  make e2e-local2remote ENV=dev         # Complete: setup IP + deploy + test (ONE COMMAND)"
	@echo "  make get-my-ip                        # Display your external IP"
	@echo "  make setup-aks-allow-my-ip ENV=dev    # Add your IP to AKS allowed list"
	@echo "  make terraform-deploy-dev             # Full deploy: terraform + build + push + helm"
	@echo "  make terraform-deploy-prod            # Full deploy for production"
	@echo "  make deploy-be-remote ENV=dev         # Deploy backend to AKS (legacy)"
	@echo "  make get-aks-external-ip ENV=dev      # Get AKS cluster external IP"
	@echo "  make setup-fe-remote ENV=dev          # Setup FE to connect to remote BE"
	@echo "\nE2E Testing (Remote FE + Remote BE on AKS):"
	@echo "  make e2e-remote2remote ENV=dev FRONTEND_IP=<ip> FRONTEND_URL=<url>   # Deploy BE + run tests"
	@echo "\nKubernetes Dashboard:"
	@echo "  make helm-dashboard-install     # install/upgrade dashboard"
	@echo "  make helm-dashboard-status      # show dashboard release status"
	@echo "  make helm-dashboard-port        # port-forward 8443->443"
	@echo "  make helm-dashboard-uninstall   # uninstall dashboard"
	@echo "  make get-aks-credentials # configures the local kubectl to connect to the AKS cluster"
	@echo "\nGlobal workspace (never destroy):"
	@echo "  make terraform-plan-global   # plan shared Storage & ACR"
	@echo "  make terraform-apply-global  # apply shared Storage & ACR"
	@echo "  make terraform-output-global # outputs for global"
	@echo "  make write-output-to-env-dev # writes the output to the .env.dev file"
	@echo "  make write-output-to-env-prod # writes the output to the .env.prod file"
	@echo "  make write-output-to-env # writes the output to the .env file"

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

terraform-workspace-global:
	@$(MAKE) terraform-workspace ENV=global

terraform-require-tfvars:
	@test -f "$(TF_DIR)/$(TFVARS)" || (echo "ERROR: missing $(TF_DIR)/$(TFVARS)"; exit 1)

terraform-plan: terraform-require-tfvars terraform-workspace
	@ENV=$(ENV); \
	VERSION="$$( $(PYTHON) scripts/terraform/azure/scripts/extract_pyproject_version.py --pyproject pyproject.toml )"; \
	IMAGE_TAG="$${VERSION}-$${ENV}"; \
	$(TF) -chdir=$(TF_DIR) plan -var-file=$(TFVARS) -var="image_tag_override=$${IMAGE_TAG}" -out=$(ENV).plan

terraform-plan-dev:
	@$(MAKE) terraform-plan ENV=dev

terraform-plan-prod:
	@$(MAKE) terraform-plan ENV=prod

terraform-plan-global:
	@$(MAKE) terraform-plan ENV=global

terraform-apply: 
	@test -f "${TF_DIR}/${ENV}.plan" || { echo "No plan at ${TF_DIR}/${ENV}.plan. Run 'make terraform-plan-${ENV}' first."; exit 1; }
	$(TF) -chdir=$(TF_DIR) apply -auto-approve ${ENV}.plan

terraform-apply-dev:
	@$(MAKE) terraform-apply ENV=dev

terraform-apply-prod:
	@$(MAKE) terraform-apply ENV=prod

terraform-apply-global:
	@$(MAKE) terraform-apply ENV=global

terraform-destroy: terraform-require-tfvars terraform-workspace
	$(TF) -chdir=$(TF_DIR) destroy -auto-approve -var-file=$(TFVARS)

terraform-destroy-dev:
	@$(MAKE) terraform-destroy ENV=dev

terraform-destroy-prod:
	@$(MAKE) terraform-destroy ENV=prod

# Explicitly no 'destroy-global' target; protect global workspace
terraform-destroy-global:
	@echo "ERROR: The global workspace must never be destroyed. Aborting." && exit 1


terraform-output:
	@$(TF) -chdir=$(TF_DIR) workspace select $(ENV) >/dev/null 2>&1 || \
	  { echo "Workspace '$(ENV)' not found. Run plan/apply first."; exit 1; }
	@mkdir -p $(TF_DIR)/outputs
	@$(TF) -chdir=$(TF_DIR) output -json | jq -r 'to_entries[] | "\(.key)=\(.value.value)"' | tee $(TF_DIR)/outputs/$(ENV).output
	@echo "Wrote outputs to $(TF_DIR)/outputs/$(ENV).output"

terraform-output-var:
	@$(TF) -chdir=$(TF_DIR) workspace select $(ENV) >/dev/null 2>&1 || \
	  { echo "Workspace '$(ENV)' not found. Run plan/apply first."; exit 1; }
	@$(TF) -chdir=$(TF_DIR) output -json | jq -r '.${VAR}.value'

terraform-output-dev:  
	@$(MAKE) terraform-output ENV=dev

terraform-output-prod: 
	@$(MAKE) terraform-output ENV=prod

terraform-output-global:
	@$(MAKE) terraform-output ENV=global

terraform-fmt:
	$(TF) -chdir=$(TF_DIR) fmt -recursive

terraform-validate:
	$(TF) -chdir=$(TF_DIR) validate

kubeconfig:
	@$(TF) -chdir=$(TF_DIR) workspace select $(ENV) >/dev/null 2>&1 || \
	  { echo "Workspace '$(ENV)' not found. Run plan/apply first."; exit 1; }
	@mkdir -p $(TF_DIR)/outputs
	@$(TF) -chdir=$(TF_DIR) output -raw kube_config_raw > $(TF_DIR)/outputs/$(ENV).kubeconfig
	@echo "Wrote kubeconfig to $(TF_DIR)/outputs/$(ENV).kubeconfig"

kubeconfig-dev:
	@$(MAKE) kubeconfig ENV=dev

kubeconfig-prod:
	@$(MAKE) kubeconfig ENV=prod


write-output-to-env:
	  $(PYTHON) scripts/terraform/azure/scripts/update_output_to_env.py -e $(ENV)

write-output-to-env-dev:
	@$(MAKE) write-output-to-env ENV=dev

write-output-to-env-prod:
	@$(MAKE) write-output-to-env ENV=prod
write-secrets-to-container-file:
	@PYTHONPATH=$(shell pwd) python scripts/terraform/azure/scripts/push_secrets_to_container.py -f "$(FILES)"

write-secrets-to-container-dev:
	@$(MAKE) write-secrets-to-container-file FILES=".env.dev,scripts/terraform/azure/outputs/dev.output" 

write-secrets-to-container-prod:
	@$(MAKE) write-secrets-to-container-file FILES=".env.prod,scripts/terraform/azure/outputs/prod.output"	

write-secrets-to-container-global:
	@$(MAKE) write-secrets-to-container-file FILES="scripts/terraform/azure/outputs/global.output" 

## One-shot deploy: plan, apply, then write kubeconfig
terraform-deploy-dev:
	@$(MAKE) terraform-plan-dev
	@$(MAKE) terraform-apply-dev
	@$(MAKE) terraform-output-dev
	@$(MAKE) write-output-to-env-dev
	@echo ""
	@echo "   - IMPORTANT: Update OpenAI Tokens-Per-Minute quotas in Azure Foundry:"
	@echo "   - Chat models: up to 1M TPM"
	@echo "   - Embedding models: up to 2M TPM"
	@echo "   (Terraform does not expose this setting)"
	@echo ""
	@read -p "Have you updated the OpenAI quotas? [y/N]: " CONFIRM; \
	if [ "$$CONFIRM" != "y" ] && [ "$$CONFIRM" != "Y" ]; then \
		echo "Deployment cancelled. Please update quotas and try again."; \
		exit 1; \
	fi
	@echo "Continuing with deployment..."
	@$(MAKE) build-image-dev
	@$(MAKE) push-image-dev
	@$(MAKE) kubeconfig-dev
	@$(MAKE) helm-upgrade-dev
	@$(MAKE) update-apim-backend-url ENV=dev
	@$(MAKE) terraform-plan-dev
	@$(MAKE) terraform-apply-dev
	@echo "Backend deployment complete!"


terraform-deploy-prod:
	@$(MAKE) terraform-plan-prod
	@$(MAKE) terraform-apply-prod
	@$(MAKE) terraform-output-prod
	@$(MAKE) write-output-to-env-prod
	@echo ""
	@echo "   - IMPORTANT: Update OpenAI Tokens-Per-Minute quotas in Azure Foundry:"
	@echo "   - Chat models: up to 1M TPM"
	@echo "   - Embedding models: up to 2M TPM"
	@echo "   (Terraform does not expose this setting)"
	@echo ""
	@read -p "Have you updated the OpenAI quotas? [y/N]: " CONFIRM; \
	if [ "$$CONFIRM" != "y" ] && [ "$$CONFIRM" != "Y" ]; then \
		echo "Deployment cancelled. Please update quotas and try again."; \
		exit 1; \
	fi
	@echo "Continuing with deployment..."
	@$(MAKE) build-image-prod
	@$(MAKE) push-image-prod
	@$(MAKE) kubeconfig-prod
	@$(MAKE) helm-upgrade-prod
	@$(MAKE) update-apim-backend-url ENV=prod
	@$(MAKE) terraform-plan-prod
	@$(MAKE) terraform-apply-prod
	@echo "Backend deployment complete!"
	

# ---- Helm deployment targets ----
.PHONY: helm-install
helm-install:
	@ENV=$(ENV); \
	test -f ./.env.$${ENV} || { echo "ERROR: missing .env.$${ENV} at repo root"; exit 1; }; \
	. ./.env.$${ENV}; \
	KUBECONFIG_FILE=$(TF_DIR)/outputs/$${ENV}.kubeconfig; \
	test -f "$${KUBECONFIG_FILE}" || { echo "ERROR: kubeconfig not found at $${KUBECONFIG_FILE}. Run 'make kubeconfig-$${ENV}' first."; exit 1; }; \
	IMAGE_REPO="$${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api"; \
	IMAGE_TAG="$(VERSION)-$${ENV}"; \
	echo "Installing Helm chart for environment: $${ENV}"; \
	echo "Using image: $${IMAGE_REPO}:$${IMAGE_TAG}"; \
	KUBECONFIG="$${KUBECONFIG_FILE}" helm install kioskbot-backend-$${ENV} ./scripts/helm \
		--values ./scripts/helm/values-$${ENV}.yaml \
		--set api.image.repository="$${IMAGE_REPO}" \
		--set api.image.tag="$${IMAGE_TAG}" \
		--set kafkaConsumer.image.repository="$${IMAGE_REPO}" \
		--set kafkaConsumer.image.tag="$${IMAGE_TAG}" \
		--create-namespace \
		--namespace kioskbot-$${ENV}

.PHONY: k8s-create-namespace
k8s-create-namespace:
	@ENV=$(ENV); \
	KUBECONFIG_FILE=$(TF_DIR)/outputs/$${ENV}.kubeconfig; \
	test -f "$${KUBECONFIG_FILE}" || { echo "ERROR: kubeconfig not found at $${KUBECONFIG_FILE}. Run 'make kubeconfig-$${ENV}' first."; exit 1; }; \
	echo "Creating namespace for environment: $${ENV}"; \
	KUBECONFIG="$${KUBECONFIG_FILE}" kubectl create namespace kioskbot-$${ENV}

.PHONY: k8s-create-namespace-dev
k8s-create-namespace-dev:
	@$(MAKE) k8s-create-namespace ENV=dev

.PHONY: k8s-create-namespace-prod
k8s-create-namespace-prod:
	@$(MAKE) k8s-create-namespace ENV=prod

.PHONY: k8s-create-secrets
k8s-create-secrets:
	@ENV=$(ENV); \
	test -f ./.env.$${ENV} || { echo "ERROR: missing .env.$${ENV} at repo root"; exit 1; }; \
	KUBECONFIG_FILE=$(TF_DIR)/outputs/$${ENV}.kubeconfig; \
	test -f "$${KUBECONFIG_FILE}" || { echo "ERROR: kubeconfig not found at $${KUBECONFIG_FILE}. Run 'make kubeconfig-$${ENV}' first."; exit 1; }; \
	echo "Creating secrets for environment: $${ENV}"; \
	KUBECONFIG="$${KUBECONFIG_FILE}" kubectl create secret generic kioskbot-backend-$${ENV}-secrets \
		--from-env-file=.env.$${ENV} \
		--namespace=kioskbot-$${ENV}

.PHONY: k8s-create-secrets-dev
k8s-create-secrets-dev:
	@$(MAKE) k8s-create-secrets ENV=dev

.PHONY: k8s-create-secrets-prod
k8s-create-secrets-prod:
	@$(MAKE) k8s-create-secrets ENV=prod

.PHONY: helm-install-dev
helm-install-dev:
	@$(MAKE) helm-install ENV=dev

.PHONY: helm-install-prod
helm-install-prod:
	@$(MAKE) helm-install ENV=prod

.PHONY: helm-upgrade
helm-upgrade:
	@ENV=$(ENV); \
	test -f ./.env.$${ENV} || { echo "ERROR: missing .env.$${ENV} at repo root"; exit 1; }; \
	. ./.env.$${ENV}; \
	KUBECONFIG_FILE=$(TF_DIR)/outputs/$${ENV}.kubeconfig; \
	test -f "$${KUBECONFIG_FILE}" || { echo "ERROR: kubeconfig not found at $${KUBECONFIG_FILE}. Run 'make kubeconfig-$${ENV}' first."; exit 1; }; \
	APIM_IP="$$( $(TF) -chdir=$(TF_DIR) output -json apim_public_ip_addresses 2>/dev/null | jq -r '.[0] // empty' )"; \
	if [ -z "$${APIM_IP}" ]; then \
		echo "ERROR: APIM public IP not found. Run 'make terraform-output-$${ENV}' first."; \
		exit 1; \
	fi; \
	IMAGE_REPO="$${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api"; \
	IMAGE_TAG="$(VERSION)-$${ENV}"; \
	echo "Upgrading Helm release for environment: $${ENV}"; \
	echo "Using image: $${IMAGE_REPO}:$${IMAGE_TAG}"; \
	echo "Allowing APIM IP: $${APIM_IP}/32"; \
	KUBECONFIG="$${KUBECONFIG_FILE}" helm upgrade kioskbot-backend-$${ENV} ./scripts/helm \
		--values ./scripts/helm/values-$${ENV}.yaml \
		--set api.image.repository="$${IMAGE_REPO}" \
		--set api.image.tag="$${IMAGE_TAG}" \
		--set api.service.loadBalancerSourceRanges[0]="$${APIM_IP}/32" \
		--set kafkaConsumer.image.repository="$${IMAGE_REPO}" \
		--set kafkaConsumer.image.tag="$${IMAGE_TAG}" \
		--namespace kioskbot-$${ENV} \
		--wait \
		--timeout 5m; \
	echo "Forcing rolling restart of deployments..."; \
	KUBECONFIG="$${KUBECONFIG_FILE}" kubectl rollout restart deployment/kioskbot-backend-$${ENV}-api -n kioskbot-$${ENV}; \
	KUBECONFIG="$${KUBECONFIG_FILE}" kubectl rollout restart deployment/kioskbot-backend-$${ENV}-kafka-consumer -n kioskbot-$${ENV}; \
	echo "Waiting for rollout to complete..."; \
	KUBECONFIG="$${KUBECONFIG_FILE}" kubectl rollout status deployment/kioskbot-backend-$${ENV}-api -n kioskbot-$${ENV} --timeout=5m; \
	KUBECONFIG="$${KUBECONFIG_FILE}" kubectl rollout status deployment/kioskbot-backend-$${ENV}-kafka-consumer -n kioskbot-$${ENV} --timeout=5m; \
	echo "All deployments ready!"

.PHONY: helm-upgrade-dev
helm-upgrade-dev:
	@$(MAKE) helm-upgrade ENV=dev

.PHONY: helm-upgrade-prod
helm-upgrade-prod:
	@$(MAKE) helm-upgrade ENV=prod

.PHONY: helm-uninstall
helm-uninstall:
	@ENV=$(ENV); \
	KUBECONFIG_FILE=$(TF_DIR)/outputs/$${ENV}.kubeconfig; \
	test -f "$${KUBECONFIG_FILE}" || { echo "ERROR: kubeconfig not found at $${KUBECONFIG_FILE}. Run 'make kubeconfig-$${ENV}' first."; exit 1; }; \
	echo "Uninstalling Helm release for environment: $${ENV}"; \
	KUBECONFIG="$${KUBECONFIG_FILE}" helm uninstall kioskbot-backend-$${ENV} \
		--namespace kioskbot-$${ENV}

.PHONY: helm-uninstall-dev
helm-uninstall-dev:
	@$(MAKE) helm-uninstall ENV=dev

.PHONY: helm-uninstall-prod
helm-uninstall-prod:
	@$(MAKE) helm-uninstall ENV=prod


# ---- Kubernetes Dashboard ----
.PHONY: helm-dashboard-install helm-dashboard-status helm-dashboard-port helm-dashboard-uninstall get-aks-credentials

helm-dashboard-install:
	@echo $@
	KUBECONFIG="$(KUBECONFIG)" helm upgrade --install kubernetes-dashboard kubernetes-dashboard \
	  --repo https://kubernetes.github.io/dashboard/ \
	  --namespace kubernetes-dashboard --create-namespace \
	  --version $(DASHBOARD_CHART_VERSION) \
	  --set metricsScraper.enabled=true \
	  --wait

helm-dashboard-status:
	@echo $@
	KUBECONFIG="$(KUBECONFIG)" helm status kubernetes-dashboard -n kubernetes-dashboard || true

helm-dashboard-port:
	@echo $@
	KUBECONFIG="$(KUBECONFIG)" kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 8443:443

create-dashboard-admin-service-account-and-cluster-role-binding:
	@echo "Creating dashboard-admin service account and cluster role binding..."
	@printf '%s\n' \
	  'apiVersion: v1' \
	  'kind: ServiceAccount' \
	  'metadata:' \
	  '  name: dashboard-admin' \
	  '  namespace: kubernetes-dashboard' \
	  '---' \
	  'apiVersion: rbac.authorization.k8s.io/v1' \
	  'kind: ClusterRoleBinding' \
	  'metadata:' \
	  '  name: dashboard-admin' \
	  'roleRef:' \
	  '  apiGroup: rbac.authorization.k8s.io' \
	  '  kind: ClusterRole' \
	  '  name: cluster-admin' \
	  'subjects:' \
	  '  - kind: ServiceAccount' \
	  '    name: dashboard-admin' \
	  '    namespace: kubernetes-dashboard' \
	  | kubectl apply -f -

helm-dashboard-uninstall:
	@echo $@
	KUBECONFIG="$(KUBECONFIG)" helm uninstall kubernetes-dashboard -n kubernetes-dashboard || true
	KUBECONFIG="$(KUBECONFIG)" kubectl delete ns kubernetes-dashboard --ignore-not-found=true

get-aks-credentials:
	@RG_NAME=$$($(MAKE) --no-print-directory terraform-output-var VAR=RESOURCE_GROUP_NAME 2>/dev/null) ; \
	AKS_NAME=$$($(MAKE) --no-print-directory terraform-output-var VAR=AKS_CLUSTER_NAME 2>/dev/null) ; \
	echo "az aks get-credentials --resource-group $$RG_NAME --name $$AKS_NAME --overwrite-existing" ; \
	az aks get-credentials --resource-group $$RG_NAME --name $$AKS_NAME --overwrite-existing
