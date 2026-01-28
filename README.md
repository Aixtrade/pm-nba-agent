# PM NBA Agent

[中文文档](./README_CN.md) | English

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A specialized AI agent for real-time NBA game analysis. Parse NBA game information from Polymarket event URLs and fetch live game data via nba_api, with built-in LLM-powered game analysis and prediction capabilities.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Modules](#core-modules)
  - [Game Data Module](#game-data-module)
  - [AI Analysis Module](#ai-analysis-module)
- [Configuration](#configuration)
- [Examples](#examples)
- [Project Structure](#project-structure)
- [Data Models](#data-models)
- [Development](#development)
- [Important Notes](#important-notes)
- [License](#license)

## Features

- **URL Parsing**: Extract team abbreviations and game dates from Polymarket URLs
- **Team Resolution**: Query full team information by abbreviation
- **Game Finder**: Locate game IDs by teams and dates
- **Live Data**: Fetch real-time game statistics, scores, and play-by-play
- **AI Analysis**: LLM-powered real-time game analysis and predictions
  - Automatic event detection (score changes, lead changes, big plays)
  - Streaming analysis output
  - Configurable analysis intervals
  - Smart event-triggered analysis
- **Data Models**: Strongly-typed game data structures with serialization support

## Installation

### Option 1: Docker (Recommended for Production)

The easiest way to deploy the full application (backend + frontend):

```bash
# 1. Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 2. Build and start services
docker compose up -d

# 3. Access the application
# Frontend: http://localhost
# API docs: http://localhost/api/docs
```

See [DOCKER.md](./DOCKER.md) for detailed Docker deployment guide.

### Option 2: Local Development

Use [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Create virtual environment and install dependencies
uv sync

# Or manually create virtual environment
uv venv
source .venv/bin/activate  # Linux/macOS

# Install dependencies
uv add nba_api pandas openai
```

## Quick Start

### Basic Game Data

```python
from pm_nba_agent.main import get_game_data_from_url

# Fetch game data from Polymarket URL
url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"
game_data = get_game_data_from_url(url)

# Access game information
print(f"Status: {game_data.game_info.status}")
print(f"{game_data.away_team.name}: {game_data.away_team.score}")
print(f"{game_data.home_team.name}: {game_data.home_team.score}")

# Convert to dictionary
data_dict = game_data.to_dict()
```

### AI-Powered Analysis

```python
import asyncio
from pm_nba_agent.agent import GameAnalyzer, GameContext, AnalysisConfig

async def analyze_game():
    # Configure analyzer (reads from environment variables by default)
    config = AnalysisConfig(
        api_key="your-openai-api-key",
        model="gpt-4o-mini",
        analysis_interval=30.0,  # Normal analysis interval (seconds)
        event_interval=15.0      # Event-triggered interval (seconds)
    )

    analyzer = GameAnalyzer(config)
    context = GameContext(game_id="0022600123")

    # Update context with game data
    context.update_scoreboard({
        "status": "Live - Q3",
        "period": 3,
        "game_clock": "7:23",
        "home_team": {"name": "Lakers", "score": 78},
        "away_team": {"name": "Warriors", "score": 82}
    })

    # Stream analysis
    if analyzer.should_analyze(context):
        async for chunk in analyzer.analyze_stream(context):
            print(chunk, end="", flush=True)

    await analyzer.close()

asyncio.run(analyze_game())
```

## Core Modules

### Game Data Module

#### 1. URL Parsing

```python
from pm_nba_agent.parsers import parse_polymarket_url

url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"
event_info = parse_polymarket_url(url)

print(event_info.team1_abbr)  # 'ORL'
print(event_info.team2_abbr)  # 'CLE'
print(event_info.game_date)   # '2026-01-26'
```

#### 2. Team Information

```python
from pm_nba_agent.nba import get_team_info

team = get_team_info('ORL')
print(team.full_name)  # 'Orlando Magic'
print(team.nickname)   # 'Magic'
```

#### 3. Game Finder

```python
from pm_nba_agent.nba import find_game_by_teams_and_date

game_id = find_game_by_teams_and_date('ORL', 'CLE', '2026-01-26')
print(game_id)  # '0022600123'
```

#### 4. Live Game Data

```python
from pm_nba_agent.nba import get_live_game_data

game_data = get_live_game_data('0022600123')
print(game_data.game_info.status)  # 'Live - Q3'
print(game_data.home_team.score)   # 89
```

### AI Analysis Module

The AI analysis module provides intelligent real-time game analysis powered by LLMs.

#### Key Components

- **GameAnalyzer**: Main analyzer with streaming support
- **GameContext**: Maintains game state and detects significant events
- **LLMClient**: Async OpenAI client with retry logic
- **AnalysisConfig**: Configuration management with environment variable support

#### Event Detection

The analyzer automatically detects:

- **Score Runs**: 5+ point scoring runs
- **Lead Changes**: When teams exchange the lead
- **Period Transitions**: Quarter/overtime changes
- **Three-Pointers**: Made three-point shots
- **Dunks**: Dunk plays

#### Analysis Triggers

- **Time-based**: Regular intervals (default 30 seconds)
- **Event-based**: Shorter intervals when significant events occur (default 15 seconds)
- **First analysis**: Triggers as soon as data is available

## Configuration

The AI analysis module can be configured via environment variables or code:

### Environment Variables

```bash
# OpenAI Configuration
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Optional
export OPENAI_MODEL="gpt-4o-mini"  # Default model

# Analysis Intervals (seconds)
export ANALYSIS_INTERVAL="30"        # Normal interval
export ANALYSIS_EVENT_INTERVAL="15"  # Event-triggered interval
```

### Programmatic Configuration

```python
from pm_nba_agent.agent import AnalysisConfig

config = AnalysisConfig(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",
    model="gpt-4o-mini",
    analysis_interval=30.0,
    event_interval=15.0,
    max_tokens=1024,
    temperature=0.7
)
```

## Examples

Run the included examples:

```bash
# Basic example
python examples/example.py

# Detailed usage
python examples/basic_usage.py

# Advanced usage (batch queries)
python examples/advanced_usage.py

# Player stats analysis
python examples/player_stats_analysis.py

# Or use uv to run
uv run python examples/example.py
```

## Project Structure

```
PM_NBA_Agent/
├── pm_nba_agent/              # Core library
│   ├── parsers/               # URL parsing
│   │   └── polymarket_parser.py
│   ├── nba/                   # NBA data fetching
│   │   ├── team_resolver.py   # Team information
│   │   ├── game_finder.py     # Game finder
│   │   └── live_stats.py      # Live data
│   ├── models/                # Data models
│   │   └── game_data.py
│   ├── agent/                 # AI analysis module
│   │   ├── analyzer.py        # Game analyzer
│   │   ├── context.py         # Game context manager
│   │   ├── llm_client.py      # OpenAI client
│   │   ├── models.py          # Analysis models
│   │   └── prompts.py         # Prompt templates
│   └── main.py                # Main orchestration
├── examples/                  # Usage examples
│   ├── example.py
│   ├── basic_usage.py
│   ├── advanced_usage.py
│   └── player_stats_analysis.py
├── tests/                     # Test scripts
│   ├── test_today_games.py
│   └── test_full_flow.py
├── pyproject.toml            # Project configuration
├── README.md                 # Documentation (English)
└── README_CN.md              # Documentation (Chinese)
```

## Data Models

### GameData

Complete game data structure:

- `game_info`: Basic game info (game_id, date, status, period, clock)
- `home_team`: Home team statistics (name, abbreviation, score, detailed stats)
- `away_team`: Away team statistics
- `players`: Player list (name, team, position, on_court status, detailed stats)

### GameContext

Manages game state for analysis:

- Tracks scoreboard, boxscore, and play-by-play updates
- Detects significant events automatically
- Determines optimal analysis timing
- Maintains analysis history

### AnalysisConfig

Configuration for the analyzer:

- OpenAI API settings (key, base_url, model)
- Analysis timing (intervals, event triggers)
- LLM parameters (max_tokens, temperature)

## Development

### Running Tests

```bash
# Tests are script-based, not pytest
python tests/test_today_games.py
python tests/test_full_flow.py

# Using uv
uv run python tests/test_today_games.py
```

### Building the Package

```bash
python -m build
```

## Important Notes

1. **API Rate Limiting**: Built-in 0.6-second delays between requests to avoid NBA API rate limits
2. **Game Timing**: Live API works for current day games; use Stats API for historical/future games
3. **Time Zone**: NBA game times are in US Eastern Time (EST/EDT)
4. **Game Status Codes**: 1=Scheduled, 2=Live, 3=Final
5. **AI Analysis**: Requires valid OpenAI API key; falls back gracefully if not configured

## License

MIT License - see [LICENSE](./LICENSE) file for details.

---

**Note**: This project uses nba_api for data access. Please respect NBA's data usage policies and API rate limits.
