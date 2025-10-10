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

#----- Azure Container Registry --------------

output "AZURE_CONTAINER_REGISTRY_LOGIN_SERVER" {
  value = module.azurerm_container_registry.AZURE_CONTAINER_REGISTRY_LOGIN_SERVER
}

output "AZURE_CONTAINER_REGISTRY_ID" {
  value = module.azurerm_container_registry.AZURE_CONTAINER_REGISTRY_ID
}

