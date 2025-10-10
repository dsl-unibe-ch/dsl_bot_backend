# --- Resource group ---
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.resource_group_location
}

# --- OpenAI ---

module "openai" {
  subscription_id                               = var.subscription_id
  resource_group_location                       = azurerm_resource_group.rg.location
  resource_group_name                           = azurerm_resource_group.rg.name
  cognitive_model_account_kind                  = var.cognitive_model_account_kind
  cognitive_model_account_name                  = var.cognitive_model_account_name
  cognitive_model_deployment_sku_name           = var.cognitive_model_deployment_sku_name
  cognitive_model_account_sku_name              = var.cognitive_model_account_sku_name
  cognitive_model_deployment_name               = var.cognitive_model_deployment_name
  cognitive_model_name                          = var.cognitive_model_name
  cognitive_model_version                       = var.cognitive_model_version
  cognitive_model_embedding_deployment_name     = var.cognitive_model_embedding_deployment_name
  cognitive_model_embedding_name                = var.cognitive_model_embedding_name
  cognitive_model_embedding_version             = var.cognitive_model_embedding_version
  cognitive_model_embedding_deployment_sku_name = var.cognitive_model_embedding_deployment_sku_name
  aif_hub_name                                  = var.aif_hub_name
  aif_project_name                              = var.aif_project_name
  source                                        = "./modules/openai"
}

