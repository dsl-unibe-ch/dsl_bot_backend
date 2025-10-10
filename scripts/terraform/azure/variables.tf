#------- Global --------

variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }


# ----- OpenAI --------
variable "cognitive_model_account_name" { type = string }
variable "cognitive_model_deployment_sku_name" { type = string }
variable "cognitive_model_account_sku_name" { type = string }
variable "cognitive_model_deployment_name" { type = string }
variable "cognitive_model_name" { type = string }
variable "cognitive_model_version" { type = string }
variable "cognitive_model_account_kind" { type = string }

variable "cognitive_model_embedding_deployment_name" { type = string }
variable "cognitive_model_embedding_name" { type = string }
variable "cognitive_model_embedding_deployment_sku_name" { type = string }
variable "cognitive_model_embedding_version" { type = string }

# ----- AI Foundry ------

variable "aif_hub_name" { type = string }
variable "aif_project_name" { type = string }


# ----- App Service Plan --------
variable "app_service_plan_name" {type = string}
variable "app_service_plan_sku_name" {type = string}
variable "app_service_plan_os_type" {
  type        = string
  default     = "Linux"
}
variable "app_service_plan_worker_count" {
  type        = number
  default     = 1
}