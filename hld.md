# Investment Research Platform — Enhanced HLD & Infrastructure Review

> **Scope**: This document reads the current GitHub repo state against the HLD and Infrastructure-first plan, identifies every gap, error, and weak concept, and delivers an enhanced, corrected version of both documents. All section numbers map back to the originals so you can diff.

---

## Part 0 — Situational summary (read first)

### What the repo actually is today

The repo is a **portfolio research tool**: users add holdings (ticker, quantity, buy date/price), click "Run Deep Research," and a FastAPI backend scores each holding on five driver dimensions (Market, Sector, Filings, Insider, Flow/Technical), then calls n8n to orchestrate an LLM narrative report. Data comes from **yfinance** — free, delayed, no real-time tick stream.

### What the old HLD described

A **real-time market data platform**: live NYSE tick ingestion from a paid vendor, Kafka/Kinesis backbone, OHLCV aggregation, WebSocket broadcaster, news crawler + FinBERT NLP, vector search, and a Next.js UI with live charts and sentiment overlays.

### What this revised plan now targets

A staged portfolio research platform:

1. **Phase 1 — Reliability ($0 infra/vendor target)**: add auth, replace yfinance-backed Filings and Insider drivers with SEC EDGAR, add server-side external-call caching, and keep n8n for research workflow orchestration.
2. **Phase 2 — Narrow live data ($0 vendor target)**: add a watchlist-scoped live market path using a free/developer market-data provider only for a small aggregated symbol set, vendor aggregate bars, and a minimal live quote/chart validation page.
3. **Phase 3 — Scale when justified**: add paid market-data plans, broad-symbol display entitlements, Kinesis or another streaming backbone, news/NLP beyond SEC filings, and higher concurrency infrastructure only after real demand exists.

### The core tension

These are **two different products** at very different maturity levels. The HLD does not acknowledge the existing repo at all — there is no migration path, no decision about what happens to n8n, no mapping of existing FastAPI routes to the new API service, and no acknowledgment that yfinance is the current data source.

This document resolves that tension and corrects every technical error before you build further.

---

## Part 1 — Critical errors (fix before anything else)

### Error 1 — Kinesis is premature for Phase 1/2 (Infra §10)

**As written**: "4 shards for `raw-nyse-*`" targeting 50 k msg/s, later corrected to a larger hand-tuned shard plan.

**Why it's wrong now**: the updated product path is watchlist-scoped, not full-universe raw-tick ingestion. For <50 symbols in an MVP, Kinesis adds fixed cost and operational complexity before there are multiple independent consumers or meaningful fan-out pressure. If Kinesis is eventually needed, the shard math still matters: each Kinesis shard handles 1 MB/s write throughput. A normalized trade event is ~250–350 bytes (Protobuf). At 300 bytes/event:

```
Max events/s per shard = 1,000,000 / 300 ≈ 3,333 events/s
50,000 events/s ÷ 3,333 = ~15 shards required
```

Add 20% headroom for bursts → **18–20 shards minimum** for `raw-nyse-ticks` at 50 k msg/s. The 4-shard figure will saturate immediately under NYSE open conditions.

**Fix**: Defer Kinesis entirely until Phase 3. In Phase 2, use a single provider WS connection feeding FastAPI in-process pub/sub or a small asyncio queue, then write vendor aggregate bars directly to Postgres/Timescale. If Phase 3 needs a streaming backbone, use Kinesis on-demand first and move to explicit shard tuning only after observed traffic requires it.

---

### Error 2 — Redis instance is undersized for the WebSocket claim (Infra §10)

**As written**: `cache.t4g.small` (2 vCPU, 1.37 GB) for the broadcaster, with the HLD claiming 50 k concurrent WebSocket connections.

**Why it's wrong**: Each WebSocket subscriber maintains a subscription in Redis pub/sub. At 50 k connections subscribing to ~10 symbols each on average, you have 500 k active subscriptions. Redis pub/sub memory overhead per channel subscriber is ~150–200 bytes; message fan-out at 50 k msgs/s write through a 1.37 GB node will saturate CPU and memory. `t4g.small` is a dev/test instance.

**Fix**: Do not introduce Redis for Phase 1. In Phase 2, the broadcaster should maintain its own in-process subscription registry. Add Redis only when multiple broadcaster replicas require shared hot state or cross-replica pub/sub. 50 k concurrent connections is a future scale target requiring multiple broadcaster replicas and load-balancer design, not an MVP default.

---

### Error 3 — "60 fps" is a gaming target, not a financial charting target (HLD §4.14)

**As written**: "smooth 60fps updates" as a frontend NFR.

**Why it's wrong**: Candlestick charts on financial platforms update at 1–5 fps for level 1 data. Even the most aggressive trading UIs (Bloomberg Terminal, TradingView) render at 10–20 fps. At 60 fps you're spending GPU budget on re-rendering unchanged chart frames. The browser's requestAnimationFrame is 60 fps but your WebSocket data doesn't arrive at 60 fps — you're just re-painting the same data.

**Fix**: NFR should be "chart re-render latency ≤ 100 ms from WebSocket message receipt; animation at 30 fps during live updates." Use a frame-throttle on the chart update loop.

---

### Error 4 — NLP throughput and latency NFRs are conflated (HLD §4.12)

**As written**: "≥ 50 docs/s with batching; latency < 500 ms per doc on GPU"

**Why it's wrong**: These are two different measurement axes. If you process 50 docs/s in a batch pipeline, individual docs may wait in queue for seconds before processing starts — 500 ms single-doc latency and 50 docs/s batch throughput cannot be guaranteed simultaneously unless you have a real-time path (priority queue for breaking news) and a bulk path (backfill/historical). Conflating them in one NFR creates an impossible target.

**Fix**: Split into two NFRs:
- Batch (backfill/historical): throughput ≥ 50 docs/s at p50 latency.
- Real-time (breaking news): single-doc latency p95 < 5 s (from crawl to sentiment result).

---

### Error 5 — WebSocket broadcaster and WebSocket gateway are duplicate components (HLD §4.8 and §4.10)

**As written**: Section 4.8 defines a "real-time broadcaster" (Node.js WS/SSE consuming from bus, fanout per symbol). Section 4.10 defines a "WebSocket gateway" (authenticated WS entrypoint, multiplex subscriptions, edge termination). These are the same service described twice with slightly different emphases.

**Fix**: Collapse into one component: **WS Gateway / Broadcaster**. Responsibilities: auth (JWT validation at connection), subscription multiplexing, provider-event fanout, backpressure, and horizontal scaling. In Phase 2 it can be FastAPI WebSockets or a small Node WS service fed by in-process pub/sub. Add Redis/Kinesis only when there are multiple broadcaster replicas or multiple consumers that justify them.

---

### Error 6 — n8n is orphaned (repo → HLD mismatch)

The existing repo has a fully built n8n workflow that orchestrates research runs: FastAPI creates a run → calls n8n webhook → n8n calls FastAPI for driver metrics → calls Claude for narrative → calls FastAPI webhook to mark COMPLETED.

The HLD does not mention n8n at all. The HLD's Kinesis + Flink approach replaces the streaming bus but does not address what happens to the existing synchronous research-run workflow, which is not a streaming problem — it's a task orchestration problem.

**Fix**: The architecture should explicitly define two separate orchestration layers:
1. **Lightweight event processing** (FastAPI background tasks / asyncio queue in Phase 1-2; Kinesis or Kafka only in Phase 3): for live quote fanout and aggregate bar persistence.
2. **Task orchestration** (n8n, or migrate to Temporal/Prefect if you outgrow n8n): for research run workflows that are async, multi-step, and involve LLM calls.

n8n stays for task orchestration in Phase 1 and beyond. If it becomes a bottleneck, migrate to Temporal. Do not conflate stream processing with task orchestration.

---

### Error 7 — The existing FastAPI is not mapped to the new API service (HLD §4.9)

The repo's FastAPI already has routes for portfolios, holdings, research runs, and driver scoring. The HLD defines a new API service for market data endpoints (`/v1/symbols`, `/v1/candles`, `/v1/compare`, etc.). There is no decision about whether these are:

- The same service (all routes in one FastAPI instance)
- Separate services (portfolio API vs market data API)
- A unified API gateway routing to both

**Fix**: Define the service boundary explicitly (see Part 2 below).

---

### Error 8 — Market-data vendor choice is over-specified too early (HLD §4.1)

**As written**: "Connect to market data vendor, subscribe to symbols."

**Why it's a critical gap**: real-time public-display market data requires a licensed feed and entitlement model. Vendor tables and free-tier claims are easy to misread, and pricing/display rights change over time. Do not anchor the MVP architecture to an unverified vendor tier.

| Vendor | Latency | Cost/month | Notes |
|---|---|---|---|
| Vendor class | Fit | Decision |
|---|---|---|
| SEC EDGAR | Authoritative public filings/fundamentals | Use immediately for filings, insider activity, and Company Facts |
| yfinance | Development-only price fallback | Keep behind non-public/dev paths; do not rely on it for public deploy |
| Alpaca/Polygon/etc. | Live quotes/bars | Evaluate in Phase 2/3 based on display rights, free-symbol caps, and current docs |
| FMP/Alpha Vantage/Twelve Data | Supplemental fundamentals/calendars | Skip for MVP unless a specific product gap remains after EDGAR Company Facts |

**Fix**: Phase 1 does not need a market-data vendor signup. Phase 2 starts with a narrow watchlist-scoped live path and a provider abstraction. Phase 3 chooses paid Alpaca SIP, Polygon, or another licensed feed only when symbol caps or display requirements justify it.

---

### Error 9 — Auth is mentioned but never designed (HLD §9)

**As written**: "JWT or API keys; per-user rate limiting; WS token validation."

**Why it's a critical gap**: Auth is not a one-line bullet. It affects every component: API rate limiting requires a user identity, WS connections require token validation at handshake, n8n research runs need to be scoped to a user's portfolio, the frontend needs a login flow.

**Fix**: Define the auth stack before building anything user-facing:
- **Provider**: Auth0, Clerk, or AWS Cognito (recommended for AWS-native stack).
- **Flow**: User logs in → receives JWT → passes JWT as `Authorization: Bearer` header on REST calls and as a query param on WS handshake (`?token=...`).
- **WS validation**: At connection time, validate JWT; store `userId` in the connection context for subscription scoping.
- **API gateway**: WAF + rate limiting by `userId` extracted from JWT.
- **Existing repo**: The FastAPI backend currently has **no auth at all** (noted as a security gap in README). Add auth before any public deployment.

---

## Part 2 — Weak concepts and design improvements

### Weak concept 1 — Missing market hours handling

No component in the HLD addresses market hours. The ingestion service will receive no data on weekends, US federal holidays, or outside NYSE hours (9:30 AM–4:00 PM ET). The system needs:

- A **market calendar service** or library (e.g., `exchange_calendars` Python package) that each service queries to determine if markets are open.
- The ingestion service should emit a `market_open` / `market_closed` event so downstream consumers (broadcaster, aggregator) can handle state transitions gracefully.
- The frontend should show a "Market closed" badge and display last close data when the market is closed.
- The aggregator's watermark strategy must account for the overnight gap (bar at 4:00 PM closes cleanly; no late events should arrive after ~4:05 PM ET).

---

### Weak concept 2 — No historical backfill strategy

When the system is first deployed, the time-series DB is empty. Users will immediately try to load 30-day or 1-year candles and see no data. The HLD does not define a backfill job.

**Fix**: Add a **Backfill Service** as part of Phase 2 deliverables:
- On startup (or on demand), fetch historical OHLCV from the vendor's REST API (most vendors offer historical bars back 2–5 years on standard plans).
- Write vendor aggregate bars directly to the time-series DB.
- Track per-symbol backfill status in Postgres so restarts are idempotent.
- Backfill current watchlist symbols and benchmarks first; do not backfill the full S&P 500 until a broader market-data product exists.

---

### Weak concept 3 — Corporate actions handling is mentioned but not designed

HLD §4.1 mentions "corp-action rules from reference data" and §4.3 mentions "adjust for corp actions if needed for real-time." This is vague. A stock split (e.g., NVDA 10:1 split) makes all historical prices incomparable to post-split prices without adjustment.

**Fix**: Define the corp action policy:
- For **historical display**: use split-adjusted prices from the vendor's adjusted endpoint. Most vendors serve pre-adjusted candles. Set `adjusted=true` on bar records accordingly.
- For **real-time ticks**: pass through unadjusted; the frontend should query adjusted historical bars and display an annotation on the day of the split.
- The `corp_actions` table in Postgres should be populated by a daily reference sync job.

---

### Weak concept 4 — Vector search latency target is aggressive without index tuning details

HLD §4.13: "p95 < 150 ms for top-20 results."

With millions of news embeddings (1536-dimensional vectors from OpenAI or similar), an exact k-NN search is O(n × d) per query — this will not achieve 150 ms without proper approximate nearest neighbor (ANN) indexing. The HLD does not specify:

- Which ANN algorithm (HNSW, IVF-PQ, ScaNN)?
- What index parameters (ef_construction, M for HNSW)?
- Recall/latency tradeoff policy?

**Fix**: Use **pgvector with HNSW index** in Phase 3 (simple, no new infra). At millions of vectors HNSW p95 < 100 ms is achievable with `m=16, ef_construction=64`. If you scale to 100 M+ vectors or need multi-tenant isolation, migrate to OpenSearch k-NN at that point. Add index tuning details to the data model section.

---

### Weak concept 5 — The comparison API is underspecified

HLD §7.1: `GET /v1/compare?symbols=AAPL,MSFT&metric=returns&window=30d`

The existing repo already has a driver scoring system that computes returns and benchmark correlations. The HLD's comparison endpoint overlaps with this but is designed from scratch without referencing or extending it. Questions left unanswered:

- What is "returns" normalized to? (percent change from window start? log returns? cumulative?)
- What happens when the two symbols have different trading days (e.g., one had a halt)?
- How many symbols can be compared at once? (The query param implies unlimited.)

**Fix**: Extend the existing FastAPI endpoint rather than designing a parallel one. Cap the comparison at 5 symbols per request. Normalize to percent change from the first observation in the window. Return `null` for gaps (trading halts, missing data) and document this in the contract.

---

### Weak concept 6 — Frontend validation is sequenced too late

The old HLD sequences: M1 (infra + market data) → M2 (news + NLP) → M3 (frontend). But you cannot validate API SLOs without a client making real requests. Building a UI after the data infrastructure means infrastructure runs for months with no user feedback.

**Fix**: Bake a minimal Next.js page into Phase 2 exit criteria: live quote + 1-day 1-minute chart for one supported watchlist symbol. This validates the WS path, candles API, entitlement checks, and frontend framework before any broad market-data buildout.

---

### Weak concept 7 — ClickHouse vs TimescaleDB decision is deferred without criteria

The HLD says "preferred ClickHouse OR TimescaleDB" and the infra plan says "start with Timescale, revisit ClickHouse when tick-level history or very high query concurrency arrives." This is fine as a phased approach, but there are no criteria for when to migrate.

**Fix**: Define the migration trigger explicitly:
- **Stay on TimescaleDB if**: query concurrency stays below 200 req/s, tick history is not stored (only 1-minute+ bars), and operational simplicity is a priority.
- **Migrate to ClickHouse if**: tick-level storage is required, query concurrency exceeds 500 req/s, or you need sub-50 ms query response for columnar analytics (e.g., aggregate sentiment vs. price across 1000 symbols).

ClickHouse Cloud is the right choice if you go that route — self-hosting ClickHouse on ECS is operationally expensive.

---

### Weak concept 8 — Infra plan Terraform structure is missing key modules

The Terraform structure in Infra §9 is missing:

- `modules/opensearch/` or `modules/pgvector/` — for vector search
- `modules/waf_rules/` — the plan mentions WAF but has no module for it
- `modules/cloudfront/` — for frontend CDN (Next.js on Vercel is simpler, but if you want AWS-native CDN for the frontend, this is needed)
- `modules/codedeploy/` or `modules/ecs_service/` — for blue/green deployments mentioned in CI/CD section
- `modules/kinesis_analytics/` — Phase 3 only, if a managed Flink/raw-event path becomes justified

**Fix**: Add these modules to the structure. Also: the `infra/envs/dev` and `infra/envs/prod` layout conflicts with the current repo's `infra/` directory that already contains `docker-compose.yml` and n8n workflows. The repo's `infra/` needs to be restructured as `infra/local/` (Docker Compose for dev) and `infra/aws/` (Terraform for cloud).

---

### Weak concept 9 — No data licensing compliance mechanism

HLD §9 mentions "ensure vendor license for display/redistribution; retain raw ticks per TOS." The infra plan has no concrete mechanism to enforce this.

**Fix**: Add to infra plan:
- Treat non-SEC vendor data as licensed data by default. Do not store, display, or redistribute it beyond the vendor's allowed use.
- Add `data_class: LicensedMarketData` tags to market-data resources once any vendor feed is enabled.
- Document vendor TOS requirements in `docs/DATA_LICENSING.md` before any public display surface ships. Avoid embedding pricing/free-tier assumptions in architecture docs; link to vendor docs instead.
- The API service must check entitlements before serving real-time data (`data_tier=delayed|realtime`) and must refuse real-time display to users without the right entitlement.
- SEC EDGAR content is treated separately as public filing data and remains the preferred source for filings, insider transactions, and standardized fundamentals.

---

## Part 3 — Enhanced architecture (revised)

### Revised product definition

This platform has two product surfaces, but they are delivered in phases rather than as a full real-time data platform up front:

**Surface A — Portfolio Research Engine** (existing, repo-complete):
- User manages a portfolio of holdings.
- System scores each holding on 5 driver dimensions.
- Phase 1 replaces yfinance-backed Filings and Insider drivers with SEC EDGAR.
- yfinance remains a development-only fallback for price/market/sector paths until a licensed market-data provider is selected.
- n8n orchestrates a multi-step research run that calls Claude for a narrative report.
- Output: a structured research report with driver scores and narrative.

**Surface B — Watchlist-Scoped Market Data** (to be built after Phase 1):
- Users maintain a watchlist derived from holdings and explicit symbol additions.
- A narrow live feed covers the aggregated active watchlist plus benchmark symbols (`SPY`, `QQQ`, sector ETFs).
- Vendor aggregate bars are written directly to Postgres/Timescale; no raw-tick pipeline in Phase 1-2.
- WebSocket fanout serves live quotes/charts only for entitled users and supported symbols.
- Output: minimal live quote and intraday chart first; comparison/sentiment later.

**Shared infrastructure**:
- PostgreSQL (Surface A: portfolios, runs, seed data. Surface B: reference data, news).
- FastAPI (unified API — add `/v1/market/*` routes to existing FastAPI rather than a second service).
- Next.js frontend (add market data pages alongside existing portfolio pages).
- Auth (add to both surfaces simultaneously).

---

### Revised data flow (corrected)

```
┌─────────────────────────────────────────────────────────────┐
│                     SURFACE A — Portfolio Research          │
│  User → Next.js → FastAPI → n8n → FastAPI → Claude → DB    │
│       (Phase 1: EDGAR for filings/insider; yfinance dev-only│
│        fallback for prices until licensed market data)       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     SURFACE B — Market Data                 │
│                                                             │
│  Aggregated watchlist symbols                               │
│       │                                                     │
│       ▼                                                     │
│  Provider WS / REST bars ──► FastAPI background task        │
│       │                         │                           │
│       │                         ├── in-process pub/sub      │
│       │                         └── Postgres/Timescale bars │
│       │                                                     │
│       ▼                                                     │
│  WS Gateway / FastAPI WebSocket ──► entitled clients        │
│                                      │                      │
│                              FastAPI (unified)              │
│                           /v1/market/* + existing routes    │
│                                      │                      │
│                              Next.js (unified)              │
│                         Market pages + Portfolio pages      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     SURFACE B.2 — News + Sentiment          │
│  RSS/APIs → Crawler → Postgres(news) → NLP Service          │
│  (ECS Fargate)          (ECS Fargate)  (FinBERT / ECS)      │
│                                              │              │
│                                      pgvector index         │
│                                      (same Postgres)        │
│                                              │              │
│                              FastAPI /v1/news/* /v1/sentiment/* │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 4 — Enhanced component specs (corrected)

### §4.1 Market-data provider adapter (corrected)

**Change**: Do not name a paid vendor for Phase 1. Keep a provider abstraction and defer the paid-feed decision until Phase 2/3 after display rights, symbol caps, and current vendor terms are verified.

**Phase 1 prerequisites**:
- SEC EDGAR client for filings, insider transactions, and Company Facts.
- `MARKET_DATA_PROVIDER` abstraction for dev-only price fallback.
- Entitlement model in the database before any public real-time display.

**Phase 2 prerequisites**:
- Watchlist model that caps the aggregate live symbol universe.
- Provider adapter for a small live-symbol set.
- Explicit licensing decision documented in `docs/DATA_LICENSING.md`.

**Corrected NFR**:
- Phase 1 reliability: EDGAR sync jobs are idempotent, rate-limited, and retry 429/503 responses.
- Phase 2 live path: p95 < 2 s provider-to-browser for supported watchlist symbols; no full-market latency SLO.
- Reconnect: exponential backoff with jitter; emit an operational warning after repeated provider reconnect failures.

**Add**: Market calendar check on startup. The live provider connector should not attempt market-hours streaming on non-trading days. Use `exchange_calendars` (Python) or provider market-clock endpoints.

---

### §4.5 Aggregators (corrected)

**Change**: Ditch Flink and raw-tick aggregation for Phase 1-2. Start with vendor aggregate bars.
1. Fetch or subscribe to vendor-provided bars for watchlist symbols.
2. Write directly to Postgres/TimescaleDB via upsert on `(symbol, interval, ts)`.
3. Use provider timestamps and simple idempotent writes; do not build watermarking until raw events are actually stored.

**Migrate to a raw-event aggregator** only in Phase 3 if product requirements need tick replay, sub-second bars, or multiple independent downstream consumers.

---

### §4.8 / §4.10 WS Gateway + Broadcaster (merged, corrected)

**Single component spec**:
- **Tech**: Phase 2 can use FastAPI WebSockets or Node.js (`ws`) depending on frontend/API ergonomics. Use one replica first; add ALB sticky sessions only when horizontal scale is needed.
- **Auth**: On WS upgrade request, validate JWT from query param `?token=...`. Reject unauthenticated connections with HTTP 401.
- **Subscription**: Client sends `{"action":"subscribe","symbols":["AAPL","MSFT"]}`. Server registers the subscription in an in-process Map (not Redis for first version).
- **Fan-out**: Consume provider events from FastAPI in-process pub/sub or a small internal queue. For each event, fan out to all connections subscribed to that symbol.
- **Backpressure**: If a client's WS send queue depth exceeds 100 messages, drop the oldest and emit a `{"type":"backpressure_warning"}` message.
- **Scaling**: Add Redis pub/sub only when you have more than 1 broadcaster replica. Add Kinesis only when at least 3 independent consumers need replay/fan-out.
- **NFR (corrected)**: Support a small internal beta in Phase 2; 5 k and 50 k concurrent connections are Phase 3 scale targets.

---

### §4.9 API service (clarified)

**Decision**: Extend the existing FastAPI, do not create a second service.

Add these route groups to the existing FastAPI `app/routers/`:
- `market.py` — `/v1/symbols`, `/v1/quotes/latest`, `/v1/candles`
- `compare.py` — `/v1/compare` (max 5 symbols, percent-change normalized)
- `news.py` — `/v1/news/:symbol`, `/v1/sentiment/:symbol`

The existing `portfolios.py`, `research.py`, `runs.py` routes remain unchanged.

**Add cache read path**: Phase 1 uses Postgres-backed 24h TTL for EDGAR/provider REST calls. Phase 2 may use in-memory or Redis hot-state cache for latest quotes. Redis is not mandatory until multiple API/broadcaster replicas need shared quote state.

---

## Part 5 — Enhanced data model (additions)

### New tables required (not in original HLD)

```sql
-- Watchlist-scoped live universe
CREATE TABLE watchlists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  symbol TEXT NOT NULL,
  source TEXT NOT NULL CHECK(source IN ('holding','manual','benchmark')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX ON watchlists (user_id, symbol);

-- Backfill tracking
CREATE TABLE backfill_jobs (
  symbol TEXT PRIMARY KEY,
  exchange TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','running','completed','failed')),
  from_date DATE,
  to_date DATE,
  last_bar_ts TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market calendar (populated by reference sync job)
CREATE TABLE market_holidays (
  exchange TEXT NOT NULL,
  date DATE NOT NULL,
  name TEXT,
  PRIMARY KEY (exchange, date)
);

-- Data entitlements (for licensing compliance)
CREATE TABLE user_entitlements (
  user_id UUID REFERENCES users(id),
  data_tier TEXT NOT NULL CHECK(data_tier IN ('delayed','realtime')),
  granted_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id)
);
```

### Corrected TimescaleDB hypertable definitions

```sql
-- Candles (replace generic candles_1m definition)
CREATE TABLE candles (
  symbol TEXT NOT NULL,
  interval TEXT NOT NULL CHECK(interval IN ('1s','1m','5m','1h')),
  ts TIMESTAMPTZ NOT NULL,
  open DOUBLE PRECISION,
  high DOUBLE PRECISION,
  low DOUBLE PRECISION,
  close DOUBLE PRECISION,
  volume BIGINT,
  vwap DOUBLE PRECISION,
  trades INTEGER,
  adjusted BOOLEAN DEFAULT false,
  PRIMARY KEY (symbol, interval, ts)
);

SELECT create_hypertable('candles', 'ts');

-- Partition by month (default TimescaleDB chunk interval)
-- Add per-symbol index for fast symbol+interval+time range queries
CREATE INDEX ON candles (symbol, interval, ts DESC);
```

---

## Part 6 — Enhanced API contracts (corrected)

### Corrected comparison endpoint

```
GET /v1/compare?symbols=AAPL,MSFT,GOOGL&interval=1d&window=30d

Constraints:
- Max 5 symbols per request
- window: 1d, 5d, 1m, 3m, 6m, 1y, 5y
- interval: 1m (intraday only), 5m, 1h, 1d

Response:
{
  "window": "30d",
  "interval": "1d",
  "series": {
    "AAPL": [
      {"ts": 1712767200000, "pct_change": 0.0, "price": 180.5},
      {"ts": 1712853600000, "pct_change": 1.24, "price": 182.7}
    ],
    "MSFT": [...],
    "GOOGL": null  // null if symbol not found or no data for window
  },
  "correlation": {
    "AAPL_MSFT": 0.87,
    "AAPL_GOOGL": null,
    "MSFT_GOOGL": null
  },
  "adjusted": true
}
```

### WebSocket message schema (corrected)

```json
// Client → Server: subscribe
{"action": "subscribe", "symbols": ["AAPL", "MSFT"]}

// Client → Server: unsubscribe
{"action": "unsubscribe", "symbols": ["AAPL"]}

// Server → Client: trade event
{"type": "trade", "symbol": "AAPL", "ts": 1712767200123, "price": 189.23, "size": 100}

// Server → Client: 1-second bar
{"type": "bar_1s", "symbol": "AAPL", "ts": 1712767200000, "o": 189.1, "h": 189.5, "l": 188.9, "c": 189.2, "v": 45230}

// Server → Client: market status change
{"type": "market_status", "exchange": "NYSE", "status": "open|closed|pre|post", "ts": 1712767200000}

// Server → Client: error / backpressure
{"type": "error", "code": "BACKPRESSURE", "message": "Message queue full, events dropped"}
```

---

## Part 7 — Enhanced milestone plan (resequenced)

### Phase 1 (2–3 weeks) — Reliability and SEC EDGAR
**Deliverables**:
- Add auth to existing FastAPI and Next.js. Clerk is the fastest default unless AWS-native Cognito is required.
- Add `user_entitlements.data_tier` before any public market-data display.
- SEC EDGAR ingestion:
  - `company_tickers.json` daily CIK/ticker sync.
  - Submissions API filing index into `filings`.
  - Form 4 XML parser into insider transaction rows.
  - Company Facts API into standardized fundamental facts.
- Replace yfinance-backed Filings and Insider drivers with EDGAR-backed DB lookups.
- Keep yfinance only as a development fallback for price/market/sector data until a licensed market-data source is selected.
- Add Postgres-backed 24h TTL cache for all external REST calls.
- Keep n8n for task orchestration; do not replace it with a streaming system.

**Exit criteria**:
- A logged-in user can create a portfolio and run a research run.
- Filings and Insider driver scores use EDGAR-backed tables, not yfinance scrapes.
- EDGAR sync is idempotent, rate-limited, and covered by tests.
- No paid vendor dependency blocks local/dev operation.

---

### Phase 2 (3–4 weeks) — Narrow live market data
**Deliverables**:
- Watchlist model: `watchlists(user_id, symbol, source, created_at)`.
- Aggregate active watchlist symbols across logged-in users plus benchmarks (`SPY`, `QQQ`, sector ETFs).
- Provider adapter for a small supported symbol set. Verify current provider terms before enabling public display.
- Single provider WS connection or REST polling loop feeding FastAPI in-process pub/sub.
- Vendor aggregate bars direct to Postgres/TimescaleDB; no raw-tick path.
- Backfill job: load historical bars only for watchlist symbols and benchmarks.
- FastAPI market routes: `/v1/symbols`, `/v1/quotes/latest`, `/v1/candles`.
- WS path: FastAPI WebSockets or Node WS gateway for entitled users.
- Reference sync job (daily): sector mappings, market holidays, supported symbol metadata.
- Minimal frontend validation page: live quote + 1-day 1-minute candlestick chart for one selected symbol.

**Exit criteria**:
- Live quote events visible in frontend within 2 s of provider delivery for supported symbols.
- `/v1/candles/AAPL?interval=1m&start=...&end=...` p95 < 150 ms for 30-day window.
- WS p99 fanout latency < 1 s under internal beta load.
- Aggregate live symbol count is capped and observable.
- Public display is blocked unless entitlement and vendor rights are confirmed.

---

### Phase 3 — Scale when justified
**Deliverables**:
- Paid live data if free/developer symbol caps are exhausted: evaluate Alpaca SIP, Polygon, or another licensed provider using current vendor docs.
- Kinesis on-demand or another streaming backbone only when at least 3 independent consumers need fan-out/replay.
- Aggregator for raw events only if vendor aggregate bars no longer meet product needs.
- Redis shared hot-state cache when multiple WS/API replicas require it.
- Load testing and entitlement enforcement for broad-symbol display.
- `/v1/compare` endpoint (5-symbol max, percent-change normalized).
- News crawler after SEC 8-K/filing text analysis proves useful; start with SEC text, then add RSS/news vendors.
- NLP service: FinBERT sentiment, entity extraction, embedding generation.
- pgvector index on filing/news embeddings (HNSW, m=16).
- `/v1/news/:symbol`, `/v1/sentiment/:symbol` endpoints.

**Exit criteria**:
- Sentiment series for AAPL updated within 10 minutes of article publish.
- `/v1/sentiment/AAPL?interval=1h` covers last 7 days.
- Comparison view works for 5 symbols in the frontend.

---

### Phase 4 — Full frontend + observability
**Deliverables**:
- Full Next.js market data pages: symbol search, live candlestick chart (TradingView Lightweight Charts), volume bars, last price display.
- Comparison view: overlaid normalized returns, correlation metric, interval toggle.
- Sentiment panel: article feed with sentiment badges, sentiment trend line, auto-updating summary paragraph (generated by Claude via FastAPI).
- OpenTelemetry collector sidecar on all ECS services.
- CloudWatch dashboards: ECS CPU/mem, API p95, WS connection count, external-provider error rate, NLP throughput.
- Alerts routed to Slack + PagerDuty.
- Load test: WS fanout under 10 k concurrent clients.

**Exit criteria**:
- Smooth chart updates at 30 fps during NYSE market hours.
- All CloudWatch alarms green under normal load.
- WS p99 < 500 ms under 10 k concurrent load test.

---

### Phase 5 (future) — Scale to 50 k WS and India markets
- Scale WS gateway to 50 k concurrent (Redis pub/sub layer, ≥3 replicas).
- Add India NSE/BSE support (schema already designed for it in repo).
- ClickHouse migration for tick-level storage (if warranted by usage metrics).
- EKS migration (if ECS/Fargate becomes a bottleneck for custom scheduling needs).

---

## Part 8 — Corrected infrastructure plan (delta from original)

### §3 Compute (corrected)

Keep ECS Fargate as written. Add explicit service list for M1:

| Service | CPU | Memory | Replicas | Spot? |
|---|---|---|---|---|
| edgar-cik-sync | 256 | 512 | scheduled | Yes |
| edgar-filing-sync | 256 | 512 | 1 | Yes |
| edgar-form4-parser | 256 | 512 | 1 | Yes |
| company-facts-sync | 256 | 512 | scheduled | Yes |
| live-provider-adapter | 512 | 1024 | 1 | No (Phase 2) |
| api (FastAPI) | 1024 | 2048 | 2 | Partial |
| ws-gateway | 512 | 1024 | 1 to start | No (latency sensitive) |
| backfill-worker | 512 | 1024 | 1 (job, not always-on) | Yes |
| news-crawler | 512 | 1024 | 1 | Yes |
| nlp-service | 2048 | 4096 | 1–2 | No (GPU optional) |

---

### §4 Streaming backbone (deferred)

No streaming backbone is required in Phase 1-2. Use a DB-backed job table for EDGAR work and FastAPI in-process pub/sub or a small internal queue for narrow live quotes.

Add Kinesis on-demand in Phase 3 only when:
- at least 3 independent consumers need the same event stream,
- replay is required for correctness/debugging,
- or a single-process queue becomes a measured bottleneck.

If explicit shard tuning is eventually required, use observed event size and throughput rather than pre-allocating raw NYSE stream shards.

---

### §5 Datastores (corrected)

**RDS Postgres + TimescaleDB**:
- Instance: `db.r6g.large` as written. ✓
- Enable TimescaleDB extension only when Phase 2 market bars are implemented; plain Postgres is enough for Phase 1 EDGAR.
- Add pgvector extension for news embeddings (saves you from running a separate vector DB in M1/M2).

**Redis**:
- Defer Redis until multiple API/WS replicas need shared hot quote state or cache state.
- Use Postgres-backed 24h TTL cache for EDGAR and external REST calls in Phase 1.

**Add missing S3 bucket**:
- `edgar-raw/`: cached SEC filing documents for reprocessing and NLP.
- `market-raw/`: Phase 3 only if raw vendor events are licensed for storage and replay.

---

### §9 Terraform structure (corrected)

```
infra/
  local/                        ← Move existing Docker Compose here
    docker-compose.yml
    docker-compose.prod.yml
    n8n/
      workflows/
  aws/                          ← New Terraform root
    modules/
      vpc/
      ecs_cluster/
      ecs_service/              ← New: service definition module
      ecr/
      kinesis_stream/           ← Phase 3 only
      kinesis_firehose/         ← Phase 3 only, for licensed raw-event archival
      rds_postgres/
      elasticache_redis/
      alb/
      acm/
      route53/
      waf/                      ← New: WAF rules module
      cloudwatch_observability/
      iam_roles/
      secrets/
      pgvector/                 ← New: pgvector setup scripts
    envs/
      dev/
        main.tf
        variables.tf
        backend.tf
        terraform.tfvars
      prod/
        main.tf
        variables.tf
        backend.tf
        terraform.tfvars
```

---

### §13 Acceptance checks (additions)

Add to the original list:
- **Auth**: A request with an invalid JWT to `/v1/candles/AAPL` returns HTTP 401.
- **Market hours**: Live provider adapter does not stream on a Saturday; clients receive a market-closed status and last known close.
- **Data entitlements**: A user with `data_tier=delayed` receives quotes that are ≥15 minutes old; a user with `data_tier=realtime` receives quotes within 2 s.
- **Backfill**: `backfill_jobs` table shows `status=completed` for watchlist symbols and benchmarks after Phase 2 deployment; `/v1/candles/AAPL?interval=1m` returns available cached history.
- **EDGAR compliance**: SEC requests include a configured User-Agent and remain at or below 10 req/s per IP.

---

## Part 9 — Fundamental data pipeline (SEC EDGAR first)

This entire pipeline was missing from the original HLD. It is the ground truth source for the three data types that power the Filings Driver and Insider Driver in the existing portfolio research engine. Replacing yfinance with this pipeline is required before any public deployment — yfinance is a scraper with no commercial ToS, no SLA, and no reliability guarantee.

---

### Why SEC EDGAR is the right primary source

The SEC mandates that all public US companies file electronically. Every 10-K, 10-Q, 8-K, and Form 4 arrives on EDGAR first — every commercial data vendor (Bloomberg, Refinitiv, FactSet) simply re-sells this data with formatting and normalization on top. Going direct to EDGAR means:

- No vendor dependency for filing data
- No cost (the API is free and has no commercial restrictions)
- Ground truth — the exact document as filed, with no intermediary transformation
- Real-time via RSS feed (filings appear on EDGAR within minutes of SEC acceptance)

EDGAR is the default source for Phase 1. It avoids vendor signup, display-rights complexity, and low request limits from supplemental APIs. Use Company Facts/XBRL before adding any commercial fundamentals provider.

---

### §4.17 — Fundamental data pipeline (new component)

#### 4.17.1 CIK ↔ Ticker mapping service

EDGAR identifies companies by CIK (Central Index Key), not ticker. Every other system uses ticker. The mapping must be built and kept fresh.

**Source**: `https://www.sec.gov/files/company_tickers.json` — a flat JSON file published by the SEC, updated daily, mapping CIK → ticker + company name for all ~10 k active filers.

**Process**:
- Download daily at 06:00 ET (before market open).
- Upsert into the `cik_ticker_map` Postgres table.
- This table is the join key for every downstream filing and insider query.

```sql
CREATE TABLE cik_ticker_map (
  cik         TEXT PRIMARY KEY,           -- zero-padded to 10 digits
  ticker      TEXT NOT NULL,
  name        TEXT NOT NULL,
  exchange    TEXT,                        -- NYSE, NASDAQ, OTC, etc.
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON cik_ticker_map (ticker);  -- primary lookup direction
```

**Rate limits**: The SEC asks for no more than 10 requests/second from a single IP. Include a `User-Agent` header with your org name and email (SEC requirement): `User-Agent: YourPlatform contact@yourdomain.com`.

---

#### 4.17.2 Filing sync service

**Purpose**: Maintain a near-real-time index of all SEC filings for tracked companies, classified by form type, with the filing URL so the NLP service can fetch the full document.

**Two operating modes**:

**Mode A — RSS real-time feed** (runs continuously during SEC operating hours, ~06:00–22:00 ET):

The SEC publishes an Atom RSS feed of all accepted filings, updated every 10 minutes:

```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent
  &type={FORM_TYPE}
  &dateb=&owner=include&count=40&output=atom
```

Poll this feed every 10 minutes for form types: `10-K`, `10-Q`, `8-K`, `4` (insider transactions), `SC 13G`, `SC 13D`.

For each new filing:
1. Extract CIK, form type, filed date, period of report, accession number.
2. Look up ticker via `cik_ticker_map`.
3. If the ticker is in the tracked universe, insert into `filings` and enqueue a DB-backed `filing.new` job for downstream parsing/NLP.

**Mode B — Historical backfill** (runs once on first deploy per symbol):

Use the EDGAR submissions API to pull all historical filings for a company:

```
https://data.sec.gov/submissions/{CIK_PADDED_10_DIGITS}.json
```

This returns a JSON object with `filings.recent` (last ~1000 filings inline) and `filings.files` (older filings in paginated files). Walk this to populate the full filing history.

**Tech**: Python ECS Fargate task. Two ECS task definitions — one always-on RSS poller, one one-shot backfill job triggered per symbol.

---

#### 4.17.3 Insider transaction parser (Form 4)

Form 4 is filed within 2 business days of an insider transaction. It is the primary source for the Insider Driver score.

**Source**: EDGAR full-text submission. Each Form 4 filing has an XML document at a predictable path inside the accession folder.

**Parsing approach**:

When the filing sync service inserts a new Form 4 filing, it enqueues a `filing.new` job. A dedicated Form 4 parser (lightweight worker, not the full NLP service) consumes this job and:

1. Fetches the XML from:
   ```
   https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION_NO_DASHES}/{PRIMARY_DOCUMENT}
   ```
2. Parses the `<nonDerivativeTransaction>` and `<derivativeTransaction>` XML nodes.
3. Extracts: insider name, title/role, transaction date, transaction type (P=purchase, S=sale, A=grant, D=disposition), shares transacted, price per share, shares owned after transaction.
4. Upserts into `insider_transactions` table.

**Key business logic**: Not all Form 4 transactions are signals. Filter out:
- Automatic grant/vesting transactions (type `A` from compensation plans) — these are noise.
- Transactions below a materiality threshold (e.g., < $10 k total value).
- Open-market purchases (type `P`) and open-market sales (type `S`) are the meaningful signals.

```sql
CREATE TABLE filings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker          TEXT NOT NULL,
  cik             TEXT NOT NULL REFERENCES cik_ticker_map(cik),
  form_type       TEXT NOT NULL,      -- '10-K', '10-Q', '8-K', '4', etc.
  filed_at        TIMESTAMPTZ NOT NULL,
  period_of_report DATE,
  accession_no    TEXT NOT NULL UNIQUE,
  document_url    TEXT,               -- direct link to primary document
  processed       BOOLEAN DEFAULT false,
  CONSTRAINT fk_cik FOREIGN KEY (cik) REFERENCES cik_ticker_map(cik)
);

CREATE INDEX ON filings (ticker, form_type, filed_at DESC);
CREATE INDEX ON filings (filed_at DESC);  -- for recency queries in driver scoring

CREATE TABLE insider_transactions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker            TEXT NOT NULL,
  cik               TEXT NOT NULL,
  filing_id         UUID REFERENCES filings(id),
  insider_name      TEXT NOT NULL,
  insider_title     TEXT,
  transaction_date  DATE NOT NULL,
  transaction_type  TEXT NOT NULL CHECK(transaction_type IN ('P','S','A','D','F','M','X','G','C','J')),
  is_open_market    BOOLEAN GENERATED ALWAYS AS (transaction_type IN ('P','S')) STORED,
  shares            BIGINT NOT NULL,
  price_per_share   NUMERIC(12,4),
  total_value       NUMERIC(18,2) GENERATED ALWAYS AS (shares * price_per_share) STORED,
  shares_owned_after BIGINT,
  filed_at          TIMESTAMPTZ NOT NULL
);

CREATE INDEX ON insider_transactions (ticker, transaction_date DESC);
CREATE INDEX ON insider_transactions (ticker, is_open_market, transaction_date DESC);
```

---

#### 4.17.4 SEC Company Facts — standardized historical fundamentals

SEC Company Facts provides standardized XBRL facts for public companies without a vendor key or display-rights burden. It replaces the previous FMP assumption for Phase 1.

**Data used from Company Facts**:

| Endpoint | Data | Used by |
|---|---|---|
| `/api/xbrl/companyfacts/CIK##########.json` | Revenue, net income, EPS, assets, liabilities, cash flow facts | Financial summary in research reports |
| SEC submissions metadata | Periods, filing dates, form types | Filing recency and report context |
| 8-K/10-Q/10-K documents | Qualitative disclosures | Narrative synthesis and later NLP |

**Sync strategy**: Pull Company Facts for each portfolio holding when a research run is triggered or during a daily watchlist sync. Cache normalized facts in Postgres for 24 hours. Earnings calendars, analyst estimates, and surprise data are not MVP-blocking and should not introduce a vendor dependency until a concrete product need exists.

```sql
CREATE TABLE company_facts_snapshots (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker          TEXT NOT NULL,
  cik             TEXT NOT NULL,
  taxonomy        TEXT NOT NULL,          -- us-gaap, dei, etc.
  concept         TEXT NOT NULL,          -- Revenues, NetIncomeLoss, EarningsPerShareDiluted
  unit            TEXT NOT NULL,          -- USD, shares, USD/shares
  fiscal_year     INTEGER,
  fiscal_period   TEXT,
  end_date        DATE,
  value_numeric   NUMERIC,
  source_accession_no TEXT,
  fetched_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (ticker, taxonomy, concept, unit, fiscal_year, fiscal_period, end_date)
);
```

---

#### 4.17.5 NLP service integration for filing documents

Once the filing sync service has indexed a new 10-K or 10-Q, the NLP service (already specified in §4.12) should additionally process the full document text, not just news articles. This is where the genuine analytical value lives — management discussion and analysis (MD&A), risk factor changes, forward guidance language.

**Processing steps for a 10-K/10-Q**:
1. Fetch the primary HTML/HTM document from the `document_url` in the `filings` table.
2. Strip XBRL tags and boilerplate (exhibit tables, signatures).
3. Extract three sections: Risk Factors, MD&A, Liquidity and Capital Resources.
4. Run FinBERT sentiment on each section separately (risk factors are inherently negative in tone; the interesting signal is year-over-year change in language, not absolute sentiment).
5. Generate a 3–5 sentence summary per section using Claude (via FastAPI, same pattern as the existing research run).
6. Store section summaries and sentiment scores in `filing_analysis` table.
7. Generate embeddings for the full document and store in `filings.embedding` (pgvector) for semantic search ("find all 10-Ks mentioning supply chain risk in the last year").

```sql
CREATE TABLE filing_analysis (
  filing_id         UUID PRIMARY KEY REFERENCES filings(id),
  section           TEXT NOT NULL CHECK(section IN ('risk_factors','mda','liquidity','full')),
  sentiment_score   NUMERIC(5,4),   -- [-1, 1]
  summary           TEXT,
  embedding         vector(1536),
  processed_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (filing_id, section)
);

CREATE INDEX ON filing_analysis USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

---

#### 4.17.6 Updated driver scoring logic

The existing driver scoring in the FastAPI backend uses yfinance for Filings and Insider drivers. Replace the data source, keeping the scoring logic intact:

**Filings Driver (updated)**:
```python
# Before (yfinance — unreliable)
filings = ticker.get_sec_filings()

# After (EDGAR via Postgres)
filings = db.query(
    "SELECT filed_at, form_type FROM filings "
    "WHERE ticker = :ticker AND form_type IN ('10-K','10-Q','8-K') "
    "ORDER BY filed_at DESC LIMIT 5",
    ticker=ticker
)
# Scoring thresholds unchanged: 3d = high, 7d = medium, 14d = low
```

**Insider Driver (updated)**:
```python
# Before (yfinance — incomplete, delayed)
insider_df = ticker.insider_transactions

# After (EDGAR Form 4 via Postgres — complete, 2-day max delay)
transactions = db.query(
    "SELECT transaction_date, transaction_type, total_value, shares "
    "FROM insider_transactions "
    "WHERE ticker = :ticker AND is_open_market = true "
    "AND transaction_date >= NOW() - INTERVAL '90 days' "
    "ORDER BY transaction_date DESC",
    ticker=ticker
)
# Add net signal: sum of purchase value minus sale value over window
# Positive net = insider buying pressure signal
```

---

#### 4.17.7 Data flow diagram for fundamental pipeline

```
SEC EDGAR
  ├── company_tickers.json (daily)     → CIK↔Ticker sync job   → cik_ticker_map
  ├── RSS Atom feed (every 10 min)     → Filing sync service    → filings table
  │     └── Form 4 XML                → Form 4 parser          → insider_transactions
  │     └── 10-K / 10-Q HTML          → NLP service            → filing_analysis + embeddings
  └── Submissions API (backfill)       → Historical sync job    → filings table (history)

SEC Company Facts
  └── companyfacts/CIK.json (cached)    → Facts normalizer       → company_facts_snapshots

Postgres (unified)
  └── FastAPI driver scoring reads:
        filings          → Filings Driver score
        insider_transactions → Insider Driver score
        company_facts_snapshots → Financial context in LLM narrative
```

---

#### 4.17.8 SEC EDGAR rate limiting and compliance

- Include `User-Agent: {AppName} {contact@email}` on every request (SEC requirement, enforced by IP block).
- Max 10 requests/second per IP. Use an async HTTP client (httpx with semaphore in Python) to enforce this.
- Cache all EDGAR document fetches in S3 (`edgar-raw/`) — if the NLP service reprocesses a filing, fetch from S3, not EDGAR again.
- The EDGAR full-text content is public domain (US government work). No licensing restrictions on storage or redistribution of the filing content itself.
- Do not use Alpha Vantage/FMP/Twelve Data in Phase 1. Their request limits and display restrictions add complexity before the product needs them.

---

#### 4.17.9 New ECS services required

| Service | Trigger | CPU | Memory | Always-on? |
|---|---|---|---|---|
| cik-ticker-sync | Daily cron (06:00 ET) | 256 | 512 | No (ECS scheduled task) |
| filing-rss-poller | Always-on during SEC hours | 256 | 512 | Yes |
| form4-parser | DB poll / internal queue on new Form 4 filing | 256 | 512 | Yes |
| filing-backfill | One-shot per symbol on deploy | 512 | 1024 | No (ECS run task) |
| company-facts-sync | Daily/watchlist-triggered | 256 | 512 | No (ECS scheduled task) |

Use a DB-backed job table or internal queue for Phase 1 filing events. Add Kinesis only in Phase 3 when multiple independent consumers need replay/fan-out.

---

## Part 10 — Priority action list (updated)

In order of what blocks everything else:

1. **Add auth to existing FastAPI + Next.js** — Clerk is fastest unless AWS-native Cognito is required. Blocks public deployment.
2. **Finish SEC EDGAR ingestion** — CIK sync, Submissions API filings, Form 4 XML parser persistence, and Company Facts snapshots.
3. **Replace yfinance-backed Filings and Insider drivers** — keep scoring logic, swap data source to EDGAR-backed tables.
4. **Add Postgres-backed 24h TTL cache** — all external calls must be cached and idempotent.
5. **Document data licensing** — add `docs/DATA_LICENSING.md` before any public market-data display.
6. **Add watchlist model** — holdings-derived + manual symbols + benchmarks.
7. **Build narrow live provider adapter** — small aggregate watchlist only; verify provider display rights before public use.
8. **Use vendor aggregate bars direct to Postgres/Timescale** — no raw-tick normalization or Kinesis in Phase 1-2.
9. **Minimal frontend validation page** — live quote + 1-day chart for a selected supported symbol.
10. **Only then evaluate paid data + Kinesis** — add them when symbol caps, display rights, or multi-consumer fan-out justify the cost.
