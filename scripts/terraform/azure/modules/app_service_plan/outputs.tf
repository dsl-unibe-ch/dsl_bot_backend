output "AZURE_APP_SERVICE_PLAN_ID" {
  value = azurerm_service_plan.this.id
}

output "AZURE_APP_SERVICE_PLAN_NAME" {
  value = azurerm_service_plan.this.name
}
