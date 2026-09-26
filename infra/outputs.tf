output "postgres_private_ip" {
  description = "The private IP address of the Cloud SQL PostgreSQL instance"
  value       = google_sql_database_instance.postgres_instance.private_ip_address
}

output "redis_host" {
  description = "The IP address of the Memorystore Redis instance"
  value       = google_redis_instance.redis_cache.host
}

output "api_gateway_url" {
  description = "The Cloud Run URL of the Catalog API Gateway"
  value       = google_cloud_run_v2_service.catalog_api.uri
}

output "classification_service_url" {
  description = "The Cloud Run URL of the ML Classification microservice"
  value       = google_cloud_run_v2_service.ml_classification.uri
}

output "description_service_url" {
  description = "The Cloud Run URL of the ML Description microservice"
  value       = google_cloud_run_v2_service.ml_description.uri
}
