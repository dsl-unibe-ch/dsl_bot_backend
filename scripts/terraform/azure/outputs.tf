#----- Azure Openai --------------

output "AZURE_OPENAI_ENDPOINT" {
  value     = module.openai.AZURE_OPENAI_ENDPOINT
  sensitive = true
}

output "AZURE_OPENAI_ACCOUNT_ID" {
  value     = module.openai.AZURE_OPENAI_ACCOUNT_ID
  sensitive = true
}

output "AZURE_OPENAI_CHAT_DEPLOYMENT" {
  value = module.openai.AZURE_OPENAI_CHAT_DEPLOYMENT
}

output "AZURE_OPENAI_CHAT_MODEL_NAME" {
  value = module.openai.AZURE_OPENAI_CHAT_MODEL_NAME
}

output "AZURE_OPENAI_CHAT_API_VERSION" {
  value = module.openai.AZURE_OPENAI_CHAT_API_VERSION
}

#----- Azure App Service Plan --------------

output "AZURE_APP_SERVICE_PLAN_ID" {
  value = module.azurerm_service_plan.AZURE_APP_SERVICE_PLAN_ID
}

output "AZURE_APP_SERVICE_PLAN_NAME" {
  value = module.azurerm_service_plan.AZURE_APP_SERVICE_PLAN_NAME
}

output "AZURE_APP_SERVICE_PLAN_SKU" {
  value = module.azurerm_service_plan.AZURE_APP_SERVICE_PLAN_SKU
}

#----- Azure App Service --------------

output "AZURE_APP_SERVICE_ID" {
  value = try(module.azurerm_app_service[0].AZURE_APP_SERVICE_ID, null)
}

output "AZURE_APP_SERVICE_DEFAULT_HOSTNAME" {
  value = try(module.azurerm_app_service[0].AZURE_APP_SERVICE_DEFAULT_HOSTNAME, null)
}

output "AZURE_APP_SERVICE_IDENTITY_PRINCIPAL_ID" {
  value = try(module.azurerm_app_service[0].AZURE_APP_SERVICE_IDENTITY_PRINCIPAL_ID, null)
}

output "AZURE_APP_SERVICE_SLOT_ID" {
  value = try(module.azurerm_app_service[0].AZURE_APP_SERVICE_SLOT_ID, null)
}


#----- Azure Container Registry --------------

output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  value = module.azurerm_container_registry.AZURE_CONTAINER_REGISTRY_LOGIN_SERVER
}

output "AZURE_CONTAINER_REGISTRY_ID" {
  value = module.azurerm_container_registry.AZURE_CONTAINER_REGISTRY_ID
}

#----- Azure Storage Account --------------

output "AZURE_STORAGE_ACCOUNT_ID" {
  value = module.azurerm_storage_account.AZURE_STORAGE_ACCOUNT_ID
}

output "AZURE_STORAGE_ACCOUNT_NAME" {
  value = module.azurerm_storage_account.AZURE_STORAGE_ACCOUNT_NAME
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_BLOB_ENDPOINT" {
  value = module.azurerm_storage_account.AZURE_STORAGE_ACCOUNT_PRIMARY_BLOB_ENDPOINT
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING" {
  sensitive = true
  value     = module.azurerm_storage_account.AZURE_STORAGE_ACCOUNT_PRIMARY_CONNECTION_STRING
}

output "AZURE_STORAGE_ACCOUNT_PRIMARY_ACCESS_KEY" {
  sensitive = true
  value     = module.azurerm_storage_account.AZURE_STORAGE_ACCOUNT_PRIMARY_ACCESS_KEY
}

#----- Azure Search Service --------------

output "AZURE_SEARCH_SERVICE_ID" {
  value = module.azurerm_search_service.AZURE_SEARCH_SERVICE_ID
}

output "AZURE_SEARCH_SERVICE_NAME" {
  value = module.azurerm_search_service.AZURE_SEARCH_SERVICE_NAME
}

output "AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY" {
  value = module.azurerm_search_service.AZURE_SEARCH_SERVICE_PRIMARY_ADMIN_KEY
  sensitive = true
}

output "AZURE_SEARCH_SERVICE_SECONDARY_ADMIN_KEY" {
  value = module.azurerm_search_service.AZURE_SEARCH_SERVICE_SECONDARY_ADMIN_KEY
  sensitive = true
}

#----- Azure Key Vault --------------
output "AZURE_KEY_VAULT_ID" {
  value = module.azurerm_key_vault.AZURE_KEY_VAULT_ID
}

output "AZURE_KEY_VAULT_NAME" {
  value = module.azurerm_key_vault.AZURE_KEY_VAULT_NAME
}

output "AZURE_KEY_VAULT_URI" {
  value = module.azurerm_key_vault.AZURE_KEY_VAULT_URI
}