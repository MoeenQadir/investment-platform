# Infrastructure

| Path | Purpose |
|------|---------|
| `local/` | Docker Compose for local dev + n8n workflows |
| `aws/`   | Terraform for cloud deployment (see `aws/README.md`) |

## Local

```sh
docker compose -f infra/local/docker-compose.yml up --build
```

## AWS

See `infra/aws/README.md`. Skeleton — populate as milestones land.
