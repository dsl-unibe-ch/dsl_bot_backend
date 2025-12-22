
output "AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY" {
  value     = azurerm_search_service.this.primary_key
  sensitive = true
}


output "AZURE_SEARCH_ENDPOINT" {
  value     = "https://${azurerm_search_service.this.name}.search.windows.net"
  sensitive = false
}


output "AZURE_SEARCH_INDEX_NAME" {
  value = var.search_index_name
}