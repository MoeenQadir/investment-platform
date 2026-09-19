# AlphaLens — Investment Research & Explanation Platform

A production-grade monorepo for agentic investment research workflows with a Next.js dashboard, FastAPI backend, PostgreSQL database, and n8n orchestration.

## Architecture Overview

- **Frontend (`/apps/web`)**: Next.js 14 App Router - calls ONLY the FastAPI backend
- **Backend (`/apps/api`)**: FastAPI - system of record, handles ALL deterministic finance calculations
- **Orchestration (`/infra/local/n8n`)**: n8n workflows - orchestrates steps and uses LLM only for narrative synthesis
- **Database**: PostgreSQL with Alembic migrations

## Quick Start

### Prerequisites
- Docker & Docker Compose (install Docker Desktop for Mac)
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Running with Docker Compose

```bash
# Build and start all services
docker compose -f infra/local/docker-compose.yml up --build

# Services will be available at:
# - Web: http://localhost:3000
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - n8n: http://localhost:5678
# - PostgreSQL: localhost:5432
```

### Initial Setup

1. **Start the database and run migrations:**
```bash
# Start only postgres first
docker compose -f infra/local/docker-compose.yml up postgres -d

# Run migrations (using Python 3.11 - required for pandas compatibility)
cd apps/api
python3.11 -m venv venv  # Use python3.11 or python3.12 (Python 3.14 not supported)
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_data.py
```

**Note:** If you're using Python 3.14, you'll need to use Python 3.11 or 3.12 instead. You can install Python 3.11 with: `brew install python@3.11`

2. **Import n8n workflow:**
   - Access n8n at http://localhost:5678
   - Import workflow from `infra/local/n8n/workflows/research-workflow.json`

3. **Start all services:**
```bash
docker compose -f infra/local/docker-compose.yml up
```

### Sample End-to-End Run

1. Access the web app at http://localhost:3000
2. Create a portfolio (e.g., "Demo Portfolio")
3. Add holdings:
   - Ticker: AAPL, Marketplace: US, Exchange: NASDAQ, Quantity: 10, Buy Date: 2024-01-01, Buy Price: 180.00
   - Ticker: MSFT, Marketplace: US, Exchange: NASDAQ, Quantity: 5, Buy Date: 2024-01-15, Buy Price: 350.00
4. Click "Run Deep Research" to trigger a research run
5. Monitor the run status on the dashboard or `/runs/[id]` page
6. View the completed report once status is COMPLETED

## Project Structure

```
.
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── infra/
│   ├── local/             # Docker Compose + n8n workflows
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.prod.yml
│   │   └── n8n/workflows/
│   └── aws/               # Terraform (modules + envs/dev|prod)
│       ├── modules/
│       └── envs/
├── docs/
│   └── CONTRACTS.md  # API contracts and specifications
├── AGENTS.md         # Architecture rules for agents
└── README.md         # This file
```

## Development

### Frontend (Next.js)
```bash
# Make sure you're in the project root first
cd ~/investment-research-platform/apps/web
pnpm install  # Install pnpm first if needed: npm install -g pnpm
pnpm dev
```

### Backend (FastAPI)
```bash
cd apps/api
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
# Make sure PostgreSQL is running locally
export DATABASE_URL="postgresql://investment_user:investment_pass@localhost:5432/investment_db"
alembic upgrade head
python scripts/seed_data.py
uvicorn app.main:app --reload
```

### Running Tests

**API Tests:**
```bash
cd apps/api
pytest
```

**Frontend Typecheck:**
```bash
cd apps/web
pnpm typecheck
```

## Architecture Rules

See `AGENTS.md` for detailed architecture rules. Key principles:

1. Frontend NEVER calls n8n directly - only FastAPI
2. Backend does ALL deterministic finance calculations
3. n8n orchestrates workflows and uses LLM only for narrative synthesis
4. All runs store `holdings_snapshot_json` for reproducibility

## API Documentation

Interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

See `docs/CONTRACTS.md` for detailed contract specifications.

## Hosting n8n Workflow

### Quick Start (Local Development)

1. **Start n8n:**
```bash
docker compose -f infra/local/docker-compose.yml up n8n -d
```

2. **Access n8n UI:**
   - Open http://localhost:5678
   - Login: username `admin`, password `admin`

3. **Import workflow:**
   - Click "Workflows" → "Import from File"
   - Select `infra/local/n8n/workflows/research-workflow.json`
   - Click "Save" and "Activate" (toggle in top right)

4. **Get webhook URL:**
   - Open the imported workflow
   - Click the "Research Webhook" node
   - Copy the webhook URL (e.g., `http://localhost:5678/webhook/research-start`)
   - This URL is what your API calls to trigger the workflow

### Production Hosting Options

#### Option A: Same Server (Docker Compose) - Recommended for MVP

**Setup:**
```bash
# Set environment variables
export N8N_HOST=yourdomain.com
export N8N_PROTOCOL=https
export WEBHOOK_URL=https://yourdomain.com:5678
export N8N_WEBHOOK_URL=https://yourdomain.com:5678/webhook/research-start

# Deploy
docker compose -f infra/local/docker-compose.yml -f infra/local/docker-compose.prod.yml up -d
```

**Configure reverse proxy (nginx) for n8n:**
```nginx
server {
    listen 443 ssl;
    server_name n8n.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5678;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Option B: n8n Cloud (Easiest, Paid)

1. Sign up at https://n8n.io/cloud
2. Create a new workflow
3. Import `infra/local/n8n/workflows/research-workflow.json`
4. Get your webhook URL from n8n Cloud
5. Update `N8N_WEBHOOK_URL` in your API environment variables

**Pros:** No server management, automatic updates, reliable
**Cons:** Monthly cost (~$20-50/month)

#### Option C: Dedicated Server/VPS

**Requirements:**
- 2GB+ RAM
- Docker installed
- Domain name (optional but recommended)

**Setup:**
```bash
# Create docker-compose file for n8n only
cat > docker-compose.n8n.yml << EOF
version: '3.8'
services:
  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=your_username
      - N8N_BASIC_AUTH_PASSWORD=your_secure_password
      - N8N_HOST=yourdomain.com
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://yourdomain.com:5678
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=your_db_host
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=investment_db
      - DB_POSTGRESDB_USER=investment_user
      - DB_POSTGRESDB_PASSWORD=your_db_password
    volumes:
      - n8n_data:/home/node/.n8n
volumes:
  n8n_data:
EOF

# Start n8n
docker compose -f docker-compose.n8n.yml up -d
```

### Important Configuration Notes

1. **Webhook URL Format:**
   - Local: `http://localhost:5678/webhook/research-start`
   - Docker network: `http://n8n:5678/webhook/research-start`
   - Production: `https://yourdomain.com/webhook/research-start`

2. **Update API Configuration:**
   - Set `N8N_WEBHOOK_URL` environment variable in your API service
   - Must match the webhook URL from your n8n instance

3. **Workflow Activation:**
   - **CRITICAL:** Workflows must be **Activated** (toggled ON) in n8n UI
   - Inactive workflows won't respond to webhooks

4. **Security:**
   - Change default `admin/admin` credentials in production
   - Use HTTPS in production
   - Consider IP whitelisting for webhook endpoints

### Troubleshooting n8n

**Workflow not triggering?**
- Check workflow is **Activated** (green toggle in n8n UI)
- Verify webhook URL matches `N8N_WEBHOOK_URL` in API
- Check n8n logs: `docker compose -f infra/local/docker-compose.yml logs n8n`

**Can't access n8n UI?**
- Verify n8n is running: `docker compose -f infra/local/docker-compose.yml ps`
- Check port 5678 is not blocked by firewall
- Try accessing via IP instead of localhost

**Webhook timeout errors?**
- Increase timeout in API code (currently 5 seconds)
- Check network connectivity between API and n8n
- Verify n8n has enough resources (CPU/RAM)

## How It Works

### Data Flow

```
User Action (Frontend)
    ↓
FastAPI Backend (creates run record)
    ↓
n8n Webhook (triggers workflow)
    ↓
n8n Workflow:
    ├─→ FastAPI (for metrics/compute)
    ├─→ LLM (for narrative synthesis only)
    └─→ FastAPI Webhook (complete/fail)
    ↓
Frontend (polls for status updates)
```

### Research Run Flow

1. User triggers "Run Deep Research" from frontend
2. Frontend calls `POST /api/research/run` with portfolio_id
3. Backend creates run record with status `QUEUED`
4. Backend calls n8n webhook to trigger workflow
5. n8n workflow:
   - Calls FastAPI to get portfolio metrics
   - FastAPI calculates returns, volatility, sector exposure
   - FastAPI calculates driver scores (market, sector, filings, insider, technical)
   - FastAPI determines dynamic driver count (3 or 5 based on strong/medium scores)
   - n8n calls LLM with calculated metrics to generate narrative report
   - n8n calls FastAPI webhook to mark run as `COMPLETED` with report
6. Frontend polls `GET /api/runs/{run_id}` to check status
7. When `COMPLETED`, frontend displays report and metrics

### Driver Scoring System

- **Market Driver**: Based on SPY correlation and alignment
- **Sector Driver**: Based on sector ETF correlation and alignment
- **Filings Driver**: Based on recency of SEC filings (3d, 7d, 14d thresholds)
- **Insider Driver**: Based on recency of insider trading activity
- **Flow/Technical Driver**: Based on price move relative to volatility (2σ threshold)

## Deployment Guide

### Deploying the Frontend on Vercel

The repo is pre-configured for Vercel via `vercel.json` (it points at `apps/web`):

1. Push this repository to GitHub.
2. In Vercel, import the repo. It will auto-detect the project from `vercel.json`.
3. No build overrides needed — the default Next.js build runs with `npm ci`.
4. Add the environment variables from `.env.example` (Clerk keys + `NEXT_PUBLIC_API_URL` pointing at your hosted FastAPI backend).
5. Set the domain to your chosen `*.vercel.app` name, e.g. `alphalens-research.vercel.app`.

> The FastAPI backend, PostgreSQL and n8n must be hosted separately (Docker Compose, Railway, Render, Fly.io, etc.). See the services below.

### Where to Deploy

#### Development Environment
- **Local Machine**: Use Docker Compose for full stack
- **Services**:
  - Web: `http://localhost:3000`
  - API: `http://localhost:8000`
  - n8n: `http://localhost:5678`
  - PostgreSQL: `localhost:5432`

#### Production Deployment Options

**Option 1: Single Server (Recommended for MVP)**
- **Platform**: AWS EC2, DigitalOcean Droplet, or similar VPS
- **Requirements**: 4GB+ RAM, 2+ CPU cores, Docker & Docker Compose
- **Deployment**: Use docker-compose.yml with production configurations
- **Access**: Configure domain with reverse proxy (nginx/traefik)

**Option 2: Container Orchestration (Recommended for Scale)**
- **Platform**: AWS ECS, Google Cloud Run, Azure Container Instances, Kubernetes
- **Services**: Container registry → Cloud Run/ECS
- **Database**: Managed PostgreSQL (AWS RDS, Google Cloud SQL, Azure Database)

**Option 3: Serverless (Frontend Only)**
- **Frontend**: Vercel, Netlify, or AWS Amplify
- **Backend**: AWS Lambda + API Gateway, or keep FastAPI on container
- **Database**: Managed PostgreSQL

### Production Deployment Steps

#### Step 1: Prepare Environment Variables

**Backend (.env in apps/api/):**
```env
DATABASE_URL=postgresql://user:pass@db-host:5432/investment_db
N8N_WEBHOOK_URL=http://n8n-host:5678/webhook
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**Frontend (.env.local in apps/web/):**
```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

#### Step 2: Deploy with Docker Compose (Single Server)
```bash
# Set environment variables
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export NEXT_PUBLIC_API_URL="https://api.yourdomain.com"
export CORS_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"

# Deploy
docker compose -f infra/local/docker-compose.yml -f infra/local/docker-compose.prod.yml up -d --build
```

#### Step 3: Configure Reverse Proxy (nginx example)
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Deployment Fixes Applied

The following deployment issues were identified and fixed:

### 1. Web Dockerfile Issues
**Fixed:**
- Updated to use `pnpm` with fallback to `npm` if pnpm-lock.yaml doesn't exist
- Added multi-stage build with `development`, `build`, and `production` targets
- Properly configured for Next.js standalone output
- Production stage uses minimal runtime with only necessary files

### 2. CORS Configuration
**Fixed:**
- Made CORS origins configurable via `CORS_ORIGINS` environment variable
- Supports multiple origins (comma-separated)
- Defaults to `http://localhost:3000` for backward compatibility
- Updated docker-compose.yml to include both localhost and container network origins

### 3. Docker Compose Container Networking
**Fixed:**
- Added `CORS_ORIGINS` to API service with both localhost and container network origins
- Created `docker-compose.prod.yml` for production overrides
- Better container networking configuration

### 4. API Dockerfile
**Fixed:**
- Created multi-stage Dockerfile with `development` and `production` targets
- Added system dependencies (gcc, postgresql-client) in base stage
- Production stage removes development dependencies
- Development stage includes `--reload` flag, production doesn't

### 5. Production Configuration
**Fixed:**
- Created `docker-compose.prod.yml` override file
- Removed volume mounts in production (uses built images)
- Removed `--reload` flag in production
- Added environment variable placeholders with defaults

## Configuration

### Environment Variables

**Backend (apps/api):**
- `DATABASE_URL`: PostgreSQL connection string
- `N8N_WEBHOOK_URL`: n8n webhook endpoint URL
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins (default: `http://localhost:3000`)

**Frontend (apps/web):**
- `NEXT_PUBLIC_API_URL`: Backend API URL (must start with `NEXT_PUBLIC_` for client-side access)

**n8n (infra/local/docker-compose.yml):**
- `N8N_BASIC_AUTH_USER`: Basic auth username (default: `admin`)
- `N8N_BASIC_AUTH_PASSWORD`: Basic auth password (default: `admin`)
- `DB_POSTGRESDB_HOST`: PostgreSQL host
- `DB_POSTGRESDB_DATABASE`: Database name
- `DB_POSTGRESDB_USER`: Database user
- `DB_POSTGRESDB_PASSWORD`: Database password

### Database Configuration
- Default database: `investment_db`
- Default user: `investment_user`
- Default password: `investment_pass` (**CHANGE IN PRODUCTION!**)

## Monitoring & Maintenance

### Health Checks
- API: `GET http://localhost:8000/` should return `{"message": "Investment Research API"}`
- Database: `docker exec investment-postgres pg_isready -U investment_user`
- n8n: Access http://localhost:5678 and verify login

### Logs
```bash
# View all logs
docker compose -f infra/local/docker-compose.yml logs -f

# View specific service logs
docker compose -f infra/local/docker-compose.yml logs -f api
docker compose -f infra/local/docker-compose.yml logs -f web
docker compose -f infra/local/docker-compose.yml logs -f n8n
```

### Database Migrations
```bash
cd apps/api
source venv/bin/activate
alembic upgrade head  # Apply latest migrations
alembic downgrade -1  # Rollback one migration
```

### Database Backups
```bash
# Add to crontab
0 2 * * * docker exec investment-postgres pg_dump -U investment_user investment_db > /backups/db_$(date +\%Y\%m\%d).sql
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Kill processes on ports 3000, 8000, 5432, 5678
2. **Database connection errors**: Verify PostgreSQL is running and DATABASE_URL is correct
3. **CORS errors**: Update `CORS_ORIGINS` environment variable in docker-compose.yml or API service
4. **n8n workflow not triggering**: Verify N8N_WEBHOOK_URL is correct and workflow is active
5. **Frontend can't reach API**: Check `NEXT_PUBLIC_API_URL` environment variable

### Testing Builds

**Test Development Build:**
```bash
cd apps/web
docker build -t investment-web:dev --target development .
docker run -p 3000:3000 investment-web:dev
```

**Test Production Build:**
```bash
cd apps/web
docker build -t investment-web:prod --target production .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 investment-web:prod
```

**Test API CORS:**
```bash
docker run -p 8000:8000 \
  -e CORS_ORIGINS="http://localhost:3000,https://example.com" \
  investment-api:latest
```

## Security Considerations

1. **Change default passwords** in production
2. **Use HTTPS** in production (SSL/TLS certificates)
3. **Restrict database access** to application servers only
4. **Implement authentication** for API endpoints (not currently implemented)
5. **Use secrets management** (AWS Secrets Manager, HashiCorp Vault) for sensitive data
6. **Regular security updates** for Docker images and dependencies

## Scaling Considerations

- **Database**: Use connection pooling (PgBouncer) for high concurrency
- **API**: Add load balancer and multiple API instances
- **Frontend**: Use CDN for static assets (Vercel handles this automatically)
- **n8n**: Consider n8n Cloud or dedicated instance for reliability
- **Caching**: Add Redis for frequently accessed data

#   i n v e s t m e n t - p l a t f o r m  
 