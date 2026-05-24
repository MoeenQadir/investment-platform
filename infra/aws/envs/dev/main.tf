terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Configure remote state in backend.tf
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = "dev"
      Project     = "investment-research-platform"
      ManagedBy   = "terraform"
    }
  }
}

# Module wiring will go here.
# Skeleton — populate as services are introduced (see HLD Part 8 / Milestone roadmap).
