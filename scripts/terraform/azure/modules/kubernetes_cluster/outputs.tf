output "AZURE_AKS_ID" { value = azurerm_kubernetes_cluster.this.id }
output "AZURE_AKS_NAME" { value = azurerm_kubernetes_cluster.this.name }
output "KUBE_CONFIG_RAW" {
  value     = azurerm_kubernetes_cluster.this.kube_config_raw
  sensitive = true
}

output "KUBE_ADMIN_CONFIG_RAW" {
  value     = azurerm_kubernetes_cluster.this.kube_admin_config_raw
  sensitive = true
}

output "AZURE_AKS_ADDITIONAL_NODE_POOLS" {
  value = {
    for name, pool in azurerm_kubernetes_cluster_node_pool.extra_pools : name => {
      id         = pool.id
      name       = pool.name
      mode       = pool.mode
      vm_size    = pool.vm_size
      node_count = pool.node_count
      os_sku     = pool.os_sku
    }
  }
}

