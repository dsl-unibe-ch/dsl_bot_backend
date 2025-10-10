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


# ----- App Service Plan --------
variable "app_service_plan_name" {type = string}
variable "app_service_plan_sku_name" {type = string}
variable "app_service_plan_os_type" {
  type        = string
  default     = "Linux"
}
variable "app_service_plan_worker_count" {
  type        = number
  default     = 1
}

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
