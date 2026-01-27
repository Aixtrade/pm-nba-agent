# NBA API - 球队统计接口文档

> 本文档整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 目录

- [概述](#概述)
- [球队基础数据](#球队基础数据)
- [球队仪表板](#球队仪表板)
- [球队历史数据](#球队历史数据)
- [球队详细信息](#球队详细信息)
- [使用指南](#使用指南)

---

## 概述

球队统计接口提供了约 12 个端点，涵盖球队的各维度数据：

### 主要分类

1. **球队基础数据**：球队统计、排名、对阵记录
2. **球队仪表板**：按多种维度划分的详细统计
3. **球队历史数据**：球队历史、领袖、冠军记录
4. **球队详细信息**：球队名单、基本信息、赛程

**关键特点：**
- ✅ 大多数端点需要 `team_id` 参数
- ✅ 支持按赛季、比赛类型筛选
- ✅ 提供球队整体和球员贡献数据
- ✅ 包含历史和当前数据

---

## 球队基础数据

### 1. TeamGameLog（球队比赛日志）

**端点描述：** 获取球队某个赛季的逐场比赛统计

**URL：** `https://stats.nba.com/stats/teamgamelog`

**参数：**

| 参数名 | Python 变量名 | 类型 | 必需 | 说明 |
|--------|-------------|------|------|------|
| TeamID | team_id | string | ✓ | 球队 ID |
| Season | season | string | ✓ | 赛季（如 "2023-24"） |
| SeasonType | season_type | string | ✓ | 赛季类型 |

**SeasonType 可选值：**
- `Regular Season`：常规赛
- `Playoffs`：季后赛
- `Pre Season`：季前赛

**返回数据集：**

#### TeamGameLog（比赛日志）
包含字段：
- **比赛信息**：SEASON_ID、GAME_ID、GAME_DATE、MATCHUP、WL（胜负）
- **统计数据**：MIN、FGM、FGA、FG_PCT、FG3M、FG3A、FG3_PCT、FTM、FTA、FT_PCT
- **全面数据**：OREB、DREB、REB、AST、STL、BLK、TOV、PF、PTS、PLUS_MINUS

**使用示例：**
```python
from nba_api.stats.endpoints import teamgamelog

# 获取勇士队 2023-24 赛季比赛日志
gamelog = teamgamelog.TeamGameLog(
    team_id='1610612744',
    season='2023-24',
    season_type_all_star='Regular Season'
)

games = gamelog.team_game_log.get_data_frame()

# 查看最近10场比赛
recent = games.head(10)
print(recent[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST']])

# 统计胜率
wins = (games['WL'] == 'W').sum()
total = len(games)
print(f"战绩: {wins}-{total-wins} ({wins/total:.1%})")
```

---

### 2. TeamYearByYearStats（球队逐年统计）

**端点描述：** 获取球队历年的赛季统计数据

**URL：** `https://stats.nba.com/stats/teamyearbyyearstats`

**参数：**
- **TeamID**（team_id）：球队 ID
- **LeagueID**（league_id）：联赛 ID
- **PerMode**（per_mode）：统计模式（Totals/PerGame等）
- **SeasonType**（season_type）：赛季类型

**返回数据集：**

#### TeamStats（球队统计）
各赛季的统计数据，包含：
- **赛季信息**：YEAR、TEAM_ID、TEAM_CITY、TEAM_NAME
- **比赛数据**：GP、WINS、LOSSES、WIN_PCT
- **统计数据**：PTS、FGM、FGA、FG_PCT、REB、AST、STL、BLK、TOV

**使用示例：**
```python
from nba_api.stats.endpoints import teamyearbyyearstats

stats = teamyearbyyearstats.TeamYearByYearStats(
    team_id='1610612744',
    per_mode='PerGame'
)

yearly = stats.team_stats.get_data_frame()

# 查看近10年数据
print(yearly[['YEAR', 'GP', 'WINS', 'LOSSES', 'WIN_PCT', 'PTS', 'REB', 'AST']].head(10))

# 找出最佳赛季
best_season = yearly.loc[yearly['WIN_PCT'].idxmax()]
print(f"\n最佳赛季: {best_season['YEAR']}, 战绩: {best_season['WINS']}-{best_season['LOSSES']}")
```

---

### 3. TeamVsPlayer（球队对阵球员）

**端点描述：** 获取球队对阵特定球员时的统计表现

**URL：** `https://stats.nba.com/stats/teamvsplayer`

**参数：**
- **TeamID**（team_id）：球队 ID
- **VsPlayerID**（vs_player_id）：对阵球员 ID
- **Season**（season）：赛季

**使用场景：** 分析球队如何防守某个明星球员

---

## 球队仪表板

### 4. TeamDashboardByClutch（关键时刻表现）

**端点描述：** 获取球队在关键时刻的统计表现

**URL：** `https://stats.nba.com/stats/teamdashboardbyclutch`

**关键时刻定义：** 第四节或加时最后 5 分钟，分差在 5 分以内

**参数：**
- **TeamID**（team_id）：球队 ID
- **Season**（season）：赛季
- **MeasureType**（measure_type）：测量类型
- **PerMode**（per_mode）：统计模式

**MeasureType 可选值：**
- `Base`：基础数据
- `Advanced`：高级数据
- `Four Factors`：四因素
- `Scoring`：得分数据
- `Opponent`：对手数据

**返回数据集：**
- **OverallTeamDashboard**：整体表现
- **ClutchTeamDashboard**：关键时刻表现
- **NonClutchTeamDashboard**：非关键时刻表现

**使用示例：**
```python
from nba_api.stats.endpoints import teamdashboardbyclutch

clutch = teamdashboardbyclutch.TeamDashboardByClutch(
    team_id='1610612744',
    season='2023-24',
    measure_type='Base'
)

clutch_stats = clutch.clutch_team_dashboard.get_data_frame()
overall = clutch.overall_team_dashboard.get_data_frame()

print("关键时刻表现:")
print(clutch_stats[['GP', 'W', 'L', 'W_PCT', 'PTS', 'FG_PCT', 'PLUS_MINUS']])

print("\n整体表现:")
print(overall[['GP', 'W', 'L', 'W_PCT', 'PTS', 'FG_PCT']])
```

---

### 5. TeamDashboardByGameSplits（按比赛分类）

**端点描述：** 获取球队按不同比赛条件分类的统计

**URL：** `https://stats.nba.com/stats/teamdashboardbygamesplits`

**分类维度：**
- **主场 vs 客场**
- **胜利 vs 失败**
- **按月份**
- **全明星赛前后**
- **赛前休息天数**

**返回数据集：**
- **OverallTeamDashboard**：整体数据
- **LocationTeamDashboard**：主客场数据
- **WinsLossesTeamDashboard**：胜负场数据
- **MonthTeamDashboard**：按月份数据
- **PrePostAllStarTeamDashboard**：全明星前后数据
- **DaysRestTeamDashboard**：按休息天数数据

**使用示例：**
```python
from nba_api.stats.endpoints import teamdashboardbygamesplits

splits = teamdashboardbygamesplits.TeamDashboardByGameSplits(
    team_id='1610612744',
    season='2023-24'
)

# 主客场对比
location = splits.location_team_dashboard.get_data_frame()
print("主客场对比:")
print(location[['GROUP_VALUE', 'GP', 'W', 'L', 'W_PCT', 'PTS', 'OPP_PTS']])

# 按月份表现
monthly = splits.month_team_dashboard.get_data_frame()
print("\n按月份表现:")
print(monthly[['GROUP_VALUE', 'GP', 'W', 'L', 'W_PCT', 'PTS']])
```

---

### 6. TeamDashboardByGeneralSplits（按一般分类）

**端点描述：** 按赛季类型、半场、时期等一般条件分类

**分类维度：**
- 赛季类型
- 上半场/下半场
- 各节/加时
- 领先/落后/持平

---

### 7. TeamDashboardByOpponent（对阵对手）

**端点描述：** 获取球队对阵各支球队的统计表现

**URL：** `https://stats.nba.com/stats/teamdashboardbyopponent`

**返回数据集：**
- **OverallTeamDashboard**：整体数据
- **OpponentTeamDashboard**：对阵各队数据（29 行，每支对手一行）

**使用示例：**
```python
from nba_api.stats.endpoints import teamdashboardbyopponent

opponent = teamdashboardbyopponent.TeamDashboardByOpponent(
    team_id='1610612744',
    season='2023-24'
)

vs_teams = opponent.opponent_team_dashboard.get_data_frame()

# 对阵战绩最好的球队
best_matchups = vs_teams.sort_values('W_PCT', ascending=False)
print(best_matchups[['VS_TEAM_NAME', 'GP', 'W', 'L', 'W_PCT', 'PLUS_MINUS']].head(10))

# 对阵战绩最差的球队
worst_matchups = vs_teams.sort_values('W_PCT')
print(worst_matchups[['VS_TEAM_NAME', 'GP', 'W', 'L', 'W_PCT']].head(5))
```

---

### 8. TeamDashboardByShootingSplits（按投篮分类）

**端点描述：** 按投篮距离、区域、类型分类

**分类维度：**
- 投篮距离（5ft、10ft、15ft 等）
- 投篮区域（油漆区、中距离、三分等）
- 投篮类型（跳投、上篮、扣篮等）
- 助攻情况

---

### 9. TeamDashboardByYearOverYear（逐年对比）

**端点描述：** 球队各赛季数据的年度对比

**使用场景：** 观察球队发展轨迹和表现变化

---

## 球队历史数据

### 10. FranchiseHistory（球队历史）

**端点描述：** 获取球队的完整历史记录

**URL：** `https://stats.nba.com/stats/franchisehistory`

**参数：**
- **LeagueID**（league_id）：联赛 ID（默认 "00"）

**返回数据集：**

#### FranchiseHistory（球队历史）
包含字段：
- **TEAM_ID**：球队 ID
- **TEAM_CITY**：城市
- **TEAM_NAME**：球队名称
- **START_YEAR**/**END_YEAR**：起止年份
- **YEARS**：存续年数
- **GAMES**：总比赛场次
- **WINS**/**LOSSES**：胜负场数
- **WIN_PCT**：胜率
- **PO_APPEARANCES**：季后赛出现次数
- **DIV_TITLES**：分区冠军数
- **CONF_TITLES**：联盟冠军数
- **LEAGUE_TITLES**：总冠军数

**使用示例：**
```python
from nba_api.stats.endpoints import franchisehistory

history = franchisehistory.FranchiseHistory()
franchise = history.franchise_history.get_data_frame()

# 查找特定球队
warriors = franchise[franchise['TEAM_NAME'] == 'Warriors']
print(warriors[['TEAM_CITY', 'START_YEAR', 'END_YEAR', 'WINS', 'LOSSES',
                'WIN_PCT', 'LEAGUE_TITLES']])

# 总冠军最多的球队
most_titles = franchise.sort_values('LEAGUE_TITLES', ascending=False)
print(most_titles[['TEAM_NAME', 'LEAGUE_TITLES', 'CONF_TITLES', 'DIV_TITLES']].head(10))
```

---

### 11. FranchiseLeaders（球队历史领袖）

**端点描述：** 获取球队历史上各项统计的领袖

**URL：** `https://stats.nba.com/stats/franchiseleaders`

**参数：**
- **TeamID**（team_id）：球队 ID

**返回数据集：**

#### FranchiseLeaders（各项领袖）
包含各项统计（得分、篮板、助攻等）的历史前列球员

**使用示例：**
```python
from nba_api.stats.endpoints import franchiseleaders

leaders = franchiseleaders.FranchiseLeaders(team_id='1610612744')
franchise_leaders = leaders.franchise_leaders.get_data_frame()

print("球队历史领袖:")
print(franchise_leaders)
```

---

### 12. FranchisePlayers（球队历史球员）

**端点描述：** 获取曾效力于某球队的所有球员列表

**URL：** `https://stats.nba.com/stats/franchiseplayers`

**参数：**
- **TeamID**（team_id）：球队 ID

**返回数据：** 所有曾效力球员的基本信息和在队统计

---

## 球队详细信息

### 13. CommonTeamRoster（球队名单）

**端点描述：** 获取球队当前赛季的球员名单

**URL：** `https://stats.nba.com/stats/commonteamroster`

**参数：**
- **TeamID**（team_id）：球队 ID
- **Season**（season）：赛季

**返回数据集：**

#### CommonTeamRoster（球队名单）
包含字段：
- **PLAYER**：球员姓名
- **PLAYER_ID**：球员 ID
- **NUM**：球衣号码
- **POSITION**：位置
- **HEIGHT**：身高
- **WEIGHT**：体重
- **BIRTH_DATE**：出生日期
- **AGE**：年龄
- **EXP**：NBA 经验
- **SCHOOL**：学校

#### Coaches（教练组）
球队教练组成员信息

**使用示例：**
```python
from nba_api.stats.endpoints import commonteamroster

roster = commonteamroster.CommonTeamRoster(
    team_id='1610612744',
    season='2023-24'
)

players = roster.common_team_roster.get_data_frame()

print("球队名单:")
print(players[['PLAYER', 'NUM', 'POSITION', 'HEIGHT', 'AGE', 'EXP']])

# 按位置分组
print("\n按位置统计:")
print(players.groupby('POSITION').size())

# 教练组
coaches = roster.coaches.get_data_frame()
print("\n教练组:")
print(coaches)
```

---

### 14. TeamInfoCommon（球队基本信息）

**端点描述：** 获取球队的基本信息和本赛季统计

**URL：** `https://stats.nba.com/stats/teaminfocommon`

**参数：**
- **TeamID**（team_id）：球队 ID
- **Season**（season）：赛季

**返回数据集：**

#### TeamInfoCommon（基本信息）
包含字段：
- **TEAM_ID**、**TEAM_CITY**、**TEAM_NAME**、**TEAM_ABBREVIATION**
- **TEAM_CONFERENCE**：所属联盟（东部/西部）
- **TEAM_DIVISION**：所属分区
- **W**/**L**：胜负场
- **W_PCT**：胜率
- **CONF_RANK**：联盟排名
- **DIV_RANK**：分区排名

#### TeamSeasonRanks（赛季排名）
球队各项统计在联盟中的排名

**使用示例：**
```python
from nba_api.stats.endpoints import teaminfocommon

info = teaminfocommon.TeamInfoCommon(
    team_id='1610612744',
    season='2023-24'
)

team_info = info.team_info_common.get_data_frame()
print("球队信息:")
print(team_info[['TEAM_NAME', 'TEAM_CONFERENCE', 'TEAM_DIVISION',
                 'W', 'L', 'W_PCT', 'CONF_RANK', 'DIV_RANK']])

rankings = info.team_season_ranks.get_data_frame()
print("\n联盟排名:")
print(rankings[['PTS_RANK', 'REB_RANK', 'AST_RANK', 'OPP_PTS_RANK']])
```

---

### 15. TeamDetails（球队详情）

**端点描述：** 获取球队的详细历史信息

**URL：** `https://stats.nba.com/stats/teamdetails`

**返回数据：** 球队历史背景、主场、老板、总经理等信息

---

## 使用指南

### 1. 如何获取 Team ID

```python
from nba_api.stats.static import teams

# 方法1：通过缩写查找
warriors = teams.find_team_by_abbreviation('GSW')
team_id = warriors['id']  # 1610612744

# 方法2：通过城市查找
la_teams = teams.find_teams_by_city('Los Angeles')
for team in la_teams:
    print(f"{team['full_name']}: {team['id']}")

# 方法3：通过全名查找
lakers = teams.find_teams_by_full_name('Lakers')
print(lakers[0]['id'])
```

### 2. 完整球队分析示例

```python
from nba_api.stats.endpoints import (
    teamgamelog,
    teamdashboardbyclutch,
    teamdashboardbyopponent,
    commonteamroster
)

team_id = '1610612744'  # 勇士队
season = '2023-24'

# 1. 比赛日志
gamelog = teamgamelog.TeamGameLog(
    team_id=team_id,
    season=season
)
games = gamelog.team_game_log.get_data_frame()

# 2. 关键时刻表现
clutch = teamdashboardbyclutch.TeamDashboardByClutch(
    team_id=team_id,
    season=season
)
clutch_stats = clutch.clutch_team_dashboard.get_data_frame()

# 3. 对阵各队表现
opponents = teamdashboardbyopponent.TeamDashboardByOpponent(
    team_id=team_id,
    season=season
)
vs_teams = opponents.opponent_team_dashboard.get_data_frame()

# 4. 球队名单
roster = commonteamroster.CommonTeamRoster(
    team_id=team_id,
    season=season
)
players = roster.common_team_roster.get_data_frame()

# 综合分析
print(f"赛季战绩: {len(games[games['WL']=='W'])}-{len(games[games['WL']=='L'])}")
print(f"场均得分: {games['PTS'].mean():.1f}")
print(f"关键时刻胜率: {clutch_stats['W_PCT'].iloc[0]:.1%}")
print(f"球队人数: {len(players)}")
```

### 3. 主客场优势分析

```python
from nba_api.stats.endpoints import teamdashboardbygamesplits

splits = teamdashboardbygamesplits.TeamDashboardByGameSplits(
    team_id='1610612744',
    season='2023-24',
    measure_type='Advanced'
)

location = splits.location_team_dashboard.get_data_frame()

# 提取主客场数据
home = location[location['GROUP_VALUE'] == 'Home']
away = location[location['GROUP_VALUE'] == 'Road']

print("主场表现:")
print(home[['W', 'L', 'W_PCT', 'OFF_RATING', 'DEF_RATING', 'NET_RATING']])

print("\n客场表现:")
print(away[['W', 'L', 'W_PCT', 'OFF_RATING', 'DEF_RATING', 'NET_RATING']])

# 计算主场优势
home_adv = home['NET_RATING'].iloc[0] - away['NET_RATING'].iloc[0]
print(f"\n主场优势（净效率差）: {home_adv:+.1f}")
```

### 4. 对阵分析

```python
from nba_api.stats.endpoints import teamdashboardbyopponent

opponent = teamdashboardbyopponent.TeamDashboardByOpponent(
    team_id='1610612744',
    season='2023-24'
)

vs_teams = opponent.opponent_team_dashboard.get_data_frame()

# 找出克星和鱼腩
print("战绩最好的对手（最强克星）:")
best = vs_teams.sort_values('W_PCT', ascending=False).head(5)
print(best[['VS_TEAM_NAME', 'GP', 'W', 'L', 'W_PCT']])

print("\n战绩最差的对手（最大苦主）:")
worst = vs_teams.sort_values('W_PCT').head(5)
print(worst[['VS_TEAM_NAME', 'GP', 'W', 'L', 'W_PCT']])

# 分差分析
print("\n分差最大的对手:")
biggest_margin = vs_teams.sort_values('PLUS_MINUS', ascending=False).head(5)
print(biggest_margin[['VS_TEAM_NAME', 'GP', 'PLUS_MINUS', 'PTS', 'OPP_PTS']])
```

### 5. 球队历史分析

```python
from nba_api.stats.endpoints import (
    franchisehistory,
    franchiseleaders
)

# 所有球队历史
history = franchisehistory.FranchiseHistory()
all_teams = history.franchise_history.get_data_frame()

# 按胜率排序
top_teams = all_teams.sort_values('WIN_PCT', ascending=False)
print("历史胜率最高的球队:")
print(top_teams[['TEAM_NAME', 'TEAM_CITY', 'YEARS', 'WIN_PCT',
                 'LEAGUE_TITLES']].head(10))

# 特定球队的历史领袖
leaders = franchiseleaders.FranchiseLeaders(team_id='1610612744')
team_leaders = leaders.franchise_leaders.get_data_frame()
print("\n球队历史领袖:")
print(team_leaders)
```

---

## 常见使用场景

### 场景 1：赛季球队报告
```python
# 比赛日志 + 主客场表现 + 对阵分析 + 关键时刻
```

### 场景 2：球队对比分析
```python
# 多个球队的相同指标对比
```

### 场景 3：球队建设分析
```python
# 球队名单 + 历年数据 + 选秀历史
```

### 场景 4：投注分析
```python
# 主客场差异 + 对阵历史 + 休息天数影响
```

---

## 注意事项

1. **Team ID**：使用静态模块获取正确的球队 ID
2. **赛季格式**：必须是 "YYYY-YY" 格式（如 "2023-24"）
3. **搬迁球队**：某些球队有多个城市/名称历史记录
4. **数据完整性**：历史数据可能不完整
5. **请求频率**：避免过于频繁的请求

---

## 相关资源

- [总览文档](./NBA_API_OVERVIEW.md)
- [静态数据模块](./API_STATIC_DATA.md)
- [比赛数据接口](./API_GAME_DATA.md)
- [球员统计接口](./API_PLAYER_STATS.md)
- [联赛数据接口](./API_LEAGUE_DATA.md)

**GitHub 端点文档：**
- [TeamGameLog](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/teamgamelog.md)
- [TeamDashboard 系列](https://github.com/swar/nba_api/tree/master/docs/nba_api/stats/endpoints)
- [FranchiseHistory](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/franchisehistory.md)
