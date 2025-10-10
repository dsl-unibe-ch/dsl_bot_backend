resource "azurerm_service_plan" "this" {
  name                = var.app_service_plan_name
  resource_group_name = var.resource_group_name
  location            = var.resource_group_location
  os_type             = var.app_service_plan_os_type     
  sku_name            = var.app_service_plan_sku_name    
  worker_count        = var.app_service_plan_worker_count
}
