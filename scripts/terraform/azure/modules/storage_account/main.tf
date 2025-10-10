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

  # Enable Data Lake Gen2 (optional)
  is_hns_enabled = var.storage_account_enable_hns

  # Blob-specific hardening & hygiene
  blob_properties {
    versioning_enabled   = var.storage_account_enable_blob_versioning
    change_feed_enabled  = var.storage_account_enable_change_feed

    delete_retention_policy {
      days = var.storage_account_blob_soft_delete_days
    }

    container_delete_retention_policy {
      days = var.storage_account_container_soft_delete_days
    }

    last_access_time_enabled = true
  }

  # Optional network rules (kept open by default)
  dynamic "network_rules" {
    for_each = var.storage_account_network_default_action == null ? [] : [1]
    content {
      default_action             = var.storage_account_network_default_action
      ip_rules                   = var.storage_account_network_ip_rules
      virtual_network_subnet_ids = var.storage_account_network_subnet_ids
      bypass                     = var.storage_account_network_bypass
    }
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

