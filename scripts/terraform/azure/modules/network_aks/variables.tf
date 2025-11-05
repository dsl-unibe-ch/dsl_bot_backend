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


