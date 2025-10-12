# --- Resource group ---
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.resource_group_location
}

# Discover current tenant for cross-module use (e.g., Key Vault)
data "azurerm_client_config" "current" {}

#---- version from pyproject ------
data "external" "pyproject" {
  program = ["bash", "${path.module}/scripts/read_pyproject_version.sh"]

  query = {
    # if not provided, default to repo root `pyproject.toml`
    path   = var.pyproject_path != null ? var.pyproject_path : "${path.root}/pyproject.toml"
    prefix = "" 
  }
}

locals {
  image_tag                           = try(data.external.pyproject.result.image_tag, null)
  container_repository_effective      = coalesce(var.container_repository, var.container_repository_name, null)
  tenant_id_effective                 = coalesce(var.key_vault_tenant_id, data.azurerm_client_config.current.tenant_id)
  default_tags = {
    environment = var.environment
    project     = "kioskbot"
    owner       = var.owner
  }
}

# --- OpenAI ---

module "openai" {
  subscription_id                               = var.subscription_id
  resource_group_location                       = azurerm_resource_group.rg.location
  resource_group_name                           = azurerm_resource_group.rg.name
  cognitive_model_account_kind                  = var.cognitive_model_account_kind
  cognitive_model_account_name                  = var.cognitive_model_account_name
  cognitive_model_deployment_sku_name           = var.cognitive_model_deployment_sku_name
  cognitive_model_account_sku_name              = var.cognitive_model_account_sku_name
  cognitive_model_deployment_name               = var.cognitive_model_deployment_name
  cognitive_model_name                          = var.cognitive_model_name
  cognitive_model_version                       = var.cognitive_model_version
  cognitive_model_embedding_deployment_name     = var.cognitive_model_embedding_deployment_name
  cognitive_model_embedding_name                = var.cognitive_model_embedding_name
  cognitive_model_embedding_version             = var.cognitive_model_embedding_version
  cognitive_model_embedding_deployment_sku_name = var.cognitive_model_embedding_deployment_sku_name
  aif_hub_name                                  = var.aif_hub_name
  aif_project_name                              = var.aif_project_name
  source                                        = "./modules/openai"
}

# --- App Service Plan ---
module "azurerm_service_plan" {
  source              = "./modules/app_service_plan"
  subscription_id     = var.subscription_id
  resource_group_location = azurerm_resource_group.rg.location
  app_service_plan_name  = var.app_service_plan_name
  resource_group_name = azurerm_resource_group.rg.name
  app_service_plan_os_type = var.app_service_plan_os_type    
  app_service_plan_sku_name = var.app_service_plan_sku_name    
  app_service_plan_worker_count = var.app_service_plan_worker_count
}


# --- Container Registry ---
module "azurerm_container_registry" {
  source              = "./modules/container_registry"
  subscription_id     = var.subscription_id
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  container_registry_name = var.container_registry_name
  container_registry_sku = var.container_registry_sku
  admin_enabled = var.admin_enabled
  retention_enabled = var.retention_enabled
  retention_days = var.retention_days
  anonymous_pull_enabled = var.anonymous_pull_enabled
  data_endpoint_enabled = var.data_endpoint_enabled
}

# --- Storage Account ---
module "azurerm_storage_account" {
  source              = "./modules/storage_account"
  subscription_id     = var.subscription_id
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  storage_account_name = var.storage_account_name
  storage_account_kind = var.storage_account_kind
  storage_account_tier = var.storage_account_tier
  storage_account_replication_type = var.storage_account_replication_type
  storage_account_enable_hns = var.storage_account_enable_hns
  storage_account_enable_blob_versioning = var.storage_account_enable_blob_versioning
  storage_account_enable_change_feed = var.storage_account_enable_change_feed
  storage_account_blob_soft_delete_days = var.storage_account_blob_soft_delete_days
  storage_account_container_soft_delete_days = var.storage_account_container_soft_delete_days
  storage_account_containers = var.storage_account_containers
  storage_account_tables     = var.storage_account_tables
  storage_account_tags       = local.default_tags
}

# --- Search Service ---

module "azurerm_search_service" {
  source              = "./modules/search_service"
  subscription_id     = var.subscription_id
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  search_service_name = var.search_service_name
  search_service_sku = var.search_service_sku
  search_service_replica_count = var.search_service_replica_count
  search_service_partition_count = var.search_service_partition_count
  search_service_hosting_mode = var.search_service_hosting_mode
  search_service_public_network_access_enabled = var.search_service_public_network_access_enabled
  grant_blob_reader_to_storage_account_id = var.grant_blob_reader_to_storage_account_id
  tags = local.default_tags
}

# --- Key Vault ---
module "azurerm_key_vault" {
  source              = "./modules/keyvault"
  subscription_id     = var.subscription_id
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  key_vault_name = var.key_vault_name
  tenant_id = local.tenant_id_effective
  key_vault_sku_name = var.key_vault_sku_name
  key_vault_soft_delete_days = var.key_vault_soft_delete_days
  key_vault_purge_protection_enabled = var.key_vault_purge_protection_enabled
  key_vault_enable_rbac = var.key_vault_enable_rbac
  key_vault_public_network_access_enabled = var.key_vault_public_network_access_enabled
  key_vault_network_default_action = var.key_vault_network_default_action
  key_vault_network_bypass = var.key_vault_network_bypass
  key_vault_network_ip_rules = var.key_vault_network_ip_rules
  key_vault_network_subnet_ids = var.key_vault_network_subnet_ids
  key_vault_access_policies = var.key_vault_access_policies
  key_vault_secrets = var.key_vault_secrets
  key_vault_rbac_role_assignments = var.key_vault_rbac_role_assignments
  key_vault_tags = local.default_tags
}

# --- check if <repo>:<tag> exists in ACR ---
data "external" "acr_image_exists" {
  program = ["bash", "${path.module}/scripts/check_acr_image.sh"]
  query = {
    registry   = var.container_registry_name
    repository = local.container_repository_effective
    tag        = local.image_tag
  }
}

locals {
  image_exists = try(data.external.acr_image_exists.result.exists, "false") == "true"
}

# --- App Service ---
module "azurerm_app_service" {
  count                  = local.image_exists ? 1 : 0
  source              = "./modules/app_service"
  container_registry_id = var.container_registry_id
  app_service_plan_name = var.app_service_plan_name
  app_service_plan_id = var.app_service_plan_id
  app_service_plan_sku_name = module.azurerm_service_plan.AZURE_APP_SERVICE_PLAN_SKU
  resource_group_name = azurerm_resource_group.rg.name
  resource_group_location = azurerm_resource_group.rg.location
  container_image_tag = coalesce(var.container_image_tag, local.image_tag)
  app_name = var.app_name
  subscription_id = var.subscription_id
  container_registry_name = var.container_registry_name
  container_repository = local.container_repository_effective
  container_registry_login_server = module.azurerm_container_registry.AZURE_CONTAINER_REGISTRY_LOGIN_SERVER
}

