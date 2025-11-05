#------- Global --------

variable "key_vault_tags" {
  description = "Tags map."
  type        = map(string)
  default     = {}
}
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }
variable "tenant_id" { type = string }

# ----- Key Vault -----
variable "key_vault_name" {
  description = "Key Vault name (globally unique in tenant)."
  type        = string
}

variable "key_vault_sku_name" {
  description = "Key Vault SKU: standard or premium."
  type        = string
  default     = "standard"
}

variable "key_vault_soft_delete_days" {
  description = "Soft delete retention in days (7..90)."
  type        = number
  default     = 90
}

 
