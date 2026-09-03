
output "AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING" {
  sensitive = true
  value     = azurerm_storage_account.this.primary_connection_string
}

output "AZURE_CONTAINER_STORAGE_SECRETS_NAME" {
  value = azurerm_storage_container.containers["dsl-bot-secrets"].name
}

output "AZURE_CONTAINER_STORAGE_NAME" {
  value = azurerm_storage_container.containers["dsl-bot-logs"].name
}