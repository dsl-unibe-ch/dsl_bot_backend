output "apim_id" {
  value       = azurerm_api_management.apim.id
  description = "ID of the API Management instance"
}

output "apim_name" {
  value       = azurerm_api_management.apim.name
  description = "Name of the API Management instance"
}

output "apim_gateway_url" {
  value       = azurerm_api_management.apim.gateway_url
  description = "Gateway URL for the APIM instance (use this as your API endpoint)"
}

output "apim_gateway_regional_url" {
  value       = azurerm_api_management.apim.gateway_regional_url
  description = "Regional gateway URL for the APIM instance"
}

output "apim_public_ip_addresses" {
  value       = azurerm_api_management.apim.public_ip_addresses
  description = "Public IP addresses for the APIM gateway"
}

output "api_id" {
  value       = azurerm_api_management_api.bot_api.id
  description = "ID of the Bot API"
}

output "api_path" {
  value       = azurerm_api_management_api.bot_api.path
  description = "Path of the Bot API"
}

output "full_api_url" {
  value       = "${azurerm_api_management.apim.gateway_url}/${azurerm_api_management_api.bot_api.path}"
  description = "Full API URL (Gateway URL + API path)"
}
