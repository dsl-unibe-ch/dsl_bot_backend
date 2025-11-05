resource "azurerm_storage_account" "this" {
  name                            = var.storage_account_name
  resource_group_name             = var.resource_group_name
  location                        = var.resource_group_location
  account_kind                    = var.storage_account_kind
  account_tier                    = var.storage_account_tier
  account_replication_type        = var.storage_account_replication_type
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  cross_tenant_replication_enabled = false
  shared_access_key_enabled        = true


  # Blob-specific hardening & hygiene
  blob_properties {
    last_access_time_enabled = true
  }
  tags = var.storage_account_tags
}


# Blob containers (optional)
resource "azurerm_storage_container" "containers" {
  for_each              = toset(var.storage_account_containers)
  name                  = each.value
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

# Tables (optional)
resource "azurerm_storage_table" "tables" {
  for_each             = toset(var.storage_account_tables)
  name                 = each.value
  storage_account_name = azurerm_storage_account.this.name
}

