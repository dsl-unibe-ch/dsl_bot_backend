output "AZURE_OPENAI_ENDPOINT" {
  value     = azurerm_cognitive_account.openai.endpoint
  sensitive = true
}

output "AZURE_OPENAI_ACCOUNT_ID" {
  value     = azurerm_cognitive_account.openai.id
  sensitive = true
}

output "AZURE_OPENAI_CHAT_DEPLOYMENT" {
  value = azurerm_cognitive_deployment.model.name
}

output "AZURE_OPENAI_CHAT_MODEL_NAME" {
  value = azurerm_cognitive_deployment.model.model[0].name
}

output "AZURE_OPENAI_CHAT_API_VERSION" {
  value = azurerm_cognitive_deployment.model.model[0].version
}

