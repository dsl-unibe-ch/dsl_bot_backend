#------- Global --------

variable "key_vault_tags" {
  description = "Tags map."
  type        = map(string)
  default     = {}
}
variable "subscription_id" { type = string }
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

variable "key_vault_purge_protection_enabled" {
  description = "Enable purge protection (recommended: true)."
  type        = bool
  default     = true
}

variable "key_vault_enable_rbac" {
  description = "Use RBAC instead of Access Policies."
  type        = bool
  default     = true
}

variable "key_vault_public_network_access_enabled" {
  description = "Public network access (set false if using Private Endpoints)."
  type        = bool
  default     = true
}

variable "key_vault_network_default_action" {
  description = "Key Vault network ACL default action: Allow or Deny. Set null to omit ACLs."
  type        = string
  default     = "Allow"
  validation {
    condition     = var.key_vault_network_default_action == null || contains(["Allow", "Deny"], var.key_vault_network_default_action)
    error_message = "network_default_action must be null, 'Allow', or 'Deny'."
  }
}

variable "key_vault_network_bypass" {
  description = "Bypass for Key Vault network ACLs."
  type        = string
  default     = "AzureServices"
}

variable "key_vault_network_ip_rules" {
  description = "Allowed IP CIDRs."
  type        = list(string)
  default     = []
}

variable "key_vault_network_subnet_ids" {
  description = "Allowed VNet subnet IDs."
  type        = list(string)
  default     = []
}

# Only used if enable_rbac = false
variable "key_vault_access_policies" {
  description = <<EOT
List of access policy objects when RBAC is disabled.
Each object:
{
  tenant_id            = string
  object_id            = string
  key_permissions         = list(string)
  secret_permissions      = list(string)
  certificate_permissions = list(string)
  storage_permissions     = list(string)
}
EOT
  type    = list(object({
    tenant_id            = string
    object_id            = string
    key_permissions         = optional(list(string), [])
    secret_permissions      = optional(list(string), [])
    certificate_permissions = optional(list(string), [])
    storage_permissions     = optional(list(string), [])
  }))
  default = []
}

# Seed secrets: map(name => { value = "...", content_type = optional("...") })
variable "key_vault_secrets" {
  description = "Map of initial secrets to create."
  type = map(object({
    value        = string
    content_type = optional(string)
  }))
  default = {}
}

# RBAC role assignments at KV scope
# Example: [{ role_definition_name = "Key Vault Secrets User", principal_id = "<objId>" }]
variable "key_vault_rbac_role_assignments" {
  description = "List of RBAC role assignments at the Key Vault scope."
  type = list(object({
    role_definition_name = string
    principal_id         = string
  }))
  default = []
}

 
