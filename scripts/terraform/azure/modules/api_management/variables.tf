variable "apim_name" {
  type        = string
  description = "Name of the API Management instance"
}

variable "apim_sku_name" {
  type        = string
  description = "SKU name of the API Management instance"
}

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group"
}

variable "resource_group_location" {
  type        = string
  description = "Location of the resource group"
}

variable "publisher_name" {
  type        = string
  description = "Publisher organization name"
}

variable "publisher_email" {
  type        = string
  description = "Publisher email address"
}

variable "backend_url" {
  type        = string
  description = "Backend AKS service URL (e.g., http://kioskbot-api.default.svc.cluster.local:80)"
}

variable "api_name" {
  type        = string
  description = "Name of the API"
}

variable "api_display_name" {
  type        = string
  description = "Display name of the API"
}

variable "api_path" {
  type        = string
  description = "Path segment for the API"
}

variable "api_revision" {
  type        = string
  description = "Revision number of the API"
}

variable "api_protocols" {
  type        = list(string)
  description = "Protocols supported by the API"
}

variable "subscription_required" {
  type        = bool
  description = "Whether API requires subscription key"
}

# Rate limiting for /initialize-agent
variable "initialize_rate_limit_calls" {
  type        = number
  description = "Number of session initialization calls allowed per minute"
}

variable "initialize_quota_calls" {
  type        = number
  description = "Total session initialization calls allowed per day"
}

# Rate limiting for /invoke-agent (OpenAI calls - STRICT)
variable "invoke_rate_limit_calls" {
  type        = number
  description = "Number of AI query calls allowed per minute (STRICT - controls OpenAI costs)"
}

variable "invoke_quota_calls" {
  type        = number
  description = "Total AI query calls allowed per day (STRICT - controls OpenAI costs)"
}

# Rate limiting for /send-feedback
variable "feedback_rate_limit_calls" {
  type        = number
  description = "Number of feedback submissions allowed per minute"
}

variable "feedback_quota_calls" {
  type        = number
  description = "Total feedback submissions allowed per day"
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to the APIM resource"
}
