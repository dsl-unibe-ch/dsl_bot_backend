#------- Global --------

variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }


# ----- Container Registry --------
variable "container_registry_name" {type  = string}
variable "container_registry_sku" {type = string}
variable "admin_enabled" {
  type        = bool
  default     = false
}
variable "retention_enabled" {
  type        = bool
  default     = false
}
variable "retention_days" {
  type        = number
  default     = 30
}
variable "anonymous_pull_enabled" {
  type        = bool
  default     = false
}
variable "data_endpoint_enabled" {
  type        = bool
  default     = false
}
