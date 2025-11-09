resource "azurerm_virtual_network" "this" {
  name                = var.vnet_name
  address_space       = var.vnet_address_space
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_network_security_group" "this" {
  name                = var.network_security_group_name
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name

  dynamic "security_rule" {
    for_each = []
    content {
      name       = "noop"
      priority   = 4096
      direction  = "Inbound"
      access     = "Deny"
      protocol   = "Tcp"
      source_port_range      = "*"
      destination_port_range = "*"
      source_address_prefix  = "*"
      destination_address_prefix = "*"
    }
  }

  tags = var.tags
}

resource "azapi_resource" "subnet" {
  type      = "Microsoft.Network/virtualNetworks/subnets@2025-01-01" # Versions from https://learn.microsoft.com/en-us/azure/templates/microsoft.network/virtualnetworks/subnets?pivots=deployment-language-bicep
  name      = var.subnet_name
  parent_id = azurerm_virtual_network.this.id
  body = {
    properties = {
      addressPrefix = var.subnet_address_prefix
      networkSecurityGroup = {
        id = azurerm_network_security_group.this.id
      }
    }
  }
}

