#------- Global --------

variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }


# ----- Container Registry --------
variable "container_registry_name" {type  = string}
variable "container_registry_sku" {type = string}
variable "container_repository_name" { type = string }
variable "container_registry_resource_group_name" { type = string }
variable "container_registry_tags" { type = map(string) }
