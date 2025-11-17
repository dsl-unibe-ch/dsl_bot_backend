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
    only_critical_addons_enabled = true # restrict default/system node pool to only critical k8s addons / components (e.g., metric server, cluster autoscaler, etc.)
  }

  tags = var.tags
}

resource "azurerm_kubernetes_cluster_node_pool" "extra_pools" {
  for_each              = var.additional_node_pools

  name                  = each.key
  kubernetes_cluster_id = azurerm_kubernetes_cluster.this.id

  vm_size               = each.value.vm_size
  node_count            = each.value.node_count
  os_disk_size_gb       = each.value.os_disk_size_gb
  os_type               = "Linux"
  os_sku                = each.value.os_sku
  vnet_subnet_id        = each.value.vnet_subnet_id

  mode                  = each.value.mode

  auto_scaling_enabled  = lookup(each.value, "auto_scaling_enabled", false)
  min_count             = lookup(each.value, "auto_scaling_enabled", false) ? lookup(each.value, "min_count", 1) : null
  max_count             = lookup(each.value, "auto_scaling_enabled", false) ? lookup(each.value, "max_count", 1) : null
}