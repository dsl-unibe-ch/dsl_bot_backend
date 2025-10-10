#------- Global --------

variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }


# ----- App Service Plan --------
variable "app_service_plan_name" {
  description = "App Service Plan name (3-60 chars, lowercase letters & numbers only)."
  type = string
  }
variable "app_service_plan_sku_name" {
  description = "App Service Plan SKU name."
  type = string
  }
variable "app_service_plan_os_type" {
  description = "App Service Plan OS type."
  type        = string
  default     = "Linux"
}
variable "app_service_plan_worker_count" {
  description = "App Service Plan worker count."
  type        = number
  default     = 1
}
