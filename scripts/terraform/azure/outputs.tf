#----- Azure Openai --------------

output "AZURE_OPENAI_VECTORIZER_ENDPOINT" {
  value     = module.openai[0].AZURE_OPENAI_VECTORIZER_ENDPOINT
  sensitive = true
}

output "AZURE_OPENAI_ENDPOINT" {
  value     = module.openai[0].AZURE_OPENAI_ENDPOINT
  sensitive = true
}

output "AZURE_OPENAI_ACCOUNT_ID" {
  value     = module.openai[0].AZURE_OPENAI_ACCOUNT_ID
  sensitive = true
}

output "AZURE_OPENAI_CHAT_DEPLOYMENT" {
  value = module.openai[0].AZURE_OPENAI_CHAT_DEPLOYMENT
}

output "AZURE_OPENAI_CHAT_MODEL_NAME" {
  value = module.openai[0].AZURE_OPENAI_CHAT_MODEL_NAME
}

output "AZURE_OPENAI_CHAT_API_VERSION" {
  value = module.openai[0].AZURE_OPENAI_CHAT_API_VERSION
}

output "AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT" {
  value = module.openai[0].AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT
}
output "AZURE_OPENAI_SEARCH_EMBEDDING_MODEL_NAME" {
  value = module.openai[0].AZURE_OPENAI_SEARCH_EMBEDDING_MODEL_NAME
}
output "AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION" {
  value = module.openai[0].AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION
}

output "AZURE_OPENAI_PRIMARY_KEY"{
  value = module.openai[0].AZURE_OPENAI_PRIMARY_KEY
  sensitive = true
}

output "AZURE_OPENAI_SECONDARY_KEY"{
  value = module.openai[0].AZURE_OPENAI_SECONDARY_KEY
  sensitive = true
}


#----- Azure Container Registry --------------

output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  value = coalesce(module.azurerm_container_registry[0].AZURE_CONTAINER_REGISTRY_LOGIN_SERVER,data.azurerm_container_registry.acr[0].login_server)
  sensitive = true
}

output "AZURE_CONTAINER_REGISTRY_ID" {
  value = coalesce(module.azurerm_container_registry[0].AZURE_CONTAINER_REGISTRY_ID, data.azurerm_container_registry.acr[0].id)
  sensitive = true
}

#----- Azure Storage Account --------------

output "AZURE_STORAGE_ACCOUNT_ID" {
  value = coalesce(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_ID, data.azurerm_storage_account.sa[0].id)
  sensitive = true
}

output "AZURE_STORAGE_ACCOUNT_NAME" {
  value = coalesce(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_NAME, data.azurerm_storage_account.sa[0].name)
  sensitive = true
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_BLOB_ENDPOINT" {
  value = coalesce(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_PRIMARY_BLOB_ENDPOINT, data.azurerm_storage_account.sa[0].primary_blob_endpoint)
  sensitive = true
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING" {
  sensitive = true
  value     = module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_ACCESS_KEY" {
  sensitive = true
  value     = module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_PRIMARY_ACCESS_KEY
}

#----- Azure Search Service --------------

output "AZURE_SEARCH_SERVICE_ID" {
  value = module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_ID
}

output "AZURE_SEARCH_SERVICE_NAME" {
  value = module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_NAME
}

output "AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY" {
  value     = module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY
  sensitive = true
}

output "AZURE_SEARCH_SERVICE_SECONDARY_ADMIN_KEY" {
  value     = module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_SECONDARY_ADMIN_KEY
  sensitive = true
}

# Endpoint
output "AZURE_SEARCH_ENDPOINT" {
  value = module.azurerm_search_service[0].AZURE_SEARCH_ENDPOINT
}

output "AZURE_AI_SEARCH_INDEX_NAME" {
  value = module.azurerm_search_service[0].AZURE_SEARCH_INDEX_NAME
}

#----- Azure Key Vault --------------
output "AZURE_KEY_VAULT_ID" {
  value = module.azurerm_key_vault[0].AZURE_KEY_VAULT_ID
}

output "AZURE_KEY_VAULT_NAME" {
  value = module.azurerm_key_vault[0].AZURE_KEY_VAULT_NAME
}

output "AZURE_KEY_VAULT_URI" {
  value = module.azurerm_key_vault[0].AZURE_KEY_VAULT_URI
}

#----- Kubernetes (AKS) --------------
output "kube_config_raw" {
  value     = module.kubernetes_cluster[0].KUBE_CONFIG_RAW
  sensitive = true
}