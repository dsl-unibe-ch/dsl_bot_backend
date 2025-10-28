resource "azurerm_kubernetes_cluster" "this" {
  name                = var.cluster_name
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.dns_prefix
  node_resource_group = var.node_resource_group_name

  identity {
    type = "SystemAssigned"
  }

  linux_profile {
    admin_username = var.admin_username

    dynamic "ssh_key" {
      for_each = var.admin_ssh_public_keys
      content {
        key_data = ssh_key.value
      }
    }
  }

  default_node_pool {
    name            = var.default_node_pool_name
    node_count      = var.default_node_pool_node_count
    vm_size         = var.default_node_pool_vm_size
    os_disk_size_gb = var.default_node_pool_os_disk_size_gb
    os_sku          = var.default_node_pool_os_sku
    type            = "VirtualMachineScaleSets"
    vnet_subnet_id  = var.vnet_subnet_id
  }

  dynamic "network_profile" {
    for_each = var.configure_network_profile ? [1] : []
    content {
      network_plugin = var.network_plugin
      # Keep other settings default unless provided later
    }
  }

  kubernetes_version = var.kubernetes_version

  tags = var.tags
}

