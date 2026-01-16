#----- Azure Openai --------------

output "AZURE_OPENAI_VECTORIZER_ENDPOINT" {
  value     = try(module.openai[0].AZURE_OPENAI_VECTORIZER_ENDPOINT, null)
  sensitive = true
}

output "AZURE_OPENAI_ENDPOINT" {
  value     = try(module.openai[0].AZURE_OPENAI_ENDPOINT, null)
  sensitive = true
}

output "AZURE_OPENAI_CHAT_DEPLOYMENT" {
  value = try(module.openai[0].AZURE_OPENAI_CHAT_DEPLOYMENT, null)
}

output "AZURE_OPENAI_CHAT_MODEL_NAME" {
  value = try(module.openai[0].AZURE_OPENAI_CHAT_MODEL_NAME, null)
}

output "AZURE_OPENAI_CHAT_API_VERSION" {
  value = try(module.openai[0].AZURE_OPENAI_CHAT_API_VERSION, null)
}

output "AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT" {
  value = try(module.openai[0].AZURE_OPENAI_SEARCH_EMBEDDING_DEPLOYMENT, null)
}
output "AZURE_OPENAI_SEARCH_EMBEDDING_MODEL_NAME" {
  value = try(module.openai[0].AZURE_OPENAI_SEARCH_EMBEDDING_MODEL_NAME, null)
}
output "AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION" {
  value = try(module.openai[0].AZURE_OPENAI_SEARCH_EMBEDDING_API_VERSION, null)
}

output "AZURE_OPENAI_PRIMARY_KEY"{
  value = try(module.openai[0].AZURE_OPENAI_PRIMARY_KEY, null)
  sensitive = true
}


#----- Azure Container Registry --------------
output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  value = coalesce(
    try(module.azurerm_container_registry[0].AZURE_CONTAINER_REGISTRY_LOGIN_SERVER, null),
    try(data.azurerm_container_registry.acr[0].login_server, null)
  )
}

#----- Azure Storage Account --------------

output "AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING" {
  sensitive = true
  value     = try(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING, null)
}

output "AZURE_CONTAINER_STORAGE_SECRETS_NAME" {
  value = try(module.azurerm_storage_account[0].AZURE_CONTAINER_STORAGE_SECRETS_NAME, null)
}

output "AZURE_CONTAINER_STORAGE_NAME" {
  value = try(module.azurerm_storage_account[0].AZURE_CONTAINER_STORAGE_NAME, null)
}

#----- Azure Search Service --------------


output "AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY" {
  value     = try(module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY, null)
  sensitive = true
}
# Endpoint
output "AZURE_SEARCH_ENDPOINT" {
  value = try(module.azurerm_search_service[0].AZURE_SEARCH_ENDPOINT, null)
}

output "AZURE_AI_SEARCH_INDEX_NAME" {
  value = try(module.azurerm_search_service[0].AZURE_SEARCH_INDEX_NAME, null)
}

#----- Azure Key Vault --------------
output "AZURE_KEY_VAULT_NAME" {
  value = try(module.azurerm_key_vault[0].AZURE_KEY_VAULT_NAME, null)
}

output "AZURE_KEY_VAULT_URI" {
  value = try(module.azurerm_key_vault[0].AZURE_KEY_VAULT_URI, null)
}


#----- Resource Group --------------
output "RESOURCE_GROUP_NAME" {
  value = azurerm_resource_group.rg.name
}

#----- Kubernetes (AKS) --------------
output "kube_config_raw" {
  value     = try(module.kubernetes_cluster[0].KUBE_CONFIG_RAW, null)
  sensitive = true
}

output "AKS_CLUSTER_NAME" {
  value = try(module.kubernetes_cluster[0].AZURE_AKS_NAME, null)
}

#----- API Management (APIM) --------------
output "APIM_GATEWAY_URL" {
  value       = try(module.api_management[0].apim_gateway_url, null)
  description = "APIM Gateway URL - use this as your API endpoint"
}

output "APIM_FULL_API_URL" {
  value       = try(module.api_management[0].full_api_url, null)
  description = "Full API URL including path (e.g., https://apim-kb-dev-001.azure-api.net/api)"
}

output "BACKEND_URL" {
  value       = try(module.api_management[0].full_api_url, null)
  description = "Frontend/Public URL - This is the URL your frontend application should use"
}

output "APIM_NAME" {
  value       = try(module.api_management[0].apim_name, null)
  description = "Name of the API Management instance"
}

output "APIM_ID" {
  value       = try(module.api_management[0].apim_id, null)
  description = "ID of the API Management instance"
}