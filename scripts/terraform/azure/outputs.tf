output "AZURE_OPENAI_ENDPOINT" {
  value     = module.openai.AZURE_OPENAI_ENDPOINT
  sensitive = true
}

output "AZURE_OPENAI_ACCOUNT_ID" {
  value     = module.openai.AZURE_OPENAI_ACCOUNT_ID
  sensitive = true
}

output "AZURE_OPENAI_CHAT_DEPLOYMENT" {
  value = module.openai.AZURE_OPENAI_CHAT_DEPLOYMENT
}

output "AZURE_OPENAI_CHAT_MODEL_NAME" {
  value = module.openai.AZURE_OPENAI_CHAT_MODEL_NAME
}

output "AZURE_OPENAI_CHAT_API_VERSION" {
  value = module.openai.AZURE_OPENAI_CHAT_API_VERSION
}

