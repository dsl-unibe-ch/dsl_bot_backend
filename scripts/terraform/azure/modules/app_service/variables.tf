#------- Global --------

variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }


# ----- App Service Plan --------

variable "app_service_plan_name" {
  description = "App Service Plan name (3-60 chars, lowercase letters & numbers only)."
  type = string
  }

variable "app_service_plan_id" {
  description = "App Service Plan ID."
  type = string
  }

variable "app_service_plan_sku_name" {
  description = "App Service Plan SKU name."
  type = string
  }

# ----- Container Registry --------
variable "container_registry_name" {type  = string}
variable "container_registry_login_server" {type  = string}  # e.g. crkbdev001.azurecr.io
variable "container_registry_id" {type  = string}


# ----- App Service -----

# App & container
variable "app_name"            { type = string }  # base (web app will be "<app_name>-web")
variable "container_repository"{ type = string }  # repo inside ACR, e.g. "kioskbot-backend-api"
variable "container_image_tag" { type = string }  # e.g. "abcd123-dev"
variable "container_port"      { 
    type = number
    default = 8080 
}

# Optional settings
variable "app_service_app_settings"        { 
    type = map(string)
    default = {} 
}

# Optional slot
variable "app_service_enable_slot"         { 
    type = bool
    default = false 
}

variable "app_service_slot_name"           { 
    type = string
    default = "staging" 
}

# (optional) App Insights – pass the connection string if you have one
variable "app_insights_connection_string" {
  type    = string
  default = null
}


# Optional: override path to pyproject.toml (default uses repo root)
variable "pyproject_path" { 
  type = string
  default = null 
}

# Toggle assigning AcrPull to the Web App MSI
variable "grant_acr_pull" { 
  type = bool
  default = true 
}

variable "tags" { 
  type = map(string)
  default = {} 
}
