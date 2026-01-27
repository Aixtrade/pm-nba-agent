# NBA API 接口文档 - 总览

> 本文档整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 目录

- [项目简介](#项目简介)
- [安装与配置](#安装与配置)
- [快速开始](#快速开始)
- [API 类型说明](#api-类型说明)
- [数据格式说明](#数据格式说明)
- [接口分类索引](#接口分类索引)
- [使用建议](#使用建议)

---

## 项目简介

**nba_api** 是一个开源的 Python API 客户端库，用于访问 NBA.com 的官方接口。该项目致力于"使 NBA.com 的 API 易于访问并提供广泛的文档"。

### 主要特点

- ✅ 访问 NBA 官方历史统计数据（stats.nba.com）
- ✅ 获取 NBA 实时比赛数据（cdn.nba.com）
- ✅ 支持多种数据返回格式（DataFrame、JSON、字典）
- ✅ 提供静态数据模块，无需 HTTP 请求即可查询球员和球队信息
- ✅ 支持代理、自定义请求头和超时设置
- ✅ 支持 WNBA（女子篮球联赛）数据访问
- ✅ 包含 120+ 个已文档化的 Stats 端点
- ✅ MIT 开源许可证

### 项目统计

- **GitHub Stars**: 3.4k+
- **贡献者**: 37+
- **Stats API 端点**: 约 121 个
- **Live API 端点**: 3+ 个主要端点
- **许可证**: MIT License

---

## 安装与配置

### 基本安装

```bash
pip install nba_api
```

### 系统要求

- **Python 版本**: 3.10 或更高
- **必需依赖**: `requests`、`numpy`
- **可选依赖**: `pandas`（用于 DataFrame 功能）

### 使用条款

使用本库时必须遵守 NBA.com 的使用条款。

---

## 快速开始

### 示例 1：获取球员职业生涯统计

```python
from nba_api.stats.endpoints import playercareerstats

# Nikola Jokić 的 player_id 是 '203999'
career = playercareerstats.PlayerCareerStats(player_id='203999')

# 以 DataFrame 格式获取
career_df = career.get_data_frame()

# 以 JSON 格式获取
career_json = career.get_json()

# 以字典格式获取
career_dict = career.get_dict()
```

### 示例 2：使用静态数据模块（无需 HTTP 请求）

```python
from nba_api.stats.static import players, teams

# 查找球员（支持正则表达式，不区分大小写）
lebron = players.find_players_by_full_name('james')
active_players = players.get_active_players()
all_players = players.get_players()

# 查找球队
lakers = teams.find_teams_by_full_name('lakers')
all_teams = teams.get_teams()
team_by_city = teams.find_teams_by_city('Los Angeles')
```

### 示例 3：获取今日比分板（Live API）

```python
from nba_api.live.nba.endpoints import scoreboard

# 获取今日所有比赛
games = scoreboard.ScoreBoard()

# 以 JSON 格式获取
games_json = games.get_json()

# 以字典格式获取
games_dict = games.get_dict()
```

### 示例 4：使用高级选项（v1.1.0+）

```python
from nba_api.stats.endpoints import commonplayerinfo

# 支持代理、自定义请求头和超时设置
player_info = commonplayerinfo.CommonPlayerInfo(
    player_id=2544,  # LeBron James
    proxy='127.0.0.1:80',
    headers={'User-Agent': 'Custom Agent'},
    timeout=100  # 秒
)
```

---

## API 类型说明

### Stats API（历史统计数据）

- **数据源**: `stats.nba.com`
- **功能**: 提供历史统计数据、职业生涯数据、赛季统计等
- **端点数量**: 约 121 个已文档化的端点
- **主要类别**:
  - 比赛数据（Box Score 系列）
  - 球员数据（职业生涯、仪表板、游戏日志等）
  - 球队数据（统计、历史、名单等）
  - 联赛数据（排名、排行榜、联赛统计等）
  - 选秀数据（选秀历史、联合试训等）
  - 特殊功能（投篮图表、防守中心、协同进攻类型等）

### Live API（实时数据）

- **数据源**: `cdn.nba.com`
- **功能**: 获取当前比赛的实时信息、比分板、逐回合数据等
- **主要端点**:
  - **ScoreBoard**: 获取今日所有比赛的比分板
  - **BoxScore**: 获取特定比赛的详细统计数据
  - **PlayByPlay**: 获取比赛的逐回合详细数据

---

## 数据格式说明

nba_api 支持三种主要的数据输出格式：

### 1. Pandas DataFrame（数据框）

```python
# 获取单个数据集的 DataFrame
data_frame = endpoint.get_data_frame()

# 获取所有数据集的 DataFrame 列表
data_frames_list = endpoint.get_data_frames()
```

- **优点**: 便于数据分析和处理
- **要求**: 需要安装 pandas 库

### 2. JSON（JSON 字符串）

```python
# 获取单个数据集的 JSON
json_data = endpoint.get_json()

# 获取规范化的 JSON
normalized_json = endpoint.get_normalized_json()
```

- **优点**: 便于数据传输和存储
- **格式**: 字符串格式的 JSON

### 3. Dictionary（Python 字典）

```python
# 获取单个数据集的字典
dict_data = endpoint.get_dict()

# 获取规范化的字典
normalized_dict = endpoint.get_normalized_dict()
```

- **优点**: 便于在 Python 中直接操作
- **格式**: Python 原生字典类型

### 4. 完整响应

```python
# 获取完整响应
response = endpoint.get_response()
```

---

## 接口分类索引

以下是按功能分类的接口文档链接：

### 📊 [静态数据模块](./API_STATIC_DATA.md)
无需 HTTP 请求即可查询球员和球队信息
- **teams 模块**: 球队查询函数
- **players 模块**: 球员查询函数

### 🏀 [比赛数据接口](./API_GAME_DATA.md)
**21 个端点** - 比赛统计、Box Score、逐回合数据等
- **Box Score 系列**: 传统、高级、防守、得分等 18 个变体
- **比赛详情**: PlayByPlay、比赛相似性评分等

### 👤 [球员统计接口](./API_PLAYER_STATS.md)
**40 个端点** - 球员职业生涯、游戏日志、进阶统计等
- **职业生涯数据**: PlayerCareerStats 等
- **游戏日志**: PlayerGameLog 等
- **球员仪表板**: 按各种维度划分的统计
- **进阶统计**: 传球、篮板、投篮、防守等

### 🏆 [球队统计接口](./API_TEAM_STATS.md)
**12 个端点** - 球队统计、历史、名单等
- **常规球队统计**: LeagueDashTeamStats 等
- **球队历史**: FranchiseHistory、FranchiseLeaders 等
- **球队名单**: CommonTeamRoster 等

### 🏅 [联赛数据接口](./API_LEAGUE_DATA.md)
**20 个端点** - 排名、排行榜、联赛统计等
- **排名与排行**: LeagueStandings、LeagueLeaders 等
- **球员联赛统计**: LeagueDashPlayerStats 等
- **球队联赛统计**: LeagueHustleStatsTeam 等

### 🎯 [选秀及其他接口](./API_DRAFT_OTHER.md)
**43 个端点** - 选秀数据及综合功能端点
- **选秀相关**: DraftHistory、DraftBoard、DraftCombine 系列（7 个）
- **其他综合端点**: CommonAllPlayers、AssistTracker、DefenseHub 等（36 个）

### ⚡ [Live API 接口](./API_LIVE_ENDPOINTS.md)
**3+ 个端点** - 实时比赛数据
- **ScoreBoard**: 实时比分板
- **BoxScore**: 实时比赛统计
- **PlayByPlay**: 实时逐回合数据

---

## 使用建议

### 1. 选择合适的 API

- **历史数据查询**: 使用 Stats API
- **实时数据**: 使用 Live API
- **本地查询**: 使用静态数据模块（teams、players）

### 2. 数据格式选择

- **数据分析**: 使用 DataFrame 格式
- **数据存储/传输**: 使用 JSON 格式
- **程序内部处理**: 使用字典格式

### 3. 性能优化

- **减少 HTTP 请求**: 优先使用静态数据模块
- **设置合理超时**: 根据网络环境调整 timeout 参数
- **使用代理**: 在需要时配置代理服务器

### 4. 错误处理

```python
from nba_api.stats.endpoints import playercareerstats

try:
    career = playercareerstats.PlayerCareerStats(
        player_id='203999',
        timeout=30
    )
    data = career.get_data_frame()
except Exception as e:
    print(f"获取数据失败: {e}")
```

### 5. 遵守使用条款

- 不要过度频繁地请求 API
- 遵守 NBA.com 的使用条款和服务条款
- 合理使用缓存机制

---

## 快速查找表

### 按使用场景查找端点

| 场景 | 推荐端点 | 文档链接 |
|------|---------|---------|
| 查找球员 ID | `players.find_players_by_full_name()` | [静态数据](./API_STATIC_DATA.md) |
| 查找球队 ID | `teams.find_teams_by_full_name()` | [静态数据](./API_STATIC_DATA.md) |
| 球员职业生涯统计 | `PlayerCareerStats` | [球员统计](./API_PLAYER_STATS.md) |
| 球员本赛季比赛日志 | `PlayerGameLog` | [球员统计](./API_PLAYER_STATS.md) |
| 比赛详细数据 | `BoxScoreTraditionalV2` | [比赛数据](./API_GAME_DATA.md) |
| 今日比赛比分 | `ScoreBoard` (Live) | [Live API](./API_LIVE_ENDPOINTS.md) |
| 联赛排名 | `LeagueStandings` | [联赛数据](./API_LEAGUE_DATA.md) |
| 球队本赛季统计 | `LeagueDashTeamStats` | [球队统计](./API_TEAM_STATS.md) |
| 选秀历史 | `DraftHistory` | [选秀数据](./API_DRAFT_OTHER.md) |
| 比赛逐回合数据 | `PlayByPlay` (Live) | [Live API](./API_LIVE_ENDPOINTS.md) |

---

## 相关资源

- **GitHub 项目**: https://github.com/swar/nba_api
- **PyPI 页面**: https://pypi.org/project/nba_api/
- **问题反馈**: GitHub Issues
- **社区讨论**: Slack 频道
- **Stack Overflow**: 标签 `nba-api`

---

## 贡献与支持

欢迎社区贡献！特别是：
- 发现新端点或端点变更
- 改进文档和示例
- 报告 bug 和问题
- 提供使用案例

---

**注意**: NBA.com 的 API 在不断更新，本文档会持续更新以反映最新变化。
