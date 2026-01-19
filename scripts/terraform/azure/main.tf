# --- Network for AKS (BYO VNet/Subnet to satisfy UniBE policy) ---
module "network_aks" {
  count                   = var.environment == "global" ? 0 : 1
  source                  = "./modules/network_aks"
  subscription_id         = var.subscription_id
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name

  tags = local.default_tags

  vnet_name               = var.aks_vnet_name
  vnet_address_space      = var.aks_vnet_address_space
  subnet_name             = var.aks_subnet_name
  subnet_address_prefix   = var.aks_subnet_address_prefix
  network_security_group_name = var.aks_network_security_group_name
  allowed_external_ips    = local.apim_public_ips
  api_destination_port    = var.aks_api_destination_port
}
# --- Resource group ---
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.resource_group_location
}

# Discover current tenant for cross-module use (e.g., Key Vault)
data "azurerm_client_config" "current" {}

locals {
  # Global has no app deployments; skip image tag resolution entirely.
  # For non-global envs: prefer explicit var, else read env-specific tag file, else empty string.
  image_tag                       = var.environment == "global" ? "" : var.image_tag_override
  tenant_id_effective             = data.azurerm_client_config.current.tenant_id
  apim_public_ips                 = var.environment == "global" ? [] : try(module.api_management[0].apim_public_ip_addresses, [])
  default_tags = {
    environment = var.environment
    project     = "kioskbot"
    owner       = var.owner
  }
}

# --- OpenAI ---

module "openai" {
  count                                        = var.environment == "global" ? 0 : 1
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
  cognitive_model_embedding_deployment_capacity = var.cognitive_model_embedding_deployment_capacity
  cognitive_model_deployment_capacity           = var.cognitive_model_deployment_capacity
  source                                        = "./modules/openai"
}

# --- Container Registry ---
module "azurerm_container_registry" {
  count                   = var.environment == "global" ? 1 : 0
  source                  = "./modules/container_registry"
  resource_group_location = azurerm_resource_group.rg.location
  container_registry_resource_group_name = var.container_registry_resource_group_name
  resource_group_name     = azurerm_resource_group.rg.name
  container_registry_name = var.container_registry_name
  container_registry_sku  = var.container_registry_sku
  container_repository_name = var.container_repository_name
  container_registry_tags = var.container_registry_tags
}

data "azurerm_container_registry" "acr" {
  count               = var.environment == "global" ? 0 : 1
  name                = var.container_registry_name
  resource_group_name = var.container_registry_resource_group_name
}

# --- Storage Account ---
module "azurerm_storage_account" {
  count                        = var.environment == "global" ? 1 : 0 #If var.environment is "global", create 1 instance, else 0
  source                       = "./modules/storage_account"
  subscription_id              = var.subscription_id
  resource_group_location      = azurerm_resource_group.rg.location
  resource_group_name          = azurerm_resource_group.rg.name
  storage_account_name         = var.storage_account_name
  storage_account_kind         = var.storage_account_kind
  storage_account_tier         = var.storage_account_tier
  storage_account_replication_type = var.storage_account_replication_type
  storage_account_containers   = var.storage_account_containers
  storage_account_tags         = var.storage_account_tags
}

data "azurerm_storage_account" "sa" {
  count               = var.environment == "global" ? 0 : 1
  name                = var.storage_account_name
  resource_group_name = var.storage_account_resource_group_name
}

# --- Search Service ---

module "azurerm_search_service" {
  count                   = var.environment == "global" ? 0 : 1
  source              = "./modules/search_service"
  subscription_id     = var.subscription_id
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  search_service_name = var.search_service_name
  search_service_sku = var.search_service_sku
  search_service_replica_count = var.search_service_replica_count
  search_service_partition_count = var.search_service_partition_count
  grant_blob_reader_to_storage_account_id = var.grant_blob_reader_to_storage_account_id
  search_index_name = var.search_index_name
  tags = local.default_tags
}

# --- AKS (Kubernetes Cluster) ---
module "kubernetes_cluster" {
  count                   = var.environment == "global" ? 0 : 1
  source                  = "./modules/kubernetes_cluster"
  subscription_id         = var.subscription_id
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name

  tags = local.default_tags

  cluster_name   = var.aks_cluster_name
  dns_prefix     = var.aks_dns_prefix
  admin_username = var.aks_admin_username
  admin_ssh_public_keys = var.aks_admin_ssh_public_keys

  default_node_pool_name          = var.aks_node_pool_name
  default_node_pool_node_count    = var.aks_node_count
  default_node_pool_vm_size       = var.aks_node_vm_size
  default_node_pool_os_disk_size_gb = var.aks_node_os_disk_size_gb
  default_node_pool_os_sku        = var.aks_node_os_sku
  vnet_subnet_id                  = module.network_aks[0].AKS_SUBNET_ID
  
  node_resource_group_name  = var.aks_node_resource_group_name

  additional_node_pools = {
    for pool_name, pool in var.aks_additional_node_pools : pool_name => merge(pool, {
      vnet_subnet_id = module.network_aks[0].AKS_SUBNET_ID # required to comply with UniBe policy
    })
  }
  
  # Grant AKS access to pull images from ACR
  acr_id = data.azurerm_container_registry.acr[0].id
}

# --- Key Vault ---
module "azurerm_key_vault" {
  count                  = var.environment == "global" ? 1 : 0
  source              = "./modules/keyvault"
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  key_vault_name = var.key_vault_name
  tenant_id = local.tenant_id_effective
  key_vault_sku_name = var.key_vault_sku_name
  key_vault_tags = var.key_vault_tags
}

# --- API Management ---
module "api_management" {
  count                   = var.environment == "global" ? 0 : 1
  source                  = "./modules/api_management"
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  
  apim_name        = var.apim_name
  apim_sku_name    = var.apim_sku_name
  publisher_name   = var.apim_publisher_name
  publisher_email  = var.apim_publisher_email
  backend_url      = var.apim_backend_url
  
  # API configuration
  api_name         = var.apim_api_name
  api_display_name = var.apim_api_display_name
  api_path         = var.apim_api_path
  api_revision     = var.apim_api_revision
  api_protocols    = var.apim_api_protocols
  
  # Rate limiting configuration per endpoint
  initialize_rate_limit_calls = var.apim_initialize_rate_limit_calls
  initialize_quota_calls      = var.apim_initialize_quota_calls
  invoke_rate_limit_calls     = var.apim_invoke_rate_limit_calls
  invoke_quota_calls          = var.apim_invoke_quota_calls
  feedback_rate_limit_calls   = var.apim_feedback_rate_limit_calls
  feedback_quota_calls        = var.apim_feedback_quota_calls
  
  subscription_required = var.apim_subscription_required
  
  tags = local.default_tags
}
