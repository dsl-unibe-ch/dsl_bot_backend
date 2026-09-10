# Azure API Management instance
resource "azurerm_api_management" "apim" {
  name                = var.apim_name
  location            = var.resource_group_location
  resource_group_name = var.resource_group_name
  publisher_name      = var.publisher_name
  publisher_email     = var.publisher_email
  sku_name = var.apim_sku_name
  tags = var.tags
}

# Define the DSL Bot API
resource "azurerm_api_management_api" "bot_api" {
  name                = var.api_name
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision            = var.api_revision
  display_name        = var.api_display_name
  path                = var.api_path
  protocols           = var.api_protocols
  service_url         = var.backend_url
  
  subscription_required = var.subscription_required
}

# Operation 1: Health check
resource "azurerm_api_management_api_operation" "health" {
  operation_id        = "health-check"
  api_name            = azurerm_api_management_api.bot_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Health Check"
  method              = "GET"
  url_template        = "/health"
  
  response {
    status_code = 200
    description = "Success"
  }
}

# Operation 2: Initialize agent
resource "azurerm_api_management_api_operation" "initialize_agent" {
  operation_id        = "initialize-agent"
  api_name            = azurerm_api_management_api.bot_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Initialize Agent"
  method              = "GET"
  url_template        = "/initialize-agent"
  
  response {
    status_code = 200
    description = "Success"
  }
}

# Operation 3: Invoke agent
resource "azurerm_api_management_api_operation" "invoke_agent" {
  operation_id        = "invoke-agent"
  api_name            = azurerm_api_management_api.bot_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Invoke Agent"
  method              = "POST"
  url_template        = "/invoke-agent"
  
  response {
    status_code = 200
    description = "Success"
  }
}

# Operation 4: Send feedback
resource "azurerm_api_management_api_operation" "send_feedback" {
  operation_id        = "send-feedback"
  api_name            = azurerm_api_management_api.bot_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Send Feedback"
  method              = "POST"
  url_template        = "/send-feedback"
  
  response {
    status_code = 200
    description = "Success"
  }
}

# Policy 1: Health check - No rate limit (for monitoring)
resource "azurerm_api_management_api_operation_policy" "health_policy" {
  api_name            = azurerm_api_management_api.bot_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  operation_id        = azurerm_api_management_api_operation.health.operation_id

  xml_content = <<XML
<policies>
    <inbound>
        <base />
        <cors allow-credentials="false">
          <allowed-origins>
            <origin>*</origin>
          </allowed-origins>
          <allowed-methods>
            <method>GET</method>
            <method>POST</method>
            <method>OPTIONS</method>
          </allowed-methods>
          <allowed-headers>
            <header>*</header>
          </allowed-headers>
        </cors>
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>
XML
}

# Policy 2: Initialize agent 
resource "azurerm_api_management_api_operation_policy" "initialize_policy" {
  api_name            = azurerm_api_management_api.bot_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  operation_id        = azurerm_api_management_api_operation.initialize_agent.operation_id

  xml_content = <<XML
<policies>
    <inbound>
        <base />
        <cors allow-credentials="true">
          <allowed-origins>
            <origin>${var.frontend_url}</origin>
          </allowed-origins>
          <allowed-methods>
            <method>GET</method>
            <method>POST</method>
            <method>OPTIONS</method>
          </allowed-methods>
          <allowed-headers>
            <header>*</header>
          </allowed-headers>
        </cors>
        <rate-limit-by-key calls="${var.initialize_rate_limit_calls}" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
        <quota-by-key calls="${var.initialize_quota_calls}" renewal-period="86400" counter-key="@(context.Request.IpAddress)" />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
</policies>
XML
}

# Policy 3: Invoke agent - STRICT limit (expensive OpenAI calls)
resource "azurerm_api_management_api_operation_policy" "invoke_policy" {
  api_name            = azurerm_api_management_api.bot_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  operation_id        = azurerm_api_management_api_operation.invoke_agent.operation_id

  xml_content = <<XML
<policies>
    <inbound>
        <base />
        <cors allow-credentials="true">
          <allowed-origins>
            <origin>${var.frontend_url}</origin>
          </allowed-origins>
          <allowed-methods>
            <method>GET</method>
            <method>POST</method>
            <method>OPTIONS</method>
          </allowed-methods>
          <allowed-headers>
            <header>*</header>
          </allowed-headers>
        </cors>
        <rate-limit-by-key calls="${var.invoke_rate_limit_calls}" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
        <quota-by-key calls="${var.invoke_quota_calls}" renewal-period="86400" counter-key="@(context.Request.IpAddress)" />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
</policies>
XML
}

# Policy 4: Send feedback 
resource "azurerm_api_management_api_operation_policy" "feedback_policy" {
  api_name            = azurerm_api_management_api.bot_api.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  operation_id        = azurerm_api_management_api_operation.send_feedback.operation_id

  xml_content = <<XML
<policies>
    <inbound>
        <base />
        <cors allow-credentials="true">
          <allowed-origins>
            <origin>${var.frontend_url}</origin>
          </allowed-origins>
          <allowed-methods>
            <method>GET</method>
            <method>POST</method>
            <method>OPTIONS</method>
          </allowed-methods>
          <allowed-headers>
            <header>*</header>
          </allowed-headers>
        </cors>
        <rate-limit-by-key calls="${var.feedback_rate_limit_calls}" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
        <quota-by-key calls="${var.feedback_quota_calls}" renewal-period="86400" counter-key="@(context.Request.IpAddress)" />
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
</policies>
XML
}
