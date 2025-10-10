
output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  value = azurerm_container_registry.this.login_server
}

output "AZURE_CONTAINER_REGISTRY_ID" {
  value = azurerm_container_registry.this.id
}
