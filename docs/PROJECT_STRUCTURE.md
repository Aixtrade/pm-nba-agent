# 项目结构说明

## 📁 目录结构

```
PM_NBA_Agent/
├── pm_nba_agent/          # 核心库（可导入的 Python 包）
│   ├── __init__.py
│   ├── main.py                # 主流程（一键获取完整数据）
│   ├── parsers/               # URL 解析模块
│   │   ├── __init__.py
│   │   └── polymarket_parser.py
│   ├── nba/                   # NBA API 交互模块
│   │   ├── __init__.py
│   │   ├── team_resolver.py   # 球队信息查询
│   │   ├── game_finder.py     # 比赛查找
│   │   └── live_stats.py      # 实时数据获取
│   └── models/                # 数据模型
│       ├── __init__.py
│       └── game_data.py       # GameData, TeamStats, PlayerStats
├── examples/                   # 使用示例
│   ├── README.md
│   ├── example.py             # 最简单的示例
│   ├── basic_usage.py         # 基础 API 使用
│   ├── advanced_usage.py      # 批量查询和分析
│   └── player_stats_analysis.py  # 球员数据分析
├── tests/                      # 测试脚本
│   ├── README.md
│   ├── test_today_games.py    # 查看今日所有比赛
│   └── test_full_flow.py      # 完整流程测试
├── .venv/                      # 虚拟环境（uv 管理）
├── pyproject.toml             # 项目配置和依赖
├── uv.lock                     # 依赖锁文件
└── README.md                   # 项目说明文档
```

## 📦 核心模块 (pm_nba_agent/)

### 1. parsers/polymarket_parser.py
**功能**: 解析 Polymarket NBA 事件 URL

```python
from pm_nba_agent.parsers import parse_polymarket_url

url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"
info = parse_polymarket_url(url)
# 返回: PolymarketEventInfo(team1_abbr='ORL', team2_abbr='CLE', game_date='2026-01-26')
```

### 2. nba/team_resolver.py
**功能**: 通过球队缩写获取详细信息

```python
from pm_nba_agent.nba import get_team_info

team = get_team_info('ORL')
# 返回: TeamInfo(id=..., full_name='Orlando Magic', ...)
```

### 3. nba/game_finder.py
**功能**: 查找比赛 ID 和今日比赛列表

```python
from pm_nba_agent.nba import find_game_by_teams_and_date, get_todays_games

# 查找特定比赛
game_id = find_game_by_teams_and_date('ORL', 'CLE', '2026-01-26')

# 获取今日所有比赛
games = get_todays_games()
```

### 4. nba/live_stats.py
**功能**: 获取实时比赛数据

```python
from pm_nba_agent.nba import get_live_game_data

game_data = get_live_game_data(game_id)
# 返回: GameData(game_info, home_team, away_team, players)
```

### 5. models/game_data.py
**数据模型**:
- `GameInfo`: 比赛基本信息（ID、状态、节数、时钟）
- `TeamStats`: 球队统计（比分、篮板、助攻、命中率等）
- `PlayerStats`: 球员统计（得分、篮板、助攻、在场状态等）
- `GameData`: 完整比赛数据容器

### 6. main.py
**一键获取**: 从 URL 到完整数据的主流程

```python
from pm_nba_agent.main import get_game_data_from_url

game_data = get_game_data_from_url(url)
```

## 📚 Examples 目录

### example.py
最简单的使用示例，5 行代码获取比赛数据。

### basic_usage.py
展示核心 API 的分步使用：
1. URL 解析
2. 球队信息查询
3. 比赛查找
4. 数据获取

### advanced_usage.py
高级功能：
- 批量查询今日所有比赛
- 按状态分类（进行中/已结束/未开始）
- 数据统计和分析

### player_stats_analysis.py
球员数据分析：
- 得分/篮板/助攻排行榜
- 投篮命中率分析
- 效率值计算
- 当前在场球员显示

## 🧪 Tests 目录

### test_today_games.py
查询今天所有 NBA 比赛，用于：
- 验证 API 连接
- 查看可用比赛
- 获取 game_id 用于测试

### test_full_flow.py
完整流程测试：
- 从 Polymarket URL 开始
- 验证所有模块正常工作
- 输出详细数据和 JSON

## 🛠️ 开发指南

### 安装开发环境

```bash
# 使用 uv 安装依赖
uv sync

# 以可编辑模式安装项目
uv pip install -e .
```

### 运行示例

```bash
python examples/example.py
python examples/basic_usage.py
python examples/advanced_usage.py
python examples/player_stats_analysis.py
```

### 运行测试

```bash
python tests/test_today_games.py
python tests/test_full_flow.py
```

### 添加新功能

1. **新的数据解析器**: 添加到 `pm_nba_agent/parsers/`
2. **新的 NBA API 功能**: 添加到 `pm_nba_agent/nba/`
3. **新的数据模型**: 添加到 `pm_nba_agent/models/`
4. **新的使用示例**: 添加到 `examples/`
5. **新的测试**: 添加到 `tests/`

## 📝 代码规范

- 所有模块都有 docstring
- 函数包含类型提示
- 使用 dataclass 定义数据模型
- API 调用包含延迟（0.6秒）避免限流
- 错误处理和降级策略

## 🎯 主要数据流

```
Polymarket URL
    ↓ [parsers.parse_polymarket_url()]
PolymarketEventInfo (team1, team2, date)
    ↓ [nba.get_team_info()]
TeamInfo (full_name, id, ...)
    ↓ [nba.find_game_by_teams_and_date()]
game_id
    ↓ [nba.get_live_game_data()]
GameData (完整比赛数据)
    ↓ [.to_dict()]
JSON 格式数据
```

## 📊 输出数据示例

```json
{
  "game_info": {
    "game_id": "0022500658",
    "status": "Live - Q4",
    "period": 4,
    "game_clock": "PT05M23.00S"
  },
  "teams": {
    "home": {
      "name": "Cavaliers",
      "score": 102,
      "statistics": {...}
    },
    "away": {...}
  },
  "players": [...]
}
```
