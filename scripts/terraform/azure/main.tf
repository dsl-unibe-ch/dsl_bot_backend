# --- Resource group ---
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.resource_group_location
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
  resource_group_location = var.resource_group_location
  app_service_plan_name  = var.app_service_plan_name
  resource_group_name = var.resource_group_name
  app_service_plan_os_type = var.app_service_plan_os_type    
  app_service_plan_sku_name = var.app_service_plan_sku_name    
  app_service_plan_worker_count = var.app_service_plan_worker_count
}

# --- Container Registry ---
module "azurerm_container_registry" {
  source              = "./modules/container_registry"
  subscription_id     = var.subscription_id
  resource_group_location = var.resource_group_location
  resource_group_name = var.resource_group_name
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
  resource_group_location = var.resource_group_location
  resource_group_name = var.resource_group_name
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
}

# --- Search Service ---

module "azurerm_search_service" {
  source              = "./modules/search_service"
  subscription_id     = var.subscription_id
  resource_group_location = var.resource_group_location
  resource_group_name = var.resource_group_name
  search_service_name = var.search_service_name
  search_service_sku = var.search_service_sku
  search_service_replica_count = var.search_service_replica_count
  search_service_partition_count = var.search_service_partition_count
  search_service_hosting_mode = var.search_service_hosting_mode
  search_service_public_network_access_enabled = var.search_service_public_network_access_enabled
  grant_blob_reader_to_storage_account_id = var.grant_blob_reader_to_storage_account_id
}