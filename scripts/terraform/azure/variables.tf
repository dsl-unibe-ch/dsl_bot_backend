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

variable "container_registry_resource_group_name" {
  type    = string
  default = null
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

variable "storage_account_resource_group_name" {
  type    = string
  default = null
}

variable "storage_account_containers" { 
  type = list(string) 
  default = [] 
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

variable "grant_blob_reader_to_storage_account_id" {
  type    = string
  default = null
}

variable "search_index_name" {
  description = "Optional: name of an existing index to reference or propagate to modules."
  type        = string
  default     = null
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

# ----- AKS (Kubernetes Cluster) -----

variable "aks_cluster_name" {
  type    = string
  default = null
}
variable "aks_dns_prefix" {
  type    = string
  default = null
}
variable "aks_admin_username" {
  type    = string
  default = "azureuser"
}
variable "aks_admin_ssh_public_keys" {
  type    = list(string)
  default = []
}
variable "aks_node_pool_name" {
  type    = string
  default = "systempool"
}
variable "aks_node_count" {
  type    = number
  default = 1
}
variable "aks_node_vm_size" {
  type    = string
  default = null
}
variable "aks_node_os_disk_size_gb" {
  type    = number
  default = 128
}
variable "aks_node_os_sku" {
  type    = string
  default = "Ubuntu"
}
variable "aks_configure_network_profile" {
  type    = bool
  default = false
}
variable "aks_network_plugin" {
  type    = string
  default = "kubenet"
}
variable "aks_version" {
  type    = string
  default = null
}

variable "aks_node_resource_group_name" {
  description = "Custom name for the AKS managed resource group (node resource group)."
  type        = string
  default     = null
}

# AKS Network (bring-your-own subnet)
variable "aks_vnet_name" {
  type    = string
  default = null
}
variable "aks_vnet_address_space" {
  type    = list(string)
  default = []
}
variable "aks_subnet_name" {
  type    = string
  default = null
}
variable "aks_subnet_address_prefix" {
  type    = string
  default = null
}
variable "aks_network_security_group_name" {
  type    = string
  default = null
}