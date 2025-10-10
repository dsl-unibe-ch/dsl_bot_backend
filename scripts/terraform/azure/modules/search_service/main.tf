
resource "azurerm_search_service" "this" {
  name                = var.search_service_name
  resource_group_name = var.resource_group_name
  location            = var.resource_group_location

  # SKU options include: free, basic, standard, standard2, standard3,
  # storage_optimized_l1, storage_optimized_l2
  sku = var.search_service_sku

  # Capacity
  replica_count   = var.search_service_replica_count   # 1..12 (depends on SKU)
  partition_count = var.search_service_partition_count # 1..12 (depends on SKU)

  # Single or HighDensity (HD only for some SKUs; default "default")
  hosting_mode = var.search_service_hosting_mode

  # Lock down public access if you plan to use Private Endpoints
  public_network_access_enabled = var.search_service_public_network_access_enabled

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

