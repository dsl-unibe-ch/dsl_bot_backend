output "AZURE_APP_SERVICE_ID" {
  value = azurerm_linux_web_app.app.id
}

output "AZURE_APP_SERVICE_DEFAULT_HOSTNAME" {
  value = azurerm_linux_web_app.app.default_hostname
}

output "AZURE_APP_SERVICE_IDENTITY_PRINCIPAL_ID" {
  value = azurerm_linux_web_app.app.identity[0].principal_id
}

output "AZURE_APP_SERVICE_SLOT_ID" {
  value = try(azurerm_linux_web_app_slot.slot[0].id, null)
}
