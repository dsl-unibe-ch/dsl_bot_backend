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
  description = "Replication type."
  type        = string
  default     = "LRS"
}

variable "storage_account_containers" {
  description = "List of blob containers to create."
  type        = list(string)
  default     = []
}
 
