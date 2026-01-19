#------- Global --------

variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }


# ----- OpenAI --------
variable "cognitive_model_account_name" { 
    description = "Cognitive model account name."
    type = string 
}
variable "cognitive_model_deployment_sku_name" { 
    description = "Cognitive model deployment SKU name."
    type = string 
}
variable "cognitive_model_account_sku_name" { 
    description = "Cognitive model account SKU name."
    type = string 
}
variable "cognitive_model_deployment_name" { 
    description = "Cognitive model deployment name."
    type = string 
}
variable "cognitive_model_name" { 
    description = "Cognitive model name."
    type = string 
}
variable "cognitive_model_version" { 
    description = "Cognitive model version."
    type = string 
}
variable "cognitive_model_account_kind" { 
    type = string 
    description = "Cognitive model account kind."
}
variable "cognitive_model_embedding_deployment_name" { 
    description = "Cognitive model embedding deployment name."
    type = string 
}
variable "cognitive_model_embedding_name" { 
    description = "Cognitive model embedding name."
    type = string 
}
variable "cognitive_model_embedding_deployment_sku_name" { 
    description = "Cognitive model embedding deployment SKU name."
    type = string 
}
variable "cognitive_model_embedding_version" { 
    description = "Cognitive model embedding version."
    type = string 
}
variable "cognitive_model_embedding_deployment_capacity" { 
    description = "Cognitive model embedding deployment capacity."
    type = number 
}

variable "cognitive_model_deployment_capacity" { 
    description = "Cognitive model deployment capacity."
    type = number 
}

# ----- API Versions (for SDK/REST) ------

variable "cognitive_model_chat_api_version" {
  description = "Azure OpenAI Chat API version to use (e.g., 2024-12-01-preview)."
  type        = string
  default     = "2024-12-01-preview"
}

variable "cognitive_model_embedding_api_version" {
  description = "Azure OpenAI Embeddings API version to use (e.g., 2024-02-01)."
  type        = string
  default     = "2024-02-01"
}
