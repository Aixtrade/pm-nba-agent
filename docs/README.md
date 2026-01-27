# NBA API 接口文档集

> 完整的 NBA API 接口文档，整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 📚 文档导航

### 🌟 [总览文档](./NBA_API_OVERVIEW.md)
**必读** - 项目介绍、安装配置、快速开始、数据格式说明

**适合对象**：所有用户
**主要内容**：
- 项目简介与特点
- 安装与配置
- 快速开始示例
- API 类型说明（Stats API vs Live API）
- 数据格式说明（DataFrame、JSON、字典）
- 快速查找表

---

## 📖 核心文档

### 📊 [静态数据模块](./API_STATIC_DATA.md)
**无需 HTTP 请求** - 球队和球员的本地查询

**适合场景**：
- 获取球员/球队 ID
- 本地搜索和筛选
- 构建选择器和下拉菜单

**主要端点**：
- **teams 模块**：9 个查询函数
- **players 模块**：7 个查询函数

**文档大小**：~750 行

---

### 🏀 [比赛数据接口](./API_GAME_DATA.md)
**21 个端点** - 比赛统计、Box Score、逐回合数据

**适合场景**：
- 比赛统计分析
- 球员比赛表现
- 逐回合事件追踪

**主要端点分类**：
- **Box Score 系列**（18 个变体）
  - 传统统计、高级统计、得分统计
  - 防守统计、杂项统计、使用率统计
  - 四因素统计、球员追踪统计
- **比赛详情**
  - PlayByPlayV2、GameRotation
  - WinProbabilityPBP

**文档大小**：~900 行

---

### 👤 [球员统计接口](./API_PLAYER_STATS.md)
**40 个端点** - 球员职业生涯、游戏日志、进阶统计

**适合场景**：
- 球员赛季报告
- 职业生涯分析
- 球员对比分析

**主要端点分类**：
- **职业生涯数据**：PlayerCareerStats、PlayerProfileV2
- **游戏日志**：PlayerGameLog
- **球员仪表板**：按关键时刻、对手、主客场等分类
- **进阶统计**：传球追踪、篮板追踪、投篮追踪、防守追踪
- **其他数据**：球员奖项、对比、估算指标

**文档大小**：~1050 行

---

### 🏆 [球队统计接口](./API_TEAM_STATS.md)
**12 个端点** - 球队统计、历史、名单

**适合场景**：
- 球队赛季报告
- 球队历史分析
- 主客场表现对比

**主要端点分类**：
- **球队基础数据**：TeamGameLog、TeamYearByYearStats
- **球队仪表板**：按关键时刻、对手、主客场等分类
- **球队历史**：FranchiseHistory、FranchiseLeaders
- **球队详情**：CommonTeamRoster、TeamInfoCommon

**文档大小**：~850 行

---

### 🏅 [联赛数据接口](./API_LEAGUE_DATA.md)
**20 个端点** - 排名、排行榜、联赛统计

**适合场景**：
- 联赛排行榜
- 全联盟数据对比
- MVP 候选分析

**主要端点分类**：
- **排名与排行**：LeagueStandings、LeagueLeaders
- **联赛球员统计**：LeagueDashPlayerStats 及各种细分
- **联赛球队统计**：LeagueDashTeamStats 及各种细分
- **比赛查找**：LeagueGameFinder、LeagueGameLog
- **其他功能**：SynergyPlayTypes、阵容可视化

**文档大小**：~900 行

---

### 🎯 [选秀及其他数据接口](./API_DRAFT_OTHER.md)
**43 个端点** - 选秀数据及综合功能端点

**适合场景**：
- 选秀球探报告
- 投篮分析
- 阵容优化
- 比赛预览

**主要端点分类**：
- **选秀相关**（7 个）：DraftHistory、DraftCombineStats 等
- **通用数据**（15 个）：CommonAllPlayers、ScoreboardV2 等
- **专项功能**（21 个）：
  - ShotChartDetail（投篮图表）
  - AssistTracker（助攻追踪）
  - DefenseHub（防守中心）
  - TeamDashLineups（阵容统计）

**文档大小**：~1000 行

---

### ⚡ [Live API 接口](./API_LIVE_ENDPOINTS.md)
**3+ 个端点** - 实时比赛数据

**适合场景**：
- 实时比分追踪
- 比赛进程监控
- 实时数据展示

**主要端点**：
- **ScoreBoard**：今日所有比赛的实时比分板
- **BoxScore**：特定比赛的实时详细统计
- **PlayByPlay**：特定比赛的实时逐回合数据

**特点**：
- 数据源：cdn.nba.com
- 延迟：10-30 秒
- 格式：纯 JSON
- 更新：实时更新

**文档大小**：~1300 行

---

## 📊 文档统计

| 文档 | 大小 | 行数（估算） | 端点数量 |
|------|------|-------------|---------|
| 总览文档 | 9.2 KB | ~250 行 | - |
| 静态数据模块 | 16 KB | ~750 行 | 16 个函数 |
| 比赛数据接口 | 17 KB | ~900 行 | 21 个端点 |
| 球员统计接口 | 21 KB | ~1050 行 | 40 个端点 |
| 球队统计接口 | 18 KB | ~850 行 | 12 个端点 |
| 联赛数据接口 | 18 KB | ~900 行 | 20 个端点 |
| 选秀及其他接口 | 20 KB | ~1000 行 | 43 个端点 |
| Live API 接口 | 28 KB | ~1300 行 | 3+ 个端点 |
| **总计** | **147 KB** | **~6000 行** | **139+ 个端点** |

---

## 🚀 快速开始

### 1. 安装 nba_api

```bash
pip install nba_api
```

### 2. 获取球员数据

```python
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats

# 查找球员 ID
lebron = players.find_players_by_full_name('LeBron James')[0]
player_id = lebron['id']

# 获取职业生涯数据
career = playercareerstats.PlayerCareerStats(player_id=player_id)
career_df = career.season_totals_regular_season.get_data_frame()

print(career_df[['SEASON_ID', 'TEAM_ABBREVIATION', 'PTS', 'REB', 'AST']])
```

### 3. 获取今日比赛

```python
from nba_api.live.nba.endpoints import scoreboard

# 获取实时比分板
board = scoreboard.ScoreBoard()
games = board.get_dict()['scoreboard']['games']

for game in games:
    away = game['awayTeam']
    home = game['homeTeam']
    print(f"{away['teamTricode']} {away['score']} @ {home['teamTricode']} {home['score']}")
```

---

## 🔍 按使用场景查找

### 数据分析
- [球员统计接口](./API_PLAYER_STATS.md) - 球员数据分析
- [球队统计接口](./API_TEAM_STATS.md) - 球队数据分析
- [联赛数据接口](./API_LEAGUE_DATA.md) - 联盟数据对比

### 实时追踪
- [Live API 接口](./API_LIVE_ENDPOINTS.md) - 实时比分和数据

### 历史查询
- [比赛数据接口](./API_GAME_DATA.md) - 历史比赛数据
- [选秀及其他接口](./API_DRAFT_OTHER.md) - 选秀历史

### 本地查询
- [静态数据模块](./API_STATIC_DATA.md) - 无需 API 的本地查询

---

## 📝 文档特点

### ✅ 完整性
- 覆盖 139+ 个端点
- 包含参数说明、返回值、使用示例
- 提供实际应用场景

### ✅ 中文化
- 所有说明使用中文
- 保留原始英文参数名
- 易于中文用户理解

### ✅ 实用性
- 丰富的代码示例
- 实际使用场景演示
- 最佳实践建议

### ✅ 结构化
- 按功能分类组织
- 清晰的目录导航
- 交叉引用链接

---

## 🔗 相关资源

### 官方资源
- **GitHub 项目**：https://github.com/swar/nba_api
- **PyPI 页面**：https://pypi.org/project/nba_api/
- **官方文档**：https://github.com/swar/nba_api/tree/master/docs

### 社区资源
- **问题反馈**：GitHub Issues
- **Stack Overflow**：标签 `nba-api`
- **社区讨论**：Slack 频道

---

## 📌 使用建议

### 1. 新手入门路径
1. 阅读 [总览文档](./NBA_API_OVERVIEW.md)
2. 学习 [静态数据模块](./API_STATIC_DATA.md)
3. 选择感兴趣的领域深入学习

### 2. 数据分析师
- 重点：[球员统计](./API_PLAYER_STATS.md)、[球队统计](./API_TEAM_STATS.md)、[联赛数据](./API_LEAGUE_DATA.md)
- 工具：DataFrame、pandas、数据可视化

### 3. 应用开发者
- 重点：[Live API](./API_LIVE_ENDPOINTS.md)、[比赛数据](./API_GAME_DATA.md)
- 工具：实时更新、API 集成、前端展示

### 4. 球探分析
- 重点：[选秀数据](./API_DRAFT_OTHER.md)、[球员统计](./API_PLAYER_STATS.md)
- 工具：试训数据、球员对比、历史分析

---

## ⚠️ 重要提示

1. **使用条款**：遵守 NBA.com 的使用条款
2. **请求频率**：避免过于频繁的 API 请求
3. **数据准确性**：API 数据可能有延迟或变更
4. **版本更新**：定期更新 nba_api 包以获取最新功能

---

## 📅 更新日志

- **2026-01-27**：完成所有8个核心文档
  - 总览文档
  - 静态数据模块文档
  - 比赛数据接口文档
  - 球员统计接口文档
  - 球队统计接口文档
  - 联赛数据接口文档
  - 选秀及其他数据接口文档
  - Live API 接口文档

---

## 🤝 贡献

欢迎提出改进建议和补充内容！

---

**祝您使用愉快！🏀**
