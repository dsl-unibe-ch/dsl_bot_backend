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

# ----- Container Registry --------
variable "container_registry_name" {type = string}
variable "container_registry_sku" {
  type    = string
  default = null
}
variable "container_registry_tags" { 
  type = map(string) 
  default = {}
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

variable "storage_account_tags" {
  description = "Tags to apply."
  type        = map(string)
  default     = {}
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

variable "key_vault_tags" {
  description = "Tags to apply."
  type        = map(string)
  default     = {}
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

variable "aks_additional_node_pools" {
  type = map(object({
    vm_size             = string
    node_count          = number
    os_disk_size_gb     = number
    os_sku              = string
    mode                = string
    auto_scaling_enabled = optional(bool)
    min_count            = optional(number)
    max_count            = optional(number)
  }))
}