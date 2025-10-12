#------- Global --------

variable "storage_account_tags" {
  description = "Tags to apply."
  type        = map(string)
  default     = {}
}
variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }


# ----- Storage Account --------
variable "storage_account_name" {
  description = "Storage account name (3-24 chars, lowercase letters & numbers only)."
  type        = string
}

variable "storage_account_kind" {
  description = "Storage account kind."
  type        = string
  default     = "StorageV2"
}

variable "storage_account_tier" {
  description = "Performance tier."
  type        = string
  default     = "Standard"
}

variable "storage_account_replication_type" {
  description = "Replication (LRS/ZRS/GZRS/RAGRS/etc.)."
  type        = string
  default     = "LRS"
}

variable "storage_account_enable_hns" {
  description = "Enable hierarchical namespace (Data Lake Gen2)."
  type        = bool
  default     = false
}

variable "storage_account_enable_blob_versioning" {
  description = "Enable blob versioning."
  type        = bool
  default     = true
}

variable "storage_account_enable_change_feed" {
  description = "Enable blob change feed."
  type        = bool
  default     = false
}

variable "storage_account_blob_soft_delete_days" {
  description = "Days to retain soft-deleted blobs (1-365)."
  type        = number
  default     = 7
}

variable "storage_account_container_soft_delete_days" {
  description = "Days to retain soft-deleted containers (1-365)."
  type        = number
  default     = 7
}

variable "storage_account_enable_static_website" {
  description = "Enable static website on the storage account."
  type        = bool
  default     = false
}

variable "storage_account_static_website_index" {
  description = "Index document for static website."
  type        = string
  default     = "index.html"
}

variable "storage_account_static_website_error" {
  description = "404 document for static website."
  type        = string
  default     = "404.html"
}

variable "storage_account_containers" {
  description = "List of blob containers to create."
  type        = list(string)
  default     = []
}

variable "storage_account_tables" {
  description = "List of tables to create."
  type        = list(string)
  default     = []
}

variable "storage_account_queues" {
  description = "List of storage queues to create."
  type        = list(string)
  default     = []
}

variable "storage_account_network_default_action" {
  description = "Default network action: Allow or Deny. Set null to omit rules."
  type        = string
  default     = "Allow"
  validation {
    condition     = var.storage_account_network_default_action == null || contains(["Allow", "Deny"], var.storage_account_network_default_action)
    error_message = "network_default_action must be null, 'Allow', or 'Deny'."
  }
}

variable "storage_account_network_ip_rules" {
  description = "IP CIDR rules when using network rules."
  type        = list(string)
  default     = []
}

variable "storage_account_network_subnet_ids" {
  description = "Subnet IDs allowed to access (Service Endpoints/Private Endpoints as applicable)."
  type        = list(string)
  default     = []
}

variable "storage_account_network_bypass" {
  description = "Services to bypass network rules."
  type        = list(string)
  default     = ["AzureServices"]
}

 
