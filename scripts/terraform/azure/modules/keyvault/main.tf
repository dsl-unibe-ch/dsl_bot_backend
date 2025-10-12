

# Key Vault
resource "azurerm_key_vault" "this" {
  name                        = var.key_vault_name
  location                    = var.resource_group_location
  resource_group_name         = var.resource_group_name
  tenant_id                   = var.tenant_id
  sku_name                    = var.key_vault_sku_name            # "standard" or "premium"
  soft_delete_retention_days  = var.key_vault_soft_delete_days    # 7..90
  purge_protection_enabled    = var.key_vault_purge_protection_enabled
  rbac_authorization_enabled   = var.key_vault_enable_rbac

  public_network_access_enabled = var.key_vault_public_network_access_enabled

  dynamic "network_acls" {
    for_each = var.key_vault_network_default_action == null ? [] : [1]
    content {
      default_action             = var.key_vault_network_default_action   
      bypass                     = var.key_vault_network_bypass           
      ip_rules                   = var.key_vault_network_ip_rules
      virtual_network_subnet_ids = var.key_vault_network_subnet_ids
    }
  }

  # Optional: classic Access Policies (only when RBAC is disabled)
  dynamic "access_policy" {
    for_each = var.key_vault_enable_rbac || length(var.key_vault_access_policies) == 0 ? [] : var.key_vault_access_policies
    content {
      tenant_id = access_policy.value.tenant_id
      object_id = access_policy.value.object_id

      key_permissions         = lookup(access_policy.value, "key_permissions", [])
      secret_permissions      = lookup(access_policy.value, "secret_permissions", [])
      certificate_permissions = lookup(access_policy.value, "certificate_permissions", [])
      storage_permissions     = lookup(access_policy.value, "storage_permissions", [])
    }
  }

  tags = var.key_vault_tags
}

# Optional: seed secrets
resource "azurerm_key_vault_secret" "secrets" {
  for_each     = var.key_vault_secrets
  name         = each.key
  value        = each.value.value
  content_type = lookup(each.value, "content_type", null)
  key_vault_id = azurerm_key_vault.this.id

  # If you want "do not purge on destroy", flip to true
  depends_on = [azurerm_key_vault.this]
}

# Optional: RBAC role assignments (e.g., Secrets User/Officer) to identities (principal/object IDs)
resource "azurerm_role_assignment" "kv_rbac" {
  for_each            = { for ra in var.key_vault_rbac_role_assignments : "${ra.role_definition_name}-${ra.principal_id}" => ra }
  scope               = azurerm_key_vault.this.id
  role_definition_name = each.value.role_definition_name
  principal_id        = each.value.principal_id
}
