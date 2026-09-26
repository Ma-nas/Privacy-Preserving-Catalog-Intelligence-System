variable "project_id" {
  description = "The GCP Project ID"
  type        = string
  default     = "catalog-intelligence-prod"
}

variable "region" {
  description = "GCP deployment region"
  type        = string
  default     = "us-central1"
}

variable "db_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-custom-2-7680"
}

variable "redis_memory_size_gb" {
  description = "Redis Memorystore capacity in GB"
  type        = number
  default     = 2
}
