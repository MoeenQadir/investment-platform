# API Contracts & Specifications

This document defines the API contracts, data structures, and business rules for the Investment Research Platform.

## Run Statuses

- `QUEUED`: Run created, awaiting processing
- `RUNNING`: Currently being processed
- `COMPLETED`: Successfully completed
- `COMPLETED_WITH_WARNINGS`: Completed but with warnings (e.g., unsupported holdings skipped)
- `FAILED`: Run failed with error

## API Endpoints

### Portfolio Endpoints

#### POST /api/portfolio
Create a new portfolio.

**Request:**
```json
{
  "name": "My Portfolio"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "My Portfolio",
  "user_id": 1
}
```

#### GET /api/portfolio/{portfolio_id}
Get portfolio details.

#### POST /api/portfolio/{portfolio_id}/holdings
Bulk upsert holdings.

**Request:**
```json
[
  {
    "ticker_symbol": "AAPL",
    "marketplace": "US",
    "exchange": "NASDAQ",
    "quantity": 10,
    "buy_date": "2024-01-01",
    "buy_price": 180.00,
    "broker": "Demo Broker",
    "currency": "USD"
  }
]
```

#### GET /api/portfolio/{portfolio_id}/holdings
List all holdings in a portfolio.

### Research Endpoints

#### POST /api/research/run
Trigger a deep research run.

**Request:**
```json
{
  "portfolio_id": 1,
  "preferences": {},
  "strategy": "default"
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "status": "QUEUED"
}
```

### Explain Endpoints

#### POST /api/explain/run
Trigger an explanation run.

**Request:**
```json
{
  "portfolio_id": 1,
  "trigger_type": "PRICE_MOVE",
  "trigger_payload": {}
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "status": "QUEUED"
}
```

### Runs Endpoints

#### GET /api/runs
List runs with optional filters.

**Query Parameters:**
- `type`: RESEARCH | EXPLAIN
- `status`: QUEUED | RUNNING | COMPLETED | COMPLETED_WITH_WARNINGS | FAILED
- `portfolio_id`: integer

#### GET /api/runs/{run_id}
Get run details.

### Webhook Endpoints (n8n → API)

#### POST /api/webhooks/n8n/complete
Mark a run as completed.

**Request:**
```json
{
  "run_id": "uuid",
  "status": "COMPLETED",
  "warnings": {},
  "metrics_json": {},
  "report_md": "# Report...",
  "sources": [
    {
      "title": "Source Title",
      "url": "https://example.com"
    }
  ]
}
```

#### POST /api/webhooks/n8n/fail
Mark a run as failed.

**Request:**
```json
{
  "run_id": "uuid",
  "error_type": "ERROR_TYPE",
  "message": "Error message",
  "partial_metrics_json": {}
}
```

## Driver Scoring Formula

### Market Driver Score
```
base = min(1, abs(r_SPY) / 0.015)
align = 1.0 if sign(r_stock) == sign(r_SPY) else 0.3
score_market = base * align
```

### Sector Driver Score
```
base = min(1, abs(r_sector_etf) / 0.02)
align = 1.0 if sign(r_stock) == sign(r_sector_etf) else 0.3
score_sector = base * align
```

### Filings Driver Score
```
recency = 1.0 if <=3d, 0.7 if <=7d, 0.4 if <=14d else 0
delta_flag = 0.5 (v1 placeholder)
score_filings = recency * delta_flag
```

### Insider Driver Score
```
recency = 1.0 if <=3d, 0.7 if <=7d, 0.4 if <=14d else 0
intensity_factor = 1.0 if exists else 0
score_insider = recency * intensity_factor
```

### Flow/Technical Driver Score
```
score_flow_technical = min(1, abs(r_stock) / (2 * σ_stock))
```

### Dynamic Driver Count
```
strong = count(scores >= 0.6)
medium = count(0.4 <= score < 0.6)
driver_count = 5 if (strong >= 4) OR (strong >= 3 AND medium >= 2) else 3
```

## Price Move Detection

A price move event is triggered when:
```
|r_t| >= 2σ
```
where:
- `r_t` = today's daily return
- `σ` = 60-trading-day volatility of daily returns

## Provider Symbol Rules

### US Market
- `provider_symbol = ticker_symbol`

### India Market (Future)
- NSE: `provider_symbol = ticker_symbol.NS`
- BSE: `provider_symbol = ticker_symbol.BO`

