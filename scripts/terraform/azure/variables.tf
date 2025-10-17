#------- Global --------

variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }
 


# ----- OpenAI --------
variable "cognitive_model_account_name" {
  type    = string
  default = null
}
variable "cognitive_model_deployment_sku_name" {
  type    = string
  default = null
}
variable "cognitive_model_account_sku_name" {
  type    = string
  default = null
}
variable "cognitive_model_deployment_name" {
  type    = string
  default = null
}
variable "cognitive_model_name" {
  type    = string
  default = null
}
variable "cognitive_model_version" {
  type    = string
  default = null
}
variable "cognitive_model_account_kind" {
  type    = string
  default = null
}

variable "cognitive_model_embedding_deployment_name" {
  type    = string
  default = null
}
variable "cognitive_model_embedding_name" {
  type    = string
  default = null
}
variable "cognitive_model_embedding_deployment_sku_name" {
  type    = string
  default = null
}
variable "cognitive_model_embedding_version" {
  type    = string
  default = null
}

# ----- AI Foundry ------

variable "aif_hub_name" {
  type    = string
  default = null
}
variable "aif_project_name" {
  type    = string
  default = null
}

# ----- Tooling paths ------
variable "pyproject_path" {
  description = "Path to pyproject.toml (optional). Defaults to repo root pyproject.toml"
  type        = string
  default     = null
}

# ----- Global tagging ------
variable "environment" { type = string }
variable "owner" {
  type    = string
  default = null
}


# ----- App Service Plan --------
variable "app_service_plan_name" {
  type    = string
  default = null
}
variable "app_service_plan_os_type" {
  type        = string
  default     = "Linux"
}
variable "app_service_plan_worker_count" {
  type        = number
  default     = 1
}

# ----- App Service --------
variable "app_service_name" {
  type    = string
  default = null
}
variable "app_service_plan_sku_name" {
  type    = string
  default = null
}
variable "app_service_os_type" {
  type    = string
  default = "Linux"
}
variable "app_service_app_settings" {
  type    = map(string)
  default = {}
}
variable "app_service_identity" {
  type    = map(string)
  default = {}
}
variable "app_service_virtual_network_subnet_id" {
  type    = string
  default = null
}
variable "app_service_connection_string" {
  type    = string
  default = null
}
variable "app_service_connection_string_name" {
  type    = string
  default = null
}
variable "app_service_connection_string_type" {
  type    = string
  default = null
}
variable "app_service_connection_string_value" {
  type    = string
  default = null
}
variable "container_registry_id" {
  type    = string
  default = null
}
variable "app_service_plan_id" {
  type    = string
  default = null
}
variable "app_name" {
  type    = string
  default = null
}
variable "container_image_tag" {
  type    = string
  default = null
}

# ----- Container Registry --------
variable "container_registry_name" {type = string}
variable "container_registry_sku" {
  type    = string
  default = null
}
variable "admin_enabled" {
  type        = bool
  default     = false
}
variable "retention_enabled" {
  type        = bool
  default     = false
}
variable "retention_days" {
  type        = number
  default     = 30
}
variable "anonymous_pull_enabled" {
  type        = bool
  default     = false
}
variable "data_endpoint_enabled" {
  type        = bool
  default     = false
}
variable "container_registry_resource_group_name" {
  description = "Optional RG name if ACR is in a different RG (e.g., global)"
  type        = string
  default     = null
}
variable "container_repository_name" { type = string }

# ----- Storage Account --------
variable "storage_account_name" {
  type    = string
  default = null
}
variable "storage_account_kind" {
  type    = string
  default = null
}
variable "storage_account_tier" {
  type    = string
  default = null
}
variable "storage_account_replication_type" {
  type    = string
  default = null
}
variable "storage_account_enable_hns" {
  type    = bool
  default = null
}
variable "storage_account_enable_blob_versioning" {
  type    = bool
  default = null
}
variable "storage_account_enable_change_feed" {
  type    = bool
  default = null
}
variable "storage_account_blob_soft_delete_days" {
  type    = number
  default = null
}
variable "storage_account_container_soft_delete_days" {
  type    = number
  default = null
}
variable "storage_account_containers" { 
  type = list(string) 
  default = [] 
}
variable "storage_account_tables"     { 
  type = list(string) 
  default = [] 
}
variable "storage_account_queues" {
  type    = list(string)
  default = []
}
variable "storage_account_enable_static_website" {
  type    = bool
  default = false
}
variable "storage_account_static_website_index" {
  type    = string
  default = "index.html"
}
variable "storage_account_static_website_error" {
  type    = string
  default = "404.html"
}
variable "storage_account_network_default_action" {
  type    = string
  default = null
}
variable "storage_account_network_ip_rules" {
  type    = list(string)
  default = []
}
variable "storage_account_network_subnet_ids" {
  type    = list(string)
  default = []
}
variable "storage_account_network_bypass" {
  type    = list(string)
  default = ["AzureServices"]
}
variable "storage_account_resource_group_name" {
  description = "Optional RG name if Storage is in a different RG (e.g., global)"
  type        = string
  default     = null
}

# ----- Search Service --------
variable "search_service_name" {
  type    = string
  default = null
}
variable "search_service_sku" {
  type    = string
  default = null
}
variable "search_service_replica_count" {
  type    = number
  default = null
}
variable "search_service_partition_count" {
  type    = number
  default = null
}
variable "search_service_hosting_mode" {
  type    = string
  default = null
}
variable "search_service_public_network_access_enabled" {
  type    = bool
  default = null
}
variable "grant_blob_reader_to_storage_account_id" {
  type    = string
  default = null
}

# ----- Key Vault --------
variable "key_vault_name" {
  type    = string
  default = null
}
variable "key_vault_tenant_id" {
  description = "Optional override for tenant ID; defaults to current azurerm client tenant."
  type        = string
  default     = null
}
variable "key_vault_sku_name" {
  type    = string
  default = null
}
variable "key_vault_soft_delete_days" {
  type    = number
  default = null
}
variable "key_vault_purge_protection_enabled" {
  type    = bool
  default = null
}
variable "key_vault_enable_rbac" {
  type    = bool
  default = null
}
variable "key_vault_public_network_access_enabled" {
  type    = bool
  default = null
}
variable "key_vault_network_default_action" {
  type    = string
  default = null
}
variable "key_vault_network_bypass" {
  type    = string
  default = null
}
variable "key_vault_network_ip_rules" {
  type    = list(string)
  default = null
}
variable "key_vault_network_subnet_ids" {
  type    = list(string)
  default = null
}
variable "key_vault_secrets" {
  type    = map(object({ value = string, content_type = string }))
  default = {}
}
variable "key_vault_rbac_role_assignments" {
  type    = list(object({ role_definition_name = string, principal_id = string }))
  default = []
}
variable "key_vault_access_policies" {
  type    = list(object({ tenant_id = string, object_id = string, key_permissions = list(string), secret_permissions = list(string), certificate_permissions = list(string), storage_permissions = list(string) }))
  default = []
}