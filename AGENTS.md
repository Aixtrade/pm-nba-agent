# AGENTS.md

This file is guidance for agentic coding assistants working in this repo.
It summarizes how to build, lint, test, and follow local code style.

Repository overview
- Package name: pm-nba-agent
- Python: >= 3.12
- Dependency manager: uv (recommended)
- Core code: pm_nba_agent/
- Tests: tests/ (script-style, not pytest)

Build, lint, test

Environment setup
- Install deps (recommended): `uv sync`
- Create venv manually: `uv venv` then `source .venv/bin/activate`

Build
- Package build (standard): `python -m build`
- Note: no explicit build scripts in this repo beyond PEP 517 metadata.

Run examples
- `python examples/example.py`
- `python examples/basic_usage.py`
- `python examples/advanced_usage.py`
- `python examples/player_stats_analysis.py`

Lint/format
- No lint/format tooling configured in this repo.
- If you add tools, prefer ruff + black and document the commands here.

Tests
- Tests are runnable scripts (not pytest).
- Run all tests (manual):
  - `python tests/test_today_games.py`
  - `python tests/test_full_flow.py`
- Run a single test: `python tests/test_today_games.py`
- With uv (if venv not activated): `uv run python tests/test_today_games.py`

Runtime notes for tests
- Tests hit live NBA APIs and are rate-limited in code with `time.sleep(0.6)`.
- Tests depend on real games; failures can be due to schedule or API state.
- If no games are scheduled, expect empty results rather than errors.
- Re-run later when games are available if a test appears inconclusive.
- Avoid parallel test runs to reduce API throttling risk.

Code style and conventions

General style
- Use 4-space indentation and keep lines readable (no enforced formatter).
- Prefer f-strings for user-facing text and logging.
- Keep public functions small and single-purpose; helper functions are private.
- Use docstrings for modules and public functions (triple-quoted).
- Docstrings commonly include Args/Returns/Examples sections.
- Keep behavior explicit; avoid hidden side effects.
- Use blank lines to separate logical blocks within functions.
- Keep conditional branches straightforward and easy to trace.

Imports
- Order imports: standard library, third-party, local.
- Use absolute imports within package when practical; relative imports are used.
- Example ordering:
  - stdlib: `import json`, `from datetime import datetime`
  - third-party: `from nba_api.stats.endpoints import scoreboardv2`
  - local: `from .models import GameData`
- Keep import groups separated by a single blank line.

Typing
- Use type hints for public functions and dataclasses.
- Return Optional[...] when a failure returns None.
- Use built-in generics (e.g., `list[TeamInfo]`) for Python 3.12.
- Use Dict[str, Any] or dict for dynamic API payloads.
- Prefer explicit types on dataclass fields.
- Keep Optional handling explicit with early returns.

Naming
- Modules: snake_case.
- Functions: snake_case with verbs (e.g., `get_live_game_data`).
- Classes: CapWords (e.g., `GameData`, `TeamStats`).
- Constants: UPPER_SNAKE_CASE (none currently defined).
- Booleans: prefer prefixes like `is_`, `has_`, `use_`.

Data modeling
- Use dataclasses for structured data (see `pm_nba_agent/models/game_data.py`).
- Provide `from_*` classmethods to adapt external API payloads.
- Keep serialization helpers (e.g., `to_dict`) on models.
- Use `field(default_factory=...)` for mutable defaults.
- Keep model `to_dict` output stable when possible.

API payload handling
- Prefer `.get(...)` with defaults when reading API dicts.
- Keep mapping logic close to the API response structure.
- Avoid mutating raw API payloads; build new dicts/models.
- Treat missing fields as expected; default to safe values.

Formatting and strings
- Strings use double quotes in most files; be consistent in touched files.
- Keep printed messages concise; prefer short status lines.
- JSON output in examples uses `ensure_ascii=False` for readability.

Error handling
- Use try/except around external API calls.
- On failure, return None or empty list, and print a clear message.
- Avoid raising for expected external failures (network, missing game data).
- Keep exception scopes narrow and close to the API call.
- Preserve existing user-facing error message style (prefix with clear context).

Logging/printing
- Current code prints user-facing progress with `print()`.
- Keep prints concise and informative; avoid noisy debug output.
- Preserve existing emoji usage only if already present in nearby code.

External APIs
- NBA API calls are rate limited by `time.sleep(0.6)` in helpers.
- Keep that delay if you add additional NBA API calls.
- Live API is preferred when available; Stats API is fallback.
- Validate inputs before making network requests when practical.

Testing conventions
- Tests are scripts; no pytest fixtures or assertions currently.
- Keep tests runnable directly with `python ...`.
- When adding tests, follow the existing print-based reporting style.
- Tests may fail if there are no games scheduled; treat as non-deterministic.
- Avoid running tests in CI without scheduling/ratelimit considerations.

File structure notes
- URL parsing lives in `pm_nba_agent/parsers/`.
- NBA API wrappers live in `pm_nba_agent/nba/`.
- Models live in `pm_nba_agent/models/`.
- Public entrypoint is `pm_nba_agent/main.py`.
- Package exports are re-exported in `pm_nba_agent/__init__.py`.

Git/workspace hygiene
- You may be in a dirty worktree; do not revert unrelated changes.
- Avoid destructive git commands unless explicitly requested.
- Do not amend commits unless explicitly requested.
- Do not push to remote unless explicitly requested.

Cursor/Copilot rules
- No `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` found.
- If you add them, update this file to mirror their requirements.

Contributing tips for agents
- Avoid changing public signatures unless necessary; update examples if you do.
- Keep README examples working when you change public APIs.
- Maintain compatibility with Python 3.12+.
- Do not remove rate-limit sleeps unless replacing with explicit throttling.
