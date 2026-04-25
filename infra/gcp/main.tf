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

data "google_project" "project" {
  project_id = var.project_id
}

locals {
  # Cloud Run default runtime SA when template.service_account is unset.
  cloud_run_api_sa = (
    var.cloud_run_api_service_account_email != ""
    ? var.cloud_run_api_service_account_email
    : "${data.google_project.project.number}-compute@developer.gserviceaccount.com"
  )
}

resource "google_storage_bucket" "artifacts" {
  name                        = var.artifact_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_sql_database_instance" "cloud_sql" {
  name             = var.db_instance_name
  region           = var.region
  database_version = "POSTGRES_15"

  deletion_protection = var.db_deletion_protection

  settings {
    tier = var.db_tier

    ip_configuration {
      ipv4_enabled = var.db_public_ipv4_enabled
      ssl_mode     = var.db_ssl_mode
    }

    backup_configuration {
      enabled = var.db_backup_enabled
    }
  }
}

resource "google_cloud_tasks_queue" "jobs" {
  count = var.manage_cloud_tasks_queue ? 1 : 0

  name     = var.tasks_queue_name
  location = var.region
}

resource "google_secret_manager_secret" "anthropic" {
  secret_id = "anthropic-primary"

  replication {
    auto {}
  }
}

# Resend API key: create the secret and secret versions outside Terraform, then set
# resend_secret_id to that secret's id. Grants the API Cloud Run runtime SA read access.
data "google_secret_manager_secret" "resend" {
  count     = var.resend_secret_id != "" ? 1 : 0
  secret_id = var.resend_secret_id
}

resource "google_secret_manager_secret_iam_member" "api_resend_accessor" {
  count     = var.resend_secret_id != "" ? 1 : 0
  secret_id = data.google_secret_manager_secret.resend[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.cloud_run_api_sa}"
}

# Cloud Run services (cih-api-prod, cih-worker-prod) are deployed via
# `gcloud run deploy` + cloud/cloudbuild.*.yaml, not Terraform. Keeping them out of
# this module avoids fighting the deploy tool over env vars, secret mounts, CloudSQL
# connectors, and the tasks-invoker SA. See infra/gcp/README.md.
