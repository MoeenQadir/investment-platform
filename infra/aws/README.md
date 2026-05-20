# AWS Infrastructure (Terraform)

Skeleton populated per HLD §8 / Part 8. Modules are placeholders — implement as each
HLD milestone is delivered.

## Layout

```
infra/aws/
  modules/                  # Reusable modules (one per AWS resource group)
    vpc/                    # VPC, subnets, NAT, route tables
    ecs_cluster/            # ECS cluster (Fargate)
    ecs_service/            # Per-service task def + service
    ecr/                    # Container registry per service
    kinesis_stream/         # raw-* / norm-* / bars-* streams
    kinesis_firehose/       # S3 archival (market-raw, edgar-raw)
    rds_postgres/           # RDS Postgres + TimescaleDB + pgvector
    elasticache_redis/      # Redis (cache.r7g.large)
    alb/                    # Application Load Balancer
    acm/                    # TLS certificates
    route53/                # DNS records
    waf/                    # WAF rules
    cloudwatch_observability/ # Dashboards, alarms, log groups
    iam_roles/              # Task roles, GitHub Actions OIDC
    secrets/                # Secrets Manager entries
    pgvector/               # pgvector extension setup scripts
  envs/
    dev/                    # Dev environment root
    prod/                   # Prod environment root
```

## Initial bootstrap (per env)

```sh
cd envs/dev

# 1. Configure backend (S3 + DynamoDB) — see backend.tf comment.
# 2. Provide credentials (use AWS SSO / OIDC, not static keys).

cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

## HLD milestone mapping

| Milestone | Modules to populate |
|-----------|---------------------|
| M0 | vpc, ecs_cluster, ecr, rds_postgres, elasticache_redis, alb, secrets, iam_roles |
| M1 | kinesis_stream, kinesis_firehose, ecs_service (ingest, normalizer, aggregator, api, ws-gateway) |
| M2 | pgvector setup, NLP service ecs_service |
| M3 | cloudwatch_observability, waf, route53, acm |
