output "AZURE_OPENAI_VECTORIZER_ENDPOINT" {
  value     = "https://${azurerm_cognitive_account.openai.name}.openai.azure.com"
  sensitive = true
}

output "AZURE_OPENAI_ENDPOINT" {
  value     = azurerm_cognitive_account.openai.endpoint
  sensitive = true
}


output "AZURE_OPENAI_CHAT_DEPLOYMENT" {
  value = azurerm_cognitive_deployment.model.name
}

output "AZURE_OPENAI_CHAT_MODEL_NAME" {
  value = azurerm_cognitive_deployment.model.model[0].name
}

output "AZURE_OPENAI_CHAT_API_VERSION" {
  value = var.cognitive_model_chat_api_version
}

output "AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT" {
  value = azurerm_cognitive_deployment.embedding.name
}

output "AZURE_OPENAI_SEARCH_EMBEDDING_MODEL_NAME" {
  value = azurerm_cognitive_deployment.embedding.model[0].name
}

output "AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION" {
  value = var.cognitive_model_embedding_api_version
}

output "AZURE_OPENAI_PRIMARY_KEY" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
}
