

# Key Vault
resource "azurerm_key_vault" "this" {
  name                        = var.key_vault_name
  location                    = var.resource_group_location
  resource_group_name         = var.resource_group_name
  tenant_id                   = var.tenant_id
  sku_name                    = var.key_vault_sku_name            # "standard" or "premium"
  soft_delete_retention_days  = var.key_vault_soft_delete_days    # 7..90


  tags = var.key_vault_tags
}
