
resource "azurerm_search_service" "this" {
  name                = var.search_service_name
  resource_group_name = var.resource_group_name
  location            = var.resource_group_location
  sku = var.search_service_sku
  public_network_access_enabled = true
  # Capacity
  replica_count   = var.search_service_replica_count   # 1..12 (depends on SKU)
  partition_count = var.search_service_partition_count # 1..12 (depends on SKU)

  # Enable MSI so you can assign RBAC (e.g., Storage Blob Data Reader)
  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}


resource "azurerm_role_assignment" "search_sa_blob_reader" {
  count                = var.grant_blob_reader_to_storage_account_id == null ? 0 : 1
  scope                = var.grant_blob_reader_to_storage_account_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_search_service.this.identity[0].principal_id
}