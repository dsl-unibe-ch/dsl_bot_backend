#----- Azure Openai --------------

output "AZURE_OPENAI_VECTORIZER_ENDPOINT" {
  value     = try(module.openai[0].AZURE_OPENAI_VECTORIZER_ENDPOINT, null)
  sensitive = true
}

output "AZURE_OPENAI_ENDPOINT" {
  value     = try(module.openai[0].AZURE_OPENAI_ENDPOINT, null)
  sensitive = true
}

output "AZURE_OPENAI_ACCOUNT_ID" {
  value     = try(module.openai[0].AZURE_OPENAI_ACCOUNT_ID, null)
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

output "AZURE_OPENAI_SECONDARY_KEY"{
  value = try(module.openai[0].AZURE_OPENAI_SECONDARY_KEY, null)
  sensitive = true
}


#----- Azure Container Registry --------------
output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  value = coalesce(
    try(module.azurerm_container_registry[0].AZURE_CONTAINER_REGISTRY_LOGIN_SERVER, null),
    try(data.azurerm_container_registry.acr[0].login_server, null)
  )
}

output "AZURE_CONTAINER_REGISTRY_ID" {
  value = coalesce(
    try(module.azurerm_container_registry[0].AZURE_CONTAINER_REGISTRY_ID, null),
    try(data.azurerm_container_registry.acr[0].id, null)
  )
}
#----- Azure Storage Account --------------
output "AZURE_STORAGE_ACCOUNT_ID" {
  value = coalesce(
    try(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_ID, null),
    try(data.azurerm_storage_account.sa[0].id, null)
  )
}

output "AZURE_STORAGE_ACCOUNT_NAME" {
  value = coalesce(
    try(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_NAME, null),
    try(data.azurerm_storage_account.sa[0].name, null)
  )
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_BLOB_ENDPOINT" {
  value = coalesce(
    try(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_PRIMARY_BLOB_ENDPOINT, null),
    try(data.azurerm_storage_account.sa[0].primary_blob_endpoint, null)
  )
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING" {
  sensitive = true
  value     = try(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING, null)
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_ACCESS_KEY" {
  sensitive = true
  value     = try(module.azurerm_storage_account[0].AZURE_STORAGE_ACCOUNT_PRIMARY_ACCESS_KEY, null)
}
#----- Azure Search Service --------------
output "AZURE_SEARCH_SERVICE_ID" {
  value = try(module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_ID, null)
}

output "AZURE_SEARCH_SERVICE_NAME" {
  value = try(module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_NAME, null)
}

output "AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY" {
  value     = try(module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY, null)
  sensitive = true
}

output "AZURE_SEARCH_SERVICE_SECONDARY_ADMIN_KEY" {
  value     = try(module.azurerm_search_service[0].AZURE_SEARCH_SERVICE_SECONDARY_ADMIN_KEY, null)
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
output "AZURE_KEY_VAULT_ID" {
  value = try(module.azurerm_key_vault[0].AZURE_KEY_VAULT_ID, null)
}

output "AZURE_KEY_VAULT_NAME" {
  value = try(module.azurerm_key_vault[0].AZURE_KEY_VAULT_NAME, null)
}

output "AZURE_KEY_VAULT_URI" {
  value = try(module.azurerm_key_vault[0].AZURE_KEY_VAULT_URI, null)
}

#----- Kubernetes (AKS) --------------
output "kube_config_raw" {
  value     = try(module.kubernetes_cluster[0].KUBE_CONFIG_RAW, null)
  sensitive = true
}

output "AZURE_AKS_ADDITIONAL_NODE_POOLS" {
  value = try(module.kubernetes_cluster[0].AZURE_AKS_ADDITIONAL_NODE_POOLS, null)
}

output "AKS_CLUSTER_NAME" {
  value = try(module.kubernetes_cluster[0].AZURE_AKS_NAME, null)
}

#----- Resource Group --------------
output "RESOURCE_GROUP_NAME" {
  value = azurerm_resource_group.rg.name
}