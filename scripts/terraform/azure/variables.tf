#------- Global --------

variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }
 


# ----- OpenAI --------
variable "cognitive_model_account_name" { type = string }
variable "cognitive_model_deployment_sku_name" { type = string }
variable "cognitive_model_account_sku_name" { type = string }
variable "cognitive_model_deployment_name" { type = string }
variable "cognitive_model_name" { type = string }
variable "cognitive_model_version" { type = string }
variable "cognitive_model_account_kind" { type = string }

variable "cognitive_model_embedding_deployment_name" { type = string }
variable "cognitive_model_embedding_name" { type = string }
variable "cognitive_model_embedding_deployment_sku_name" { type = string }
variable "cognitive_model_embedding_version" { type = string }

# ----- AI Foundry ------

variable "aif_hub_name" { type = string }
variable "aif_project_name" { type = string }

# ----- Tooling paths ------
variable "pyproject_path" {
  description = "Path to pyproject.toml (optional). Defaults to repo root pyproject.toml"
  type        = string
  default     = null
}


# ----- App Service Plan --------
variable "app_service_plan_name" {type = string}
variable "app_service_plan_os_type" {
  type        = string
  default     = "Linux"
}
variable "app_service_plan_worker_count" {
  type        = number
  default     = 1
}

# ----- App Service --------
variable "app_service_name" {type = string}
variable "app_service_plan_sku_name" {type = string}
variable "app_service_os_type" {type = string}
variable "app_service_app_settings" {type = map(string)}
variable "app_service_tags" {type = map(string)}
variable "app_service_identity" {type = map(string)}
variable "app_service_virtual_network_subnet_id" {type = string}
variable "app_service_connection_string" {type = string}
variable "app_service_connection_string_name" {type = string}
variable "app_service_connection_string_type" {type = string}
variable "app_service_connection_string_value" {type = string}
variable "container_registry_id" {type = string}
variable "app_service_plan_id" {type = string}
variable "app_name" {type = string}
variable "container_image_tag" {type = string}
variable "container_repository" {type = string}

# ----- Container Registry --------
variable "container_registry_name" {type = string}
variable "container_registry_sku" {type = string}
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
variable "container_repository_name" { type = string }

# ----- Storage Account --------
variable "storage_account_name" { type = string }
variable "storage_account_kind" { type = string }
variable "storage_account_tier" { type = string }
variable "storage_account_replication_type" { type = string }
variable "storage_account_enable_hns" { type = bool }
variable "storage_account_enable_blob_versioning" { type = bool }
variable "storage_account_enable_change_feed" { type = bool }
variable "storage_account_blob_soft_delete_days" { type = number }
variable "storage_account_container_soft_delete_days" { type = number }
variable "storage_account_containers" { 
  type = list(string) 
  default = [] 
}
variable "storage_account_tables"     { 
  type = list(string) 
  default = [] 
}

# ----- Search Service --------
variable "search_service_name" { type = string }
variable "search_service_sku" { type = string }
variable "search_service_replica_count" { type = number }
variable "search_service_partition_count" { type = number }
variable "search_service_hosting_mode" { type = string }
variable "search_service_public_network_access_enabled" { type = bool }
variable "grant_blob_reader_to_storage_account_id" { type = string }

# ----- Key Vault --------
variable "key_vault_name" { type = string }
variable "key_vault_tenant_id" { type = string }
variable "key_vault_sku_name" { type = string }
variable "key_vault_soft_delete_days" { type = number }
variable "key_vault_purge_protection_enabled" { type = bool }
variable "key_vault_enable_rbac" { type = bool }
variable "key_vault_public_network_access_enabled" { type = bool }
variable "key_vault_network_default_action" { type = string }
variable "key_vault_network_bypass" { type = string }
variable "key_vault_network_ip_rules" { type = list(string) }
variable "key_vault_network_subnet_ids" { type = list(string) }
variable "key_vault_secrets" { type = map(object({ value = string, content_type = string })) }
variable "key_vault_rbac_role_assignments" { type = list(object({ role_definition_name = string, principal_id = string })) }
variable "key_vault_tags" { type = map(string) }
variable "key_vault_access_policies" { type = list(object({ tenant_id = string, object_id = string, key_permissions = list(string), secret_permissions = list(string), certificate_permissions = list(string), storage_permissions = list(string) })) }