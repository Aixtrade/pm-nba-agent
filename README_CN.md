# PM NBA Agent

中文文档 | [English](./README.md)

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

专门用于实时分析 NBA 比赛数据的 AI Agent。从 Polymarket 事件 URL 解析 NBA 比赛信息，并通过 nba_api 获取实时比赛数据，内置基于 LLM 的比赛分析和预测功能。

## 目录

- [功能特性](#功能特性)
- [安装](#安装)
- [快速开始](#快速开始)
- [核心模块](#核心模块)
  - [比赛数据模块](#比赛数据模块)
  - [AI 分析模块](#ai-分析模块)
- [配置说明](#配置说明)
- [示例](#示例)
- [项目结构](#项目结构)
- [数据模型](#数据模型)
- [开发](#开发)
- [注意事项](#注意事项)
- [许可证](#许可证)

## 功能特性

- **URL 解析**: 从 Polymarket URL 提取球队缩写和比赛日期
- **球队信息查询**: 通过缩写获取完整球队信息
- **比赛查找**: 根据球队和日期查找 game_id
- **实时数据**: 获取实时比赛统计、比分和逐回合数据
- **AI 智能分析**: 基于 LLM 的实时比赛分析和预测
  - 自动事件检测（比分变化、领先交换、精彩进球）
  - 流式分析输出
  - 可配置分析间隔
  - 智能事件触发分析
- **数据模型**: 强类型游戏数据结构，支持序列化

## 安装

### 方式一：Docker（推荐用于生产环境）

最简单的方式部署完整应用（后端 + 前端）：

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 2. 构建并启动服务
docker compose up -d

# 3. 访问应用
# 前端界面: http://localhost
# API 文档: http://localhost/api/docs
```

详细的 Docker 部署指南请参考 [DOCKER.md](./DOCKER.md)。

### 方式二：本地开发

使用 [uv](https://github.com/astral-sh/uv) 管理依赖：

```bash
# 创建虚拟环境并安装依赖
uv sync

# 或者手动创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS

# 安装依赖
uv add nba_api pandas openai
```

## 快速开始

### 基础比赛数据

```python
from pm_nba_agent.main import get_game_data_from_url

# 从 Polymarket URL 获取比赛数据
url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"
game_data = get_game_data_from_url(url)

# 访问比赛信息
print(f"比赛状态: {game_data.game_info.status}")
print(f"{game_data.away_team.name}: {game_data.away_team.score}")
print(f"{game_data.home_team.name}: {game_data.home_team.score}")

# 转换为字典格式
data_dict = game_data.to_dict()
```

### AI 智能分析

```python
import asyncio
from pm_nba_agent.agent import GameAnalyzer, GameContext, AnalysisConfig

async def analyze_game():
    # 配置分析器（默认从环境变量读取）
    config = AnalysisConfig(
        api_key="your-openai-api-key",
        model="gpt-4o-mini",
        analysis_interval=30.0,  # 正常分析间隔（秒）
        event_interval=15.0      # 事件触发间隔（秒）
    )

    analyzer = GameAnalyzer(config)
    context = GameContext(game_id="0022600123")

    # 更新上下文数据
    context.update_scoreboard({
        "status": "Live - Q3",
        "period": 3,
        "game_clock": "7:23",
        "home_team": {"name": "Lakers", "score": 78},
        "away_team": {"name": "Warriors", "score": 82}
    })

    # 流式生成分析
    if analyzer.should_analyze(context):
        async for chunk in analyzer.analyze_stream(context):
            print(chunk, end="", flush=True)

    await analyzer.close()

asyncio.run(analyze_game())
```

## 核心模块

### 比赛数据模块

#### 1. URL 解析

```python
from pm_nba_agent.parsers import parse_polymarket_url

url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"
event_info = parse_polymarket_url(url)

print(event_info.team1_abbr)  # 'ORL'
print(event_info.team2_abbr)  # 'CLE'
print(event_info.game_date)   # '2026-01-26'
```

#### 2. 球队信息查询

```python
from pm_nba_agent.nba import get_team_info

team = get_team_info('ORL')
print(team.full_name)  # 'Orlando Magic'
print(team.nickname)   # 'Magic'
```

#### 3. 比赛查找

```python
from pm_nba_agent.nba import find_game_by_teams_and_date

game_id = find_game_by_teams_and_date('ORL', 'CLE', '2026-01-26')
print(game_id)  # '0022600123'
```

#### 4. 实时数据获取

```python
from pm_nba_agent.nba import get_live_game_data

game_data = get_live_game_data('0022600123')
print(game_data.game_info.status)  # 'Live - Q3'
print(game_data.home_team.score)   # 89
```

### AI 分析模块

AI 分析模块提供基于 LLM 的智能实时比赛分析功能。

#### 核心组件

- **GameAnalyzer**: 主分析器，支持流式输出
- **GameContext**: 维护比赛状态并检测重要事件
- **LLMClient**: 异步 OpenAI 客户端，带重试逻辑
- **AnalysisConfig**: 配置管理，支持环境变量

#### 事件检测

分析器自动检测以下事件：

- **得分潮**: 单队连续得分 5 分以上
- **领先交换**: 双方领先优势互换
- **节次变化**: 进入新的节次或加时
- **三分球**: 三分球命中
- **扣篮**: 扣篮得分

#### 分析触发机制

- **基于时间**: 常规间隔（默认 30 秒）
- **基于事件**: 重要事件发生时使用更短间隔（默认 15 秒）
- **首次分析**: 一旦有数据即触发

## 配置说明

AI 分析模块可通过环境变量或代码进行配置：

### 环境变量

```bash
# OpenAI 配置
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
export OPENAI_MODEL="gpt-4o-mini"  # 默认模型

# 分析间隔（秒）
export ANALYSIS_INTERVAL="30"        # 正常间隔
export ANALYSIS_EVENT_INTERVAL="15"  # 事件触发间隔
```

### 代码配置

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

## 示例

运行包含的示例代码：

```bash
# 基础示例
python examples/example.py

# 详细用法
python examples/basic_usage.py

# 高级示例（批量查询）
python examples/advanced_usage.py

# 球员数据分析
python examples/player_stats_analysis.py

# 或使用 uv 运行
uv run python examples/example.py
```

## 项目结构

```
PM_NBA_Agent/
├── pm_nba_agent/              # 核心库
│   ├── parsers/               # URL 解析
│   │   └── polymarket_parser.py
│   ├── nba/                   # NBA 数据获取
│   │   ├── team_resolver.py   # 球队信息
│   │   ├── game_finder.py     # 比赛查找
│   │   └── live_stats.py      # 实时数据
│   ├── models/                # 数据模型
│   │   └── game_data.py
│   ├── agent/                 # AI 分析模块
│   │   ├── analyzer.py        # 比赛分析器
│   │   ├── context.py         # 比赛上下文管理
│   │   ├── llm_client.py      # OpenAI 客户端
│   │   ├── models.py          # 分析模型
│   │   └── prompts.py         # 提示词模板
│   └── main.py                # 主流程
├── examples/                  # 使用示例
│   ├── example.py
│   ├── basic_usage.py
│   ├── advanced_usage.py
│   └── player_stats_analysis.py
├── tests/                     # 测试脚本
│   ├── test_today_games.py
│   └── test_full_flow.py
├── pyproject.toml            # 项目配置
├── README.md                 # 文档（英文）
└── README_CN.md              # 文档（中文）
```

## 数据模型

### GameData

完整的比赛数据结构：

- `game_info`: 比赛基本信息（game_id, 日期, 状态, 节数, 比赛时钟）
- `home_team`: 主队统计（名称, 缩写, 比分, 详细统计）
- `away_team`: 客队统计
- `players`: 球员列表（姓名, 球队, 位置, 是否在场, 详细统计）

### GameContext

管理比赛状态以供分析：

- 跟踪比分板、详细统计和逐回合更新
- 自动检测重要事件
- 确定最佳分析时机
- 维护分析历史

### AnalysisConfig

分析器配置：

- OpenAI API 设置（key, base_url, model）
- 分析时机（间隔、事件触发）
- LLM 参数（max_tokens, temperature）

## 开发

### 运行测试

```bash
# 测试是脚本式，非 pytest
python tests/test_today_games.py
python tests/test_full_flow.py

# 使用 uv 运行
uv run python tests/test_today_games.py
```

### 构建包

```bash
python -m build
```

## 注意事项

1. **API 限流**: 代码已内置请求延迟 (0.6秒)，避免被 NBA API 限流
2. **比赛时间**: Live API 适用于当天比赛，历史或未来比赛使用 Stats API
3. **时区**: NBA 比赛时间为美国东部时间 (EST/EDT)
4. **比赛状态**: 1=未开始, 2=进行中, 3=已结束
5. **AI 分析**: 需要有效的 OpenAI API Key；未配置时会优雅降级

## 许可证

MIT License - 详见 [LICENSE](./LICENSE) 文件。

---

**注意**: 本项目使用 nba_api 获取数据。请尊重 NBA 的数据使用政策和 API 速率限制。
