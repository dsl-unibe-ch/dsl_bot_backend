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
    for_each = { for idx, ip in var.allowed_external_ips : idx => ip }
    content {
      name                       = "AllowBotApiInbound-${security_rule.key}"
      priority                   = 100 + security_rule.key
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = var.api_destination_port
      source_address_prefix      = security_rule.value
      destination_address_prefix = "*"
    }
  }

  tags = var.tags
}

# Org policy "Deny-Subnet-Non-UDR" requires every subnet to have a route table attached.
# The route table is auto-created by the platform in its own RG within this same subscription.
data "azurerm_route_table" "this" {
  name                = var.route_table_name
  resource_group_name = var.route_table_resource_group_name
}

resource "azapi_resource" "subnet" {
  type      = "Microsoft.Network/virtualNetworks/subnets@2023-11-01" 
  name      = var.subnet_name
  parent_id = azurerm_virtual_network.this.id
  body = {
    properties = {
      addressPrefix = var.subnet_address_prefix
      networkSecurityGroup = {
        id = azurerm_network_security_group.this.id
      }
      routeTable = {
        id = data.azurerm_route_table.this.id
      }
    }
  }
}

