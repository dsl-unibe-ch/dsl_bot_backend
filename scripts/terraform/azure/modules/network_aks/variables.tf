variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }

variable "vnet_name" { type = string }
variable "vnet_address_space" { type = list(string) }
variable "subnet_name" { type = string }
variable "subnet_address_prefix" { type = string }
variable "network_security_group_name" { type = string }


variable "tags" {
  type    = map(string)
  default = {}
}

variable "allowed_external_ips" {
  description = "List of external IP addresses allowed to access the kioskbot-api (CIDR notation, e.g., '203.0.113.10/32')"
  type        = list(string)
  default     = []
}

variable "api_destination_port" {
  description = "Destination port for the kioskbot-api service"
  type        = string
  default     = "*"
}
