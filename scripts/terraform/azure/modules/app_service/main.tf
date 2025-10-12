locals {
  webapp_name = "${var.app_name}-web"
}

data "azurerm_role_definition" "acr_pull" {
  name  = "AcrPull"
  scope = var.container_registry_id
}

resource "azurerm_linux_web_app" "app" {
  name                = local.webapp_name
  resource_group_name = var.resource_group_name
  location            = var.resource_group_location
  service_plan_id     = var.app_service_plan_id

  https_only = true

  identity { type = "SystemAssigned" }

  site_config {
    always_on                               = true
    minimum_tls_version                     = "1.2"
    container_registry_use_managed_identity = true

    dynamic "application_stack" {
      for_each = var.container_repository != null && var.container_image_tag != null ? [1] : []
      content {
        docker_image_name   = "${var.container_registry_login_server}/${var.container_repository}:${var.container_image_tag}"
        docker_registry_url = "https://${var.container_registry_login_server}"
      }
    }
  }

  app_settings = merge(
    {
      WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
      WEBSITES_PORT                       = tostring(var.container_port)
      WEBSITES_CONTAINER_START_TIME_LIMIT = "600"
    },
    var.app_insights_connection_string != null ? {
      APPLICATIONINSIGHTS_CONNECTION_STRING = var.app_insights_connection_string
    } : {},
    var.app_service_app_settings
  )
}

resource "azurerm_role_assignment" "acr_pull_to_app" {
  scope              = var.container_registry_id
  role_definition_id = data.azurerm_role_definition.acr_pull.id
  principal_id       = azurerm_linux_web_app.app.identity[0].principal_id
  depends_on         = [azurerm_linux_web_app.app]
}

resource "azurerm_linux_web_app_slot" "slot" {
  count          = var.app_service_enable_slot ? 1 : 0
  name           = var.app_service_slot_name
  app_service_id = azurerm_linux_web_app.app.id

  site_config {
    always_on                               = true
    minimum_tls_version                     = "1.2"
    container_registry_use_managed_identity = true
    application_stack {
      docker_image_name   = "${var.container_registry_login_server}/${var.container_repository}:${var.container_image_tag}"
      docker_registry_url = "https://${var.container_registry_login_server}"
    }
  }

  app_settings = merge(
    {
      WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
      WEBSITES_PORT                       = tostring(var.container_port)
      SLOT_NAME                           = var.app_service_slot_name
    },
    var.app_insights_connection_string != null ? {
      APPLICATIONINSIGHTS_CONNECTION_STRING = var.app_insights_connection_string
    } : {},
    var.app_service_app_settings
  )
}
