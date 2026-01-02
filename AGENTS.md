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

