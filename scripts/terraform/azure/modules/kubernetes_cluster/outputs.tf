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

