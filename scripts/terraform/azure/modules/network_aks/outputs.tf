output "AKS_VNET_ID" { value = azurerm_virtual_network.this.id }
output "AKS_SUBNET_ID" { value = azapi_resource.subnet.id }
output "AKS_NSG_ID" { value = azurerm_network_security_group.this.id }