output "AZURE_STORAGE_ACCOUNT_ID" {
  value = azurerm_storage_account.this.id
}

output "AZURE_STORAGE_ACCOUNT_NAME" {
  value = azurerm_storage_account.this.name
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_BLOB_ENDPOINT" {
  value = azurerm_storage_account.this.primary_blob_endpoint
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING" {
  sensitive = true
  value     = azurerm_storage_account.this.primary_connection_string
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_ACCESS_KEY" {
  sensitive = true
  value     = azurerm_storage_account.this.primary_access_key
}