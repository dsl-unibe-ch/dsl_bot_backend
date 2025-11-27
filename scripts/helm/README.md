# KioskBot Backend Helm Chart

This Helm chart deploys the KioskBot backend application to Kubernetes, including Kafka, the API service, and the Kafka consumer.

## How Helm Templates Work

Helm uses **templates** to generate Kubernetes YAML files dynamically. Here's the flow:

```
Template Files + Values Files → Helm Renders → Final YAML → Kubernetes API → Running Pods
```

### The Three Components

1. **Template Files** (`helm/templates/*.yaml`)
   - Blueprints with `{{ }}` placeholders
   - Example: `{{ .Values.api.replicaCount }}` gets replaced with actual values
   - Use Helm functions like `toYaml`, `nindent`, etc.

2. **Values Files** (`helm/values-*.yaml`)
   - Configuration for each environment (dev/prod)
   - Define variables that fill in the template placeholders
   - Example: `api.replicaCount: 1` in values-dev.yaml

3. **Rendered YAML** (generated at runtime)
   - Final Kubernetes-ready YAML
   - Sent directly to Kubernetes API (not saved as files)
   - You can preview it with: `helm template kioskbot-backend-dev ./helm --values ./helm/values-dev.yaml`

### Example: How Templates are Rendered

**Template** (`templates/api-deployment.yaml`):
```yaml
spec:
  replicas: {{ .Values.api.replicaCount }}
  template:
    spec:
      containers:
      - name: api
        image: {{ .Values.api.image.repository }}:{{ .Values.api.image.tag }}
        envFrom:
        {{- toYaml .Values.api.envFrom | nindent 8 }}
```

**Values** (`values-dev.yaml`):
```yaml
api:
  replicaCount: 1
  image:
    repository: "crkbglobal002.azurecr.io/kioskbot-backend-api"
    tag: "0.1.0-dev"
  envFrom:
    - secretRef:
        name: kioskbot-backend-dev-secrets
```

**Rendered Output** (what Kubernetes receives):
```yaml
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: api
        image: crkbglobal002.azurecr.io/kioskbot-backend-api:0.1.0-dev
        envFrom:
        - secretRef:
            name: kioskbot-backend-dev-secrets
```

### Common Helm Template Functions

- `{{ .Values.path.to.value }}` - Access values from values.yaml
- `{{ .Chart.Name }}` - Chart name from Chart.yaml
- `{{ .Chart.Version }}` - Chart version
- `{{- toYaml .Values.object | nindent 8 }}` - Convert object to YAML with 8-space indentation
- `{{ .Values.var | quote }}` - Add quotes around a value
- `{{- if .Values.condition }}` - Conditional rendering

### Preview Rendered YAML

To see what Helm will generate before deploying:

```bash
# Preview all templates
helm template kioskbot-backend-dev ./helm \
  --values ./helm/values-dev.yaml \
  --set api.image.repository="crkbglobal002.azurecr.io/kioskbot-backend-api" \
  --set api.image.tag="0.1.0-dev" \
  --set kafkaConsumer.image.repository="crkbglobal002.azurecr.io/kioskbot-backend-api" \
  --set kafkaConsumer.image.tag="0.1.0-dev"

# Preview specific template
helm template kioskbot-backend-dev ./helm \
  --values ./helm/values-dev.yaml \
  --show-only templates/api-deployment.yaml
```

## Prerequisites

- Kubernetes cluster (AKS or other)
- `kubectl` configured with access to your cluster
- `helm` CLI installed
- Docker images built and pushed to Azure Container Registry
- `.env.dev` or `.env.prod` files with your environment variables

### For Team Members (First Time Setup)

If you're setting this up for the first time:

1. **Clone the repository** (you already have the Helm files)

2. **Get environment files** from your secure storage:
   - `.env.dev`
   - `.env.prod`
   
   > ⚠️ Never commit these files to Git!

3. **Generate kubeconfig** from Terraform:
   ```bash
   make kubeconfig-dev
   ```
   This creates `scripts/terraform/azure/outputs/dev.kubeconfig`

4. **Create Kubernetes secrets** (see section below)

5. **Deploy** using the commands in this README

All Helm chart files are already in the repository under `helm/` directory.

## Quick Start

### 1. Create Kubernetes Secrets

Before deploying, create a Kubernetes secret from your environment file:

**For Dev:**
```bash
kubectl create namespace kioskbot-dev
kubectl create secret generic kioskbot-backend-dev-secrets \
  --from-env-file=.env.dev \
  --namespace=kioskbot-dev
```

**For Prod:**
```bash
kubectl create namespace kioskbot-prod
kubectl create secret generic kioskbot-backend-prod-secrets \
  --from-env-file=.env.prod \
  --namespace=kioskbot-prod
```

### 2. Deploy with Helm

**Using Makefile (Recommended):**
```bash
# Dev environment
make helm-install-dev

# Prod environment
make helm-install-prod
```

**Manual Helm commands (equivalent to `make helm-install-dev`):**
```bash
# Load environment variables
source .env.dev

# Install
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
helm install kioskbot-backend-dev ./helm \
  --values ./helm/values-dev.yaml \
  --set api.image.repository="${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api" \
  --set api.image.tag="$(grep '^version' pyproject.toml | head -1 | cut -d '\"' -f2)-dev" \
  --set kafkaConsumer.image.repository="${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER}/kioskbot-backend-api" \
  --set kafkaConsumer.image.tag="$(grep '^version' pyproject.toml | head -1 | cut -d '\"' -f2)-dev" \
  --create-namespace \
  --namespace kioskbot-dev
```

> **Note:** The Makefile commands are recommended as they handle all environment setup automatically.

## Updating the Deployment

### Deploying New Versions

**When you want to deploy a new version of your application:**

1. **Update the application version in `pyproject.toml`:**
   ```toml
   version = "0.2.0"  # Increment from 0.1.0
   ```

2. **(Optional) Update chart metadata in `helm/Chart.yaml`:**
   - **`appVersion`**: Update to match `pyproject.toml` for documentation purposes (e.g., `"0.2.0"`)
   - **`version`**: Only increment when you modify the Helm chart templates themselves (e.g., adding new deployments, changing resource limits in templates), not for application version updates
   
   Example:
   ```yaml
   apiVersion: v2
   name: kioskbot-backend
   description: A Helm chart for KioskBot Backend Application
   type: application
   version: 0.1.0        # Chart version - increment only for template changes
   appVersion: "0.2.0"   # Application version - sync with pyproject.toml
   ```

3. **Build and push the new Docker image:**
   ```bash
   make build-image-dev
   make push-image-dev
   ```

4. **Upgrade the Helm release (or re-deploy the pods with your latest modifications):**
   ```bash
   make helm-upgrade-dev
   ```

The Makefile automatically reads the version from `pyproject.toml` and sets the image tag to `{VERSION}-{ENV}` (e.g., `0.2.0-dev`).

**What gets updated:**
- Both `api` and `kafka-consumer` use the same image, so both get updated together
- Kafka uses the official Apache Kafka image and won't change unless you modify `values-dev.yaml`

### Updating Only Specific Components

**To update just Kafka version:**
```bash
# Edit helm/values-dev.yaml
kafka:
  image:
    tag: "4.2.0"  # Change from 4.1.0

# Apply the change
make helm-upgrade-dev
```

**To update configuration (resources, replicas, etc.):**
```bash
# Edit helm/values-dev.yaml
api:
  replicaCount: 3  # Scale from 1 to 3

# Apply the change
make helm-upgrade-dev
```

### Rolling Back a Deployment

If a new version has issues, you can roll back:

**1. View release history:**
```bash
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  helm history kioskbot-backend-dev -n kioskbot-dev
```

This shows all revisions with their status:
```
REVISION  STATUS      DESCRIPTION
1         superseded  Install complete
2         superseded  Upgrade complete
3         deployed    Upgrade complete
```

**2. Roll back to previous version (revision 2):**
```bash
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  helm rollback kioskbot-backend-dev -n kioskbot-dev
```

**3. Roll back to specific revision number:**
```bash
# Roll back to revision 2 specifically
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  helm rollback kioskbot-backend-dev 2 -n kioskbot-dev
```

**For production environment:**
```bash
# View history
KUBECONFIG=scripts/terraform/azure/outputs/prod.kubeconfig \
  helm history kioskbot-backend-prod -n kioskbot-prod

# Rollback
KUBECONFIG=scripts/terraform/azure/outputs/prod.kubeconfig \
  helm rollback kioskbot-backend-prod -n kioskbot-prod
```

### Upgrade vs Install

- **`helm install`** - Deploy for the first time (use `make helm-install-dev`)
- **`helm upgrade`** - Update existing deployment (use `make helm-upgrade-dev`)
- **`helm rollback`** - Revert to a previous version

## Uninstalling

**What happens when you uninstall:**
- Deletes all application resources (deployments, services, pods) in the namespace
- **Keeps** the AKS cluster running
- **Keeps** the namespace `kioskbot-dev` or `kioskbot-prod`
- **Keeps** the Kubernetes Secret (you need to delete it manually if needed)
- **Does NOT affect** other namespaces or system components

**Uninstall the Helm release:**
```bash
# Dev
make helm-uninstall-dev

# Prod
make helm-uninstall-prod
```

**To completely clean up (optional):**
```bash
# Delete the secret too
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl delete secret kioskbot-backend-dev-secrets -n kioskbot-dev

# Delete the namespace (removes ALL resources in kioskbot-dev namespace)
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl delete namespace kioskbot-dev
```

> ⚠️ **Warning:** Deleting the namespace removes ALL resources within it, including any resources deployed by other applications if they used the same namespace. Resources in other namespaces (like `kioskbot-prod` or `kube-system`) are not affected.

> **Note:** To destroy the AKS cluster itself, use `make terraform-destroy-dev`

## Understanding Namespaces

**Kubernetes Namespaces** provide isolation within your AKS cluster:

- **`kioskbot-dev`** - Development environment resources
- **`kioskbot-prod`** - Production environment resources  
- **`kube-system`** - Kubernetes system components (DNS, metrics, etc.)

Both `kioskbot-dev` and `kioskbot-prod` run on the **same AKS cluster** and **same nodes**, but:
- Resources are isolated (separate networks, secrets, services)
- `kioskbot-dev-kafka:9092` is different from `kioskbot-prod-kafka:9092`
- Deleting one namespace doesn't affect the other

**Terraform Workspaces vs K8s Namespaces:**
- **Terraform workspaces** (`dev`, `prod`, `global`) = Separate infrastructure state (could be different clusters)
- **Kubernetes namespaces** = Virtual partitions within a single cluster
- They're unrelated concepts that happen to share similar naming!

## Architecture

### Components

1. **Kafka** - Message broker for event streaming
2. **Backend API** - FastAPI application serving HTTP requests
3. **Kafka Consumer** - Python script consuming Kafka messages and processing them

### Services

- `kioskbot-backend-{env}-kafka:9092` - Kafka internal service
- `kioskbot-backend-{env}-api:8000` - Backend API service (LoadBalancer)

### Key Differences from Docker Compose

The Helm chart automatically handles K8s-specific configurations:

- **Kafka Controller Quorum Voters**: Uses `localhost:29093` instead of `kafka:29093`
- **Health Checks**: Uses TCP socket checks instead of bash commands
- **Service Discovery**: Uses K8s service names for inter-pod communication
- **KAFKA_BOOTSTRAP_SERVERS**: Set to service name (e.g., `kioskbot-backend-dev-kafka:9092`)

## Configuration

### Values Files

- `values-dev.yaml` - Development environment configuration
- `values-prod.yaml` - Production environment configuration

### Key Configuration Options

**Resource Limits:**
```yaml
api:
  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
    requests:
      cpu: 500m
      memory: 512Mi
```

**Replica Count:**
```yaml
api:
  replicaCount: 2  # Number of API pods (ignored if autoscaling is enabled)
  
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
```

> **Note:** When `autoscaling.enabled: true`, the `replicaCount` field is ignored and HPA controls the number of replicas based on CPU/memory usage.

**Image Pull Secrets (for private registries):**
```yaml
api:
  imagePullSecrets:
    - name: acr-secret
```

## Environment Variables

All environment variables are loaded from Kubernetes Secrets via `envFrom`:

```yaml
envFrom:
  - secretRef:
      name: kioskbot-backend-dev-secrets
```

The following variables are explicitly set by the Helm chart:
- `ENV` - Environment name (dev/prod)
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka service address
- `PYTHONPATH` - Python path (for consumer only)

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n kioskbot-dev
```

### View Logs
```bash
# API logs
kubectl logs -n kioskbot-dev -l app.kubernetes.io/component=api

# Kafka logs
kubectl logs -n kioskbot-dev -l app.kubernetes.io/component=kafka

# Consumer logs
kubectl logs -n kioskbot-dev -l app.kubernetes.io/component=kafka-consumer
```

### Check Services
```bash
kubectl get svc -n kioskbot-dev
```

### Check Autoscaling Status

**View Horizontal Pod Autoscaler (HPA) status:**
```bash
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl get hpa -n kioskbot-dev
```

This shows current CPU/memory usage and replica count:
```
NAME                       TARGETS                               MINPODS   MAXPODS   REPLICAS
kioskbot-backend-dev-api   cpu: 45%/70%, memory: 22%/80%        1         3         1
```

**View detailed HPA information:**
```bash
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl describe hpa kioskbot-backend-dev-api -n kioskbot-dev
```

> **Note:** Metrics may show `<unknown>` for the first 1-2 minutes after deployment while the metrics-server collects data.

### Update Secrets
```bash
# Delete old secret
kubectl delete secret kioskbot-backend-dev-secrets -n kioskbot-dev

# Create new secret
kubectl create secret generic kioskbot-backend-dev-secrets \
  --from-env-file=.env.dev \
  --namespace=kioskbot-dev

# Restart deployments to pick up new secrets
kubectl rollout restart deployment -n kioskbot-dev
```

### View Secrets

**List all secrets in namespace:**
```bash
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl get secrets -n kioskbot-dev
```

**View secret details (base64 encoded):**
```bash
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl get secret kioskbot-backend-dev-secrets -n kioskbot-dev -o yaml
```

**Decode and view actual secret values:**
```bash
# All secrets decoded
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl get secret kioskbot-backend-dev-secrets -n kioskbot-dev -o json | \
  jq -r '.data | to_entries[] | "\(.key)=\(.value | @base64d)"'

# Single secret value
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl get secret kioskbot-backend-dev-secrets -n kioskbot-dev -o jsonpath='{.data.AZURE_OPENAI_API_KEY}' | base64 -d

# Pretty print all secrets
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig \
  kubectl get secret kioskbot-backend-dev-secrets -n kioskbot-dev -o json | \
  jq -r '.data | to_entries[] | "\(.key)=\(.value | @base64d)"' | sort
```

**For production environment:**
```bash
# List secrets
KUBECONFIG=scripts/terraform/azure/outputs/prod.kubeconfig \
  kubectl get secrets -n kioskbot-prod

# View decoded values
KUBECONFIG=scripts/terraform/azure/outputs/prod.kubeconfig \
  kubectl get secret kioskbot-backend-prod-secrets -n kioskbot-prod -o json | \
  jq -r '.data | to_entries[] | "\(.key)=\(.value | @base64d)"'
```

> ⚠️ **Security Warning:** Secret values are sensitive! Only run these commands in secure environments and don't share the output.

## Migration from Kompose

The old workflow with manual manifest editing is now deprecated:

**Old Way (deprecated):**
```bash
make kompose-convert-dev  # Generated manifests
# Manually edit 3+ files
make k8s-apply-dev
```

**New Way:**
```bash
make helm-install-dev # wait a few minutes for the pods to be actually ready and running
```

All the K8s-specific configurations are now handled automatically by Helm templates.

## Others

To get the public IP address of Azure Load Balancer:
```bash
KUBECONFIG=scripts/terraform/azure/outputs/dev.kubeconfig kubectl get svc -n kioskbot-dev
```

This will show all services. Look for the `kioskbot-backend-dev-api` service - the `EXTERNAL-IP` column shows the public IP
