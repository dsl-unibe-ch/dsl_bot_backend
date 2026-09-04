variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }

variable "cluster_name" { type = string }
variable "dns_prefix" { type = string }

variable "admin_username" { type = string }
variable "admin_ssh_public_keys" { type = list(string) }

variable "default_node_pool_name" { type = string }
variable "default_node_pool_node_count" { type = number }
variable "default_node_pool_vm_size" { type = string }
variable "default_node_pool_os_disk_size_gb" { type = number }
variable "default_node_pool_os_sku" { type = string }

# Optional: bring your own subnet to satisfy policies
variable "vnet_subnet_id" {
  type    = string
  default = null
}

# Optional: name of the managed resource group AKS uses for infra
variable "node_resource_group_name" {
  type    = string
  default = null
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "additional_node_pools" {
  type = map(object({
    vm_size            = string
    node_count         = number
    os_disk_size_gb    = number
    os_sku             = string
    mode               = string
    vnet_subnet_id     = string # required to comply with UniBe policy
    auto_scaling_enabled = optional(bool)
    min_count           = optional(number)
    max_count           = optional(number)
  }))
}

variable "acr_id" {
  type        = string
  description = "Azure Container Registry ID for granting AcrPull permission"
  default     = null
}

variable "private_cluster_enabled" {
  description = "Disable the public AKS API server endpoint (required by org policy for Corp landing zones)."
  type        = bool
  default     = true
}

variable "private_dns_zone_id" {
  description = "Private DNS zone for the AKS API server. 'System' lets Azure manage its own privatelink.<region>.azmk8s.io zone."
  type        = string
  default     = "System"
}
