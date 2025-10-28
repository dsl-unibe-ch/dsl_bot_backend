terraform {
  required_version = "= 1.13.3"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.47.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 1.13.0"
    }

  }
}

