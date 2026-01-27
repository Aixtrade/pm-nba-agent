# 快速开始指南

## 🚀 5 分钟上手

### 1. 安装

```bash
# 克隆项目后进入目录
cd PM_NBA_Agent

# 使用 uv 安装依赖
uv sync

# 以可编辑模式安装项目
uv pip install -e .
```

### 2. 最简单的使用

创建文件 `my_first_script.py`：

```python
from pm_nba_agent.main import get_game_data_from_url

# Polymarket 比赛 URL
url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"

# 一键获取数据
game_data = get_game_data_from_url(url, verbose=False)

# 显示结果
if game_data:
    print(f"🏀 {game_data.away_team.name} @ {game_data.home_team.name}")
    print(f"📊 {game_data.away_team.score} - {game_data.home_team.score}")
    print(f"⏰ {game_data.game_info.status}")
```

运行：
```bash
python my_first_script.py
```

### 3. 查看今天的比赛

```bash
python tests/test_today_games.py
```

输出示例：
```
找到 7 场比赛:

1. ORL @ CLE
   Game ID: 0022500658
   状态: Live - Q4
   比分: 91 - 102
...
```

### 4. 运行完整示例

```bash
# 基础示例
python examples/example.py

# 详细步骤
python examples/basic_usage.py

# 批量查询分析
python examples/advanced_usage.py

# 球员数据分析
python examples/player_stats_analysis.py
```

## 📖 常用场景

### 场景 1: 获取特定比赛数据

```python
from pm_nba_agent.main import get_game_data_from_url

url = "https://polymarket.com/event/nba-xxx-xxx-2026-01-27"
game_data = get_game_data_from_url(url)

# 访问数据
print(game_data.game_info.status)      # 比赛状态
print(game_data.home_team.score)       # 主队比分
print(len(game_data.players))          # 球员数量
```

### 场景 2: 分步获取数据

```python
from pm_nba_agent.parsers import parse_polymarket_url
from pm_nba_agent.nba import (
    get_team_info,
    find_game_by_teams_and_date,
    get_live_game_data
)

# 步骤 1: 解析 URL
info = parse_polymarket_url(url)

# 步骤 2: 获取球队信息
team1 = get_team_info(info.team1_abbr)

# 步骤 3: 查找比赛
game_id = find_game_by_teams_and_date(
    info.team1_abbr,
    info.team2_abbr,
    info.game_date
)

# 步骤 4: 获取数据
game_data = get_live_game_data(game_id)
```

### 场景 3: 批量查询今天所有比赛

```python
from pm_nba_agent.nba.game_finder import get_todays_games

games = get_todays_games()

for game in games:
    print(f"{game['away_team']} @ {game['home_team']}")
    print(f"  状态: {game['status']}")
    print(f"  比分: {game['away_score']} - {game['home_score']}")
```

### 场景 4: 分析球员数据

```python
game_data = get_game_data_from_url(url)

# 得分榜
top_scorers = sorted(
    game_data.players,
    key=lambda x: x.stats['points'],
    reverse=True
)[:5]

for player in top_scorers:
    print(f"{player.name}: {player.stats['points']}分")

# 在场球员
on_court = [p for p in game_data.players if p.on_court]
print(f"当前在场: {len(on_court)} 人")
```

### 场景 5: 导出为 JSON

```python
game_data = get_game_data_from_url(url)
data_dict = game_data.to_dict()

import json
print(json.dumps(data_dict, indent=2, ensure_ascii=False))
```

## 🔍 查找比赛 ID

如果你只有球队缩写和日期：

```python
from pm_nba_agent.nba import find_game_by_teams_and_date

game_id = find_game_by_teams_and_date('LAL', 'GSW', '2026-01-27')
print(f"Game ID: {game_id}")
```

## 📊 数据结构

### GameData 包含：

```python
game_data.game_info       # GameInfo 对象
    .game_id             # 比赛 ID
    .status              # 状态（Live - Q3, Final, 等）
    .period              # 节数
    .game_clock          # 比赛时钟

game_data.home_team       # TeamStats 对象
    .name               # 球队名称
    .score              # 比分
    .statistics         # 详细统计（字典）

game_data.away_team       # 同上

game_data.players         # List[PlayerStats]
    [0].name            # 球员姓名
    [0].team            # 所属球队
    [0].on_court        # 是否在场
    [0].stats           # 详细统计（字典）
```

## ⚠️ 常见问题

### Q: 找不到比赛？
A: 确保日期格式正确（YYYY-MM-DD），比赛可能还未开始或已经是几天前的比赛。

### Q: SSL 错误？
A: 这是网络波动导致的，重试即可。代码会自动从 Live API 降级到 Stats API。

### Q: API 限流？
A: 代码已内置 0.6 秒延迟。如果仍然被限流，增加延迟时间。

### Q: 数据不是实时的？
A: Live API 会有小延迟（通常 10-30 秒），这是 NBA API 的特性。

## 📚 更多资源

- 完整文档：`README.md`
- 项目结构：`PROJECT_STRUCTURE.md`
- 示例代码：`examples/`
- 测试脚本：`tests/`

## 💡 提示

1. 使用 `verbose=True` 查看详细执行过程
2. 优先使用 `get_game_data_from_url()` 一键获取数据
3. 批量查询时记得添加延迟避免限流
4. 使用 `get_todays_games()` 查看今天有哪些比赛

祝使用愉快！🎉
