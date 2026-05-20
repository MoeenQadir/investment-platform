# Work Done By Agents

Chronological log of every change made by Claude Code, Codex CLI, and spawned sub-agents since the initial repo import (commit `280d6e2`). Append a new entry after each completed task. Keep entries terse — link to files instead of duplicating code.

---

## Session 1 — 2026-05-15

### 1. Ruflo + swarm bootstrap
- Installed `ruflo@latest` globally (`v3.7.0-alpha.40`).
- `ruflo init --full --start-all` — created `.claude/`, `.claude-flow/`, `.swarm/`, `.mcp.json`, `CLAUDE.md`, 98 agents, 10 commands, 7 hooks.
- `ruflo swarm init --topology hierarchical --max-agents 8` — swarm `swarm-1778907833667-bhv9ox`.
- `TeamCreate` → team `investment-research` (later replaced by `edgar-pipeline`).

### 2. Doctor + disk cleanup
- `ruflo doctor` flagged: no API keys, disk 95%, no TS, no agentic-flow, encryption off.
- Installed `typescript` (devDep) in `apps/web/`.
- Installed `agentic-flow@latest` globally (528 pkgs).
- `brew cleanup -s` freed 1.8 GB; `npm cache clean --force`. Disk 38% → 33% used.

### 3. Statusline setup
- Created `~/.claude/statusline-command.sh` (user@host | dir | git branch | model | ctx%).
- Wired into `~/.claude/settings.json` `statusLine` block.

### 4. Repo analysis vs `hld.md`
- Read `hld.md` Part 0–10. Mapped existing repo (Surface A portfolio research, yfinance, n8n) vs target (Surface B live market data, EDGAR, NLP).
- Identified gaps: no auth, no EDGAR/Polygon, no Timescale/pgvector, no live data, n8n still good for task orchestration.

### 5. Vendor research
- Reviewed Polygon free alternatives → recommended **Alpaca free** (real-time IEX WS, 30-symbol cap, 200 req/min).
- Discussed SEC EDGAR + XBRL Company Facts as zero-cost replacement for FMP fundamentals.

### 6. Provider abstraction (yfinance ↔ alpaca swappable)
- New package `apps/api/app/services/providers/` with `base.py` (`MarketDataProvider` Protocol), `yfinance_provider.py`, `alpaca_provider.py`, `__init__.py` (`get_provider()` factory keyed by `MARKET_DATA_PROVIDER` env var).
- Refactored `apps/api/app/services/finance.py`, `drivers.py`, `portfolio_metrics.py` to route through the provider — no more direct `yf.Ticker(...)` calls in those modules.
- `apps/api/requirements.txt` + `alpaca-py==0.30.1`.
- Created `apps/api/.env.example` with `MARKET_DATA_PROVIDER`, Alpaca keys.

### 7. Infra restructure
- `git mv` Docker Compose + n8n to `infra/local/` (history preserved).
- Fixed compose build contexts: `../apps/...` → `../../apps/...`; n8n volume → `./n8n/workflows`.
- Created `infra/aws/` Terraform skeleton: 15 module stubs (vpc, ecs_*, kinesis_*, rds_postgres, elasticache_redis, alb, acm, route53, waf, cloudwatch_observability, iam_roles, secrets, pgvector, ecr) + `envs/dev|prod` (main.tf, variables.tf, backend.tf, terraform.tfvars.example).
- Added `infra/README.md` and `infra/aws/README.md` (milestone → module map).
- Updated `README.md` + `PROJECT_STATUS.md` path refs (`infra/docker-compose` → `infra/local/docker-compose`).

---

## Session 2 — 2026-05-16

### 8. HLD revision (user-authored)
- User rewrote `hld.md` around Phase 1 (EDGAR reliability) → Phase 2 (watchlist-scoped live) → Phase 3 (scale when justified).
- Deferred Kinesis, Redis, Flink, raw-tick normalization, paid vendor signups out of Phase 1–2.
- Replaced FMP with SEC Company Facts/XBRL.
- Added `watchlists` and `user_entitlements (data_tier=delayed|realtime)` tables.
- File untracked in git (working-tree only).

### 9. EDGAR pipeline (5-agent swarm)
- Team `edgar-pipeline` created. Spawned `researcher` → `architect` → `coder` → `tester` → `reviewer` (all background).
- `researcher` documented EDGAR endpoints, sample shapes, gotchas (CIK padding, accession dash/no-dash, Form 4 atom feed dedup). Output: `/tmp/edgar-research.md` + `/tmp/edgar-samples/`.
- `architect` produced `/tmp/edgar-design.md` (table DDL, service signatures).
- `coder` shipped:
  - `apps/api/alembic/versions/002_edgar_tables.py` + ORM models `SecCompany`, `SecFiling`, `SecForm4Transaction` in `models.py`.
  - `apps/api/app/services/edgar/{sec_client,cik_sync,filing_sync,form4_parser}.py` (async httpx + `asyncio.Semaphore` + UA header, defusedxml).
  - `apps/api/app/services/drivers.py` helpers `get_days_since_filing` + `get_days_since_form4`; wired into `score_drivers_for_event(..., ticker)`.
  - `defusedxml==0.7.1` in `requirements.txt`. `SEC_USER_AGENT`, `EDGAR_RATE_LIMIT` in `.env.example`.
- `tester` wrote 5 test files (`test_edgar_sec_client.py`, `test_edgar_cik_sync.py`, `test_edgar_filing_sync.py`, `test_edgar_form4_parser.py`, `test_drivers_edgar_helpers.py`) + `conftest.py` + `fixtures/form4_sample.xml`. 39 tests pass.
- `reviewer` produced `/tmp/edgar-review.md`: 10/10 PASS, 0 fails, 6 non-blocking notes.
- Removed duplicate `test_edgar_drivers_helpers.py` (kept `test_drivers_edgar_helpers.py` which uses shared `conftest.py` fixture).
- All 5 agents shut down cleanly.

### 10. Clerk auth — Track A (backend + frontend)
- Backend
  - `apps/api/app/auth.py` — JWKS cache, `verify_token`, `get_current_user` FastAPI dep (auto-upserts User by `clerk_user_id`).
  - `apps/api/app/db/models.py` — added `clerk_user_id` (unique) + `created_at` columns to `User`.
  - `apps/api/alembic/versions/003_clerk_user_id.py` — add columns + unique index.
  - `apps/api/requirements.txt` + `pyjwt[crypto]==2.8.0`.
- Frontend
  - `apps/web/app/layout.tsx` — `<ClerkProvider>` wrap.
  - `apps/web/middleware.ts` — `clerkMiddleware`, public matcher (`/`, `/sign-in`, `/sign-up`).
  - `apps/web/app/sign-in/[[...sign-in]]/page.tsx`, `apps/web/app/sign-up/[[...sign-up]]/page.tsx`.
  - `apps/web/lib/api.ts` — `setAuthTokenGetter`, request interceptor.
  - `apps/web/lib/use-api-auth.ts` — hook bridging Clerk `getToken()` → axios.
  - `apps/web/package.json` + `@clerk/nextjs ^6.0.0`.
  - `apps/web/.env.local.example` — Clerk + redirect URLs.
- Routers **not yet** protected with `Depends(get_current_user)` (next pass).

### 11. Codex CLI — Track B (parallel cleanup)
- Launched `codex exec --sandbox workspace-write` in background via Bash.
- Output verified on disk:
  - `AGENTS.md` + new sections "Auth (Clerk)" (4 rules) and "EDGAR Pipeline" (5 rules).
  - `apps/api/app/services/drivers.py` lines 82 + 100: broad `except Exception:` → typed `(ValueError, KeyError, IndexError, TypeError, AttributeError)`.
  - `apps/api/app/services/edgar/filing_sync.py:_build_index_url` collapsed to single-line URL (removed dup `action=getcompany` + pointless `.replace("\n","")`).
- `python3 -m py_compile` passed on all 3 edited files.

### 12. Process — work log added
- Created this file at `docs/WORK_DONE_BY_AGENTS.md` to track every agent-driven change going forward. Update at the end of every completed task.

### 13. Routers protected (Clerk + n8n shared secret)
- `apps/api/app/routers/portfolio.py` — all 4 routes now take `Depends(get_current_user)`. New `_get_owned_portfolio` helper scopes lookups to `Portfolio.user_id == current_user.id`. `DEMO_USER_ID` removed; portfolios are created against the authenticated user.
- `apps/api/app/routers/research.py` — `/run` protected. Portfolio lookup gated on `user_id == current_user.id`. `ResearchRun.user_id` set from `current_user.id`. Removed `DEMO_USER_ID` + unused `json` import.
- `apps/api/app/routers/explain.py` — same pattern as research. Removed `DEMO_USER_ID` + unused `json` import + unused `score_drivers_for_event` import.
- `apps/api/app/routers/runs.py` — both routes (`GET /` and `GET /{run_id}`) protected. List query filtered by `ResearchRun.user_id == current_user.id`; single-run lookup also filters by owner. Invalid UUID now returns 400 (was a 200 with `{"error": ...}` body); missing run returns 404.
- `apps/api/app/routers/webhooks.py` — kept open to n8n (not a browser caller), but gated by new `verify_n8n_secret` dep that does a `hmac.compare_digest` against `N8N_WEBHOOK_SECRET` env var when set. Dev loop without the var still works; production must set the secret in API env + n8n HTTP Request node.
- All 5 routers `python3 -m py_compile` clean.

### 14. AuthBridge mounted + sec_client Host header dropped
- `apps/web/components/auth-bridge.tsx` — new client component calling `useApiAuth()` then rendering children.
- `apps/web/app/layout.tsx` — wraps children with `<AuthBridge>` inside `<ClerkProvider>`. Single mount point; every page now gets Clerk token injection automatically.
- `apps/web/tsconfig.json` already has `@/*` alias → `./*`, so `@/components/auth-bridge` resolves.
- `apps/api/app/services/edgar/sec_client.py` — removed hardcoded `Host: www.sec.gov` header from `httpx.AsyncClient` defaults. httpx derives Host from URL per request, so `data.sec.gov` calls now send correct Host. Closes reviewer note #3.
- Did NOT run `alembic upgrade` — needs postgres running via `docker compose -f infra/local/docker-compose.yml up postgres -d`. User runs that step when ready.

### 16. Datetime + SQLAlchemy deprecation cleanup
- `apps/api/app/utils/time.py` — NEW. Single `utcnow()` helper returning naive UTC (`datetime.now(timezone.utc).replace(tzinfo=None)`). Centralised so a future tz-aware migration only touches one file.
- `apps/api/app/services/drivers.py` — `datetime.utcnow()` → `utcnow()` import.
- `apps/api/app/db/models.py` — 8 `default=datetime.utcnow` callbacks swapped to `default=utcnow`. Removed now-unused `from datetime import datetime`.
- `apps/api/tests/test_drivers_edgar_helpers.py` — 7 `datetime.utcnow()` calls replaced via `sed` + import update.
- `apps/api/app/db/database.py` — `from sqlalchemy.ext.declarative import declarative_base` → `from sqlalchemy.orm import declarative_base` (SQLAlchemy 2.0).
- pytest: **46 passed, 0 warnings** (was 46 passed, 63 warnings).

### 15. EDGAR reviewer follow-ups closed (singleton + XXE + integration tests)
- `apps/api/app/services/edgar/sec_client.py` — added `get_shared_client()` async singleton + `reset_shared_client()` teardown helper. Closes reviewer note #2 (per-process semaphore).
- `apps/api/app/services/edgar/__init__.py` — re-exports the two new helpers.
- `apps/api/tests/test_edgar_form4_parser.py` — added two XXE smoke tests: `test_rejects_xxe_doctype_payload` (external entity to `/etc/passwd`) and `test_rejects_entity_expansion_payload` (billion-laughs). Both assert `defusedxml.common.DefusedXmlException` is raised. Closes reviewer note #5.
- `apps/api/tests/test_edgar_sync_integration.py` — NEW. 5 end-to-end tests using `httpx.MockTransport` to verify `sync_cik_tickers` + `sync_filings_for_cik` wire correctly: happy path, idempotence over HTTP, form-type filter. Closes reviewer note #4.
- pytest run: **46 passed** (was 39). Pre-existing `datetime.utcnow()` deprecation warnings in `drivers.py` + `test_drivers_edgar_helpers.py` not introduced here — follow-up cleanup tracked below.

---

## Outstanding (next)
1. `docker compose -f infra/local/docker-compose.yml up postgres -d` → `alembic upgrade head` to apply migrations 002 + 003.
2. Clerk signup + populate `.env` (`CLERK_SECRET_KEY`, `CLERK_JWT_ISSUER`, `CLERK_JWKS_URL`, `N8N_WEBHOOK_SECRET`) + `.env.local` (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`).
3. `cd apps/web && npm install` to pull `@clerk/nextjs`.
4. First real EDGAR sync run (CIK map + S&P 500 filings).
