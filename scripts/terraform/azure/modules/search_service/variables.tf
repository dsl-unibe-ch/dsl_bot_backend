#------- Global --------
variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "resource_group_location" { type = string }

# ----- Search Service -----

variable "search_service_name" {
  description = "Azure AI Search service name (lowercase, letters/digits, 2-60 chars)."
  type        = string
}

variable "search_service_sku" {
  description = "Search SKU: free, basic, standard, standard2, standard3, storage_optimized_l1, storage_optimized_l2."
  type        = string
  default     = "basic"
}

variable "search_service_replica_count" {
  description = "Number of replicas (affects query throughput/SLAs)."
  type        = number
  default     = 1
}

variable "search_service_partition_count" {
  description = "Number of partitions (affects index size & ingestion throughput)."
  type        = number
  default     = 1
}


variable "grant_blob_reader_to_storage_account_id" {
  description = "If set, grants Search MSI 'Storage Blob Data Reader' on this Storage Account ID."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply."
  type        = map(string)
  default     = {}
}

# Optional: create a basic index
variable "search_index_name" {
  description = "If set, creates a basic index with 'id' and 'content' fields."
  type        = string
  default     = null
}