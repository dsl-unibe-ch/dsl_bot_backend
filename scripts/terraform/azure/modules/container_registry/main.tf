resource "azurerm_container_registry" "this" {
  name                          = var.container_registry_name
  resource_group_name           = var.container_registry_resource_group_name
  location                      = var.resource_group_location
  sku                           = var.container_registry_sku
  tags                          = var.container_registry_tags
}
