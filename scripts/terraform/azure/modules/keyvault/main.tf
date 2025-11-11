

# Key Vault
resource "azurerm_key_vault" "this" {
  name                        = var.key_vault_name
  location                    = var.resource_group_location
  resource_group_name         = var.resource_group_name
  tenant_id                   = var.tenant_id
  sku_name                    = var.key_vault_sku_name            # "standard" or "premium"
  tags = var.key_vault_tags
  purge_protection_enabled = true # When set to true, prevents the key vault from being permanently deleted. Value must be set to true to comply with the UniBE policy.
}
