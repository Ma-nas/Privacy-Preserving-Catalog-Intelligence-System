terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Dedicated VPC & Private Service Access
resource "google_compute_network" "vpc_network" {
  name                    = "catalog-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "catalog-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc_network.id
}

resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# 2. Cloud SQL (PostgreSQL 15+) with Private IP and RLS Support
resource "google_sql_database_instance" "postgres_instance" {
  name             = "catalog-postgres-instance"
  database_version = "POSTGRES_15"
  region           = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier              = var.db_tier
    availability_type = "REGIONAL"
    disk_size         = 50
    disk_type         = "PD_SSD"

    ip_configuration {
      ipv4_enabled    = false # Non-negotiable rule: No public IP exposure
      private_network = google_compute_network.vpc_network.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }

    database_flags {
      name  = "cloudsql.enable_pgaudit"
      value = "on"
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "catalog_db" {
  name     = "catalog_db"
  instance = google_sql_database_instance.postgres_instance.name
}

# 3. Memorystore Redis
resource "google_redis_instance" "redis_cache" {
  name               = "catalog-redis"
  tier               = "STANDARD_HA"
  memory_size_gb     = var.redis_memory_size_gb
  region             = var.region
  authorized_network = google_compute_network.vpc_network.id
  redis_version      = "REDIS_7_0"

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

# 4. Serverless VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  name          = "catalog-vpc-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc_network.name
}

# 5. Cloud Run Service: ML Classification Microservice
resource "google_cloud_run_v2_service" "ml_classification" {
  name     = "ml-classification-service"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 20
    }
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }
    containers {
      image = "gcr.io/${var.project_id}/ml-classification:latest"
      resources {
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
      }
    }
  }
}

# 6. Cloud Run Service: ML Description Microservice
resource "google_cloud_run_v2_service" "ml_description" {
  name     = "ml-description-service"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 20
    }
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }
    containers {
      image = "gcr.io/${var.project_id}/ml-description:latest"
      resources {
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
      }
    }
  }
}

# 7. Cloud Run Service: FastAPI Gateway
resource "google_cloud_run_v2_service" "catalog_api" {
  name     = "catalog-api-gateway"
  location = var.region

  template {
    scaling {
      min_instance_count = 1
      max_instance_count = 30
    }
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "ALL_TRAFFIC"
    }
    containers {
      image = "gcr.io/${var.project_id}/catalog-api:latest"
      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "CLASSIFICATION_SERVICE_URL"
        value = google_cloud_run_v2_service.ml_classification.uri
      }
      env {
        name  = "DESCRIPTION_SERVICE_URL"
        value = google_cloud_run_v2_service.ml_description.uri
      }
    }
  }
}
