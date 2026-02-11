# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PM NBA Agent — real-time NBA game analysis + Polymarket trading system. Python backend (FastAPI + SSE) with Vue3 frontend dashboard.

- Python >= 3.12, dependency manager: **uv**
- Backend: `pm_nba_agent/`
- Frontend: `frontend/` (Vue3 + Vite + TailwindCSS v4 + DaisyUI v5)
- No lint/format tooling configured

## Development Commands

### Backend
```bash
uv sync                          # Install dependencies
uv run uvicorn pm_nba_agent.api.app:app --host 0.0.0.0 --port 8000 --reload  # Dev server

# Tests are script-style (not pytest), hit live NBA APIs
uv run python tests/test_today_games.py
uv run python tests/test_full_flow.py
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev          # Dev server (port 3000)
pnpm build        # Production build
pnpm type-check   # TypeScript type checking
```

### Docker (4 services: redis, backend, worker, frontend)
```bash
cp .env.example .env
docker compose up -d
# Frontend: http://localhost:8080, API proxied at http://localhost:8080/api/*
```

## Architecture

### System Overview
```
Frontend (Vue3) <-- SSE --> FastAPI API <-- WebSocket --> Polymarket
                                |
                                v
                          NBA API (nba_api)
                                |
                          Redis (optional)
                                |
                          Worker (background tasks)
```

Two operating modes:
1. **Direct streaming** — frontend opens SSE to `/api/v1/live/stream`, backend streams data directly (no Redis needed)
2. **Task mode** — frontend creates a background task via `/api/v1/tasks/create`, worker process picks it up from Redis, frontend subscribes via `/api/v1/live/subscribe/{task_id}`

### Backend Modules (`pm_nba_agent/`)
- `api/` — FastAPI app, routes, services
  - `routes/`: `live_stream.py` (SSE), `tasks.py` (background tasks CRUD), `auth.py` (JWT login), `orders.py`, `positions.py`, `parse.py`
  - `services/game_stream.py` — core: integrates NBA data + Polymarket orderbook + strategy execution
- `nba/` — NBA data fetching (team_resolver, game_finder, live_stats, playbyplay)
- `polymarket/` — trading integration
  - `ws_client.py`, `book_stream.py` — WebSocket orderbook subscription
  - `strategies/` — strategy framework (see "Strategies" section)
  - `executor.py` — strategy executor
  - `orders.py`, `positions.py` — order placement & position queries
- `agent/` — AI analysis (GameAnalyzer, GameContext, LLMClient)
- `worker/` — background task processor (`main.py`, `task_manager.py`, `game_task.py`)
- `shared/` — Redis client, task models, pub/sub channels
- `models/` — data models (GameData, TeamStats, PlayerStats)
- `parsers/` — Polymarket URL parsing

### Frontend Modules (`frontend/src/`)
- **Stores** (Pinia): `gameStore` (game data + signals), `taskStore` (background tasks), `authStore` (JWT), `connectionStore` (SSE state), `toastStore`
- **Services**: `sseService.ts` (SSE connection + auto-reconnect), `autoBuyService.ts` (auto-execute merge_long signals), `taskService.ts` (task CRUD)
- **Composables**: `useSSE.ts` (wires SSE events → stores)
- **Views**: `MonitorView.vue` (main dashboard)
- **Components**: `monitor/` — ScoreBoard, BoxScore, PolymarketBookPanel, StrategySignalPanel, StrategySidebar, StreamConfig, AgentAnalysisPanel

### Data Flow (Direct Streaming)
1. Frontend SSE → `POST /api/v1/live/stream`
2. `GameStreamService` parses Polymarket URL, gets market info
3. Subscribes Polymarket WebSocket for live orderbook
4. Polls NBA API for scores, stats, play-by-play
5. Strategy engine generates signals on orderbook changes
6. AI analyzer periodically analyzes game state
7. All data pushed to frontend via SSE events

### SSE Event Types
`scoreboard`, `boxscore`, `polymarket_info`, `polymarket_book`, `strategy_signal`, `analysis_chunk`, `game_end`, `heartbeat`, `error`, `task_status`, `task_end`, `subscribed`, `auto_buy_state`, `auto_sell_state`, `auto_sell_execution`, `position_state`

## Strategies

### Available Strategies
- **`merge_long`** (Binary Merge Long) — arbitrage when YES+NO cost < 1.0
- **`locked_profit`** (Locked Profit) — hedge to lock in target profit

### Multi-Strategy Support
`LiveStreamRequest` accepts both `strategy_id` (single, backward-compat) and `strategy_ids` (multi). `get_effective_strategy_configs()` unifies both into `list[tuple[str, dict]]`. Frontend `gameStore` stores signals per-strategy (`strategySignalsByStrategy`, `latestSignalByStrategy`). `StrategySidebar.vue` renders one `StrategySignalPanel` per active strategy.

### Adding a New Strategy
1. Create file in `pm_nba_agent/polymarket/strategies/`
2. Inherit `BaseStrategy`, implement `strategy_id` property and `generate_signal()`
3. Register with `@StrategyRegistry.register("strategy_id")` decorator

### Auto-Buy
`autoBuyService` subscribes to `sseService.subscribeStrategySignal()` and filters for `merge_long` BUY signals only.

## Authentication
- JWT-based via `config/users.yaml` (accounts) + `LOGIN_PASSPHRASE` + `LOGIN_TOKEN_SALT`
- Login endpoint: `POST /api/v1/auth/login`
- Tasks are user-scoped

## Environment Variables
```bash
OPENAI_API_KEY=sk-...            # AI analysis (optional)
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
ANALYSIS_INTERVAL=30             # Seconds between AI analyses
ANALYSIS_EVENT_INTERVAL=15
LOGIN_PASSPHRASE=change-me       # Auth passphrase
LOGIN_TOKEN_SALT=change-me-salt  # JWT salt
REDIS_URL=                       # Optional; enables task mode (redis://localhost:6379/0)
```

## Code Conventions

### Python
- Type annotations with Python 3.12 builtins: `list[T]`, `dict[K, V]`, `X | None`
- `dataclass` with `from_*()` factory classmethods and `to_dict()` serialization
- External API calls wrapped in try/except, return `None` on failure
- NBA API calls must have `time.sleep(0.6)` rate limiting — do not remove
- Logging: `from loguru import logger`
- Double-quoted strings; f-strings for interpolation

### Frontend
- Vue3 Composition API + `<script setup>`
- Pinia state management
- TailwindCSS v4 + DaisyUI v5

## Important Constraints
- **Never remove** `time.sleep(0.6)` rate limiting on NBA API calls
- NBA API times are US Eastern (EST/EDT)
- Live API only works for same-day games
- Polymarket WebSocket requires valid `token_id` list
- Tests hit live APIs — failures may be due to no scheduled games, not bugs
- Avoid parallel test runs (API throttling)
