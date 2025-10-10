output "AZURE_SEARCH_SERVICE_ID" {
  value = azurerm_search_service.this.id
}

output "AZURE_SEARCH_SERVICE_NAME" {
  value = azurerm_search_service.this.name
}


output "AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY" {
  value     = azurerm_search_service.this.primary_key
  sensitive = true
}

output "AZURE_SEARCH_SERVICE_SECONDARY_ADMIN_KEY" {
  value     = azurerm_search_service.this.secondary_key
  sensitive = true
}
