output "KUBE_CONFIG_RAW" {
  value     = azurerm_kubernetes_cluster.this.kube_config_raw
  sensitive = true
}

output "AZURE_AKS_NAME" { value = azurerm_kubernetes_cluster.this.name }