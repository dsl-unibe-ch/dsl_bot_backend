
# --- OpenAI account ---
resource "azurerm_cognitive_account" "openai" {
  name                = var.cognitive_model_account_name
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name
  kind                = var.cognitive_model_account_kind
  sku_name            = var.cognitive_model_account_sku_name

  identity {
    type = "SystemAssigned"
  }
}

# --- Chat deployment ---s
resource "azurerm_cognitive_deployment" "model" {
  name                 = var.cognitive_model_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = var.cognitive_model_account_kind
    name    = var.cognitive_model_name
    version = var.cognitive_model_version
  }

  sku {
    name = var.cognitive_model_deployment_sku_name
    capacity = var.cognitive_model_deployment_capacity
  }

}

# --- Embedding deployment ---
resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.cognitive_model_embedding_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = var.cognitive_model_account_kind
    name    = var.cognitive_model_embedding_name
    version = var.cognitive_model_embedding_version
  }

  sku {
    name = var.cognitive_model_embedding_deployment_sku_name
    capacity = var.cognitive_model_embedding_deployment_capacity
  }
}

