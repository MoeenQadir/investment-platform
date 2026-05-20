# Agent Architecture Rules

This document defines the non-negotiable architecture rules for agents working on this codebase.

## Core Principles

1. **Frontend Isolation**: The Next.js frontend calls ONLY the FastAPI backend. Frontend must NEVER call n8n directly.

2. **Backend as System of Record**: The FastAPI backend is the system of record and does ALL deterministic finance calculations:
   - Returns, volatility, exposure calculations
   - Benchmark comparisons
   - Driver scoring (0..1 buckets)
   - Price move detection (2σ threshold)
   - Sector normalization and ETF proxy resolution

3. **n8n Orchestration Scope**: n8n orchestrates workflow steps and retries. It uses an LLM ONLY for narrative synthesis (report writing), NEVER for math or deterministic calculations.

4. **Reproducibility**: All runs are LIVE-based (use current portfolio at trigger time), BUT store `holdings_snapshot_json` inside each run record for reproducibility.

5. **Run Statuses**: Research/Explanation runs use these statuses:
   - `QUEUED`: Run created, awaiting processing
   - `RUNNING`: Currently being processed
   - `COMPLETED`: Successfully completed
   - `COMPLETED_WITH_WARNINGS`: Completed but with warnings (e.g., unsupported holdings skipped)
   - `FAILED`: Run failed with error

## Data Flow

```
User Action → Frontend → FastAPI API → (creates run) → n8n webhook
                                                         ↓
n8n workflow → FastAPI (for metrics/compute) → LLM (narrative only) → FastAPI webhook (complete/fail)
```

## Calculation Ownership

- **FastAPI owns**: All math, scoring, sector mapping, ETF resolution
- **n8n owns**: Orchestration, retries, LLM prompting for reports
- **Frontend owns**: UI/UX, polling for status updates

## Sector & ETF Handling

- Canonical sectors are normalized (NOT raw provider strings)
- Sector→ETF mapping is DB-driven via `sector_etf_proxies` table
- Provider aliases map to canonical sectors via `sector_aliases` table

## Marketplace Support

- v1: US only (provider_symbol = ticker_symbol)
- Future: India support (NSE => ticker.NS, BSE => ticker.BO)
- Schema designed to support multiple marketplaces without refactoring

## Auth (Clerk)
- All Clerk JWT verification happens in apps/api/app/auth.py via JWKS, never duplicated elsewhere.
- Every FastAPI route that touches user-scoped data MUST take Depends(get_current_user). Routes that don't need a user (health, public reference data) explicitly note 'public' in a docstring.
- The User row is the join key. We upsert by clerk_user_id on first sign-in. Never use the email as a primary identifier; emails are mutable in Clerk.
- Frontend never embeds CLERK_SECRET_KEY — only NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY. The secret key is API-side only.

## EDGAR Pipeline
- Every SEC HTTP call goes through apps/api/app/services/edgar/sec_client.SecClient. Never call httpx.get on sec.gov directly.
- SEC_USER_AGENT env var must be set to 'AppName contact@email' format. Missing/empty value MUST raise on client construction.
- CIK is stored as a 10-digit zero-padded string. Use _pad_cik helper at every boundary that accepts user/JSON input.
- Form 4 parsing uses defusedxml only. Stdlib xml.etree is forbidden.
- cik_sync and filing_sync MUST be idempotent — they are safe to re-run.
