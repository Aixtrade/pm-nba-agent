# PM NBA Agent

专门实时分析 NBA 的 AI Agent，从 Polymarket 事件 URL 解析 NBA 比赛信息，并通过 nba_api 获取实时比赛数据。

## 安装

使用 uv 管理虚拟环境和依赖：

```bash
# 创建虚拟环境并安装依赖
uv sync

# 或者手动创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS

# 安装依赖
uv add nba_api pandas
```

## 快速开始

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

## 运行示例

```bash
# 基础示例
python examples/example.py

# 详细用法
python examples/basic_usage.py

# 高级示例（批量查询）
python examples/advanced_usage.py

# 球员数据分析
python examples/player_stats_analysis.py
```

## 项目结构

```
PM_NBA_Agent/
├── pm_nba_agent/          # 核心库
│   ├── parsers/               # URL 解析
│   │   └── polymarket_parser.py
│   ├── nba/                   # NBA 数据获取
│   │   ├── team_resolver.py   # 球队信息
│   │   ├── game_finder.py     # 比赛查找
│   │   └── live_stats.py      # 实时数据
│   ├── models/                # 数据模型
│   │   └── game_data.py
│   └── main.py                # 主流程
├── examples/                   # 使用示例
│   ├── example.py             # 简单示例
│   ├── basic_usage.py         # 基础用法
│   ├── advanced_usage.py      # 高级用法
│   └── player_stats_analysis.py  # 数据分析
├── tests/                      # 测试脚本
│   ├── test_today_games.py    # 今日比赛
│   └── test_full_flow.py      # 完整流程测试
├── pyproject.toml             # 项目配置
└── README.md                   # 项目文档
```

## 核心功能

### 1. URL 解析

```python
from pm_nba_agent.parsers import parse_polymarket_url

url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"
event_info = parse_polymarket_url(url)

print(event_info.team1_abbr)  # 'ORL'
print(event_info.team2_abbr)  # 'CLE'
print(event_info.game_date)   # '2026-01-26'
```

### 2. 球队信息查询

```python
from pm_nba_agent.nba import get_team_info

team = get_team_info('ORL')
print(team.full_name)  # 'Orlando Magic'
print(team.nickname)   # 'Magic'
```

### 3. 比赛查找

```python
from pm_nba_agent.nba import find_game_by_teams_and_date

game_id = find_game_by_teams_and_date('ORL', 'CLE', '2026-01-26')
print(game_id)  # '0022600123'
```

### 4. 实时数据获取

```python
from pm_nba_agent.nba import get_live_game_data

game_data = get_live_game_data('0022600123')
print(game_data.game_info.status)  # 'Live - Q3'
print(game_data.home_team.score)   # 89
```

## 数据结构

### GameData

完整的比赛数据，包含：

- `game_info`: 比赛基本信息（game_id, 日期, 状态, 节数, 比赛时钟）
- `home_team`: 主队统计（名称, 缩写, 比分, 详细统计）
- `away_team`: 客队统计
- `players`: 球员列表（姓名, 球队, 位置, 是否在场, 详细统计）

## 注意事项

1. **API 限流**: 代码已内置请求延迟 (0.6秒)，避免被 NBA API 限流
2. **比赛时间**: Live API 适用于当天比赛，历史或未来比赛使用 Stats API
3. **时区**: NBA 比赛时间为美国东部时间 (EST/EDT)
4. **比赛状态**: 1=未开始, 2=进行中, 3=已结束

## License

MIT
