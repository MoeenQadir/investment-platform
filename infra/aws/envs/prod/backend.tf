terraform {
  # Configure S3 + DynamoDB backend before `terraform init`.
  # backend "s3" {
  #   bucket         = "investment-research-tfstate-prod"
  #   key            = "envs/prod/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "investment-research-tfstate-lock"
  #   encrypt        = true
  # }
}
