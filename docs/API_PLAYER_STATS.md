# NBA API - 球员统计接口文档

> 本文档整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 目录

- [概述](#概述)
- [职业生涯数据](#职业生涯数据)
- [游戏日志](#游戏日志)
- [球员仪表板](#球员仪表板)
- [进阶统计](#进阶统计)
- [其他球员数据](#其他球员数据)
- [使用指南](#使用指南)

---

## 概述

球员统计接口提供了约 40 个端点，涵盖球员的各个维度数据：

### 主要分类

1. **职业生涯数据**：球员整个职业生涯的统计汇总
2. **游戏日志**：球员每场比赛的详细数据
3. **球员仪表板**：按各种维度划分的统计（vs 对手、主客场等）
4. **进阶统计**：传球、篮板、投篮、防守等细分数据
5. **其他数据**：奖项、比较、索引等

**关键特点：**
- ✅ 所有端点都需要 `player_id` 参数
- ✅ 大多数支持按赛季、比赛类型筛选
- ✅ 提供常规赛、季后赛、全明星等多种数据
- ✅ 支持 DataFrame、JSON、字典多种格式

---

## 职业生涯数据

### 1. PlayerCareerStats（职业生涯统计）

**端点描述：** 获取球员职业生涯的完整统计数据

**URL：** `https://stats.nba.com/stats/playercareerstats`

**参数：**

| 参数名 | Python 变量名 | 类型 | 必需 | 说明 |
|--------|-------------|------|------|------|
| PlayerID | player_id | string | ✓ | 球员 ID |
| PerMode | per_mode | string |  | 统计模式（Totals/PerGame/Per36 等） |

**PerMode 可选值：**
- `Totals`：累计数据
- `PerGame`：场均数据
- `Per36`：每 36 分钟数据
- `Per100Possessions`：每 100 回合数据

**返回数据集：**

#### SeasonTotalsRegularSeason（常规赛赛季数据）
包含字段：
- **赛季信息**：SEASON_ID、TEAM_ID、TEAM_ABBREVIATION、PLAYER_AGE
- **比赛信息**：GP（比赛场次）、GS（首发场次）、MIN（总上场时间）
- **投篮数据**：FGM、FGA、FG_PCT、FG3M、FG3A、FG3_PCT、FTM、FTA、FT_PCT
- **篮板数据**：OREB、DREB、REB
- **其他数据**：AST、STL、BLK、TOV、PF、PTS

#### CareerTotalsRegularSeason（常规赛生涯总计）
职业生涯累计统计

#### SeasonTotalsPostSeason（季后赛赛季数据）
季后赛各赛季统计

#### CareerTotalsPostSeason（季后赛生涯总计）
季后赛生涯累计

#### SeasonTotalsAllStarSeason（全明星赛季数据）
全明星赛统计

**使用示例：**
```python
from nba_api.stats.endpoints import playercareerstats

# 获取 LeBron James 的职业生涯数据
career = playercareerstats.PlayerCareerStats(
    player_id='2544',
    per_mode='PerGame'
)

# 常规赛场均数据
regular_season = career.season_totals_regular_season.get_data_frame()
print(regular_season[['SEASON_ID', 'TEAM_ABBREVIATION', 'GP', 'PTS', 'REB', 'AST']])

# 生涯总计
career_totals = career.career_totals_regular_season.get_data_frame()
print(career_totals)
```

---

### 2. PlayerProfileV2（球员档案）

**端点描述：** 获取球员的详细档案信息和生涯概览

**URL：** `https://stats.nba.com/stats/playerprofilev2`

**参数：**
- **PlayerID**（player_id）：球员 ID
- **LeagueID**（league_id）：联赛 ID（默认 "00"）
- **PerMode**（per_mode）：统计模式

**返回数据集：**
- **SeasonTotalsRegularSeason**：各赛季常规赛数据
- **SeasonTotalsPostSeason**：各赛季季后赛数据
- **CareerTotalsRegularSeason**：常规赛生涯总计
- **CareerTotalsPostSeason**：季后赛生涯总计
- **SeasonHighs**：赛季最高纪录

---

### 3. PlayerCareerByCollege（按大学生涯）

**端点描述：** 获取球员按大学分类的生涯统计

**使用场景：** 查看球员在不同大学的表现（如果有转学）

---

### 4. PlayerCareerByCollegeRollup（大学生涯汇总）

**端点描述：** 球员大学时期生涯数据的汇总统计

---

## 游戏日志

### 5. PlayerGameLog（球员比赛日志）

**端点描述：** 获取球员某个赛季的逐场比赛统计

**URL：** `https://stats.nba.com/stats/playergamelog`

**参数：**

| 参数名 | Python 变量名 | 类型 | 必需 | 说明 |
|--------|-------------|------|------|------|
| PlayerID | player_id | string | ✓ | 球员 ID |
| Season | season | string | ✓ | 赛季（如 "2023-24"） |
| SeasonType | season_type | string | ✓ | 赛季类型 |

**SeasonType 可选值：**
- `Regular Season`：常规赛
- `Playoffs`：季后赛
- `Pre Season`：季前赛
- `All Star`：全明星

**返回数据集：**

#### PlayerGameLog（比赛日志）
包含字段：
- **比赛信息**：SEASON_ID、GAME_ID、GAME_DATE、MATCHUP、WL（胜负）
- **统计数据**：MIN、FGM、FGA、FG_PCT、FG3M、FG3A、FG3_PCT、FTM、FTA、FT_PCT
- **全面数据**：OREB、DREB、REB、AST、STL、BLK、TOV、PF、PTS、PLUS_MINUS

**使用示例：**
```python
from nba_api.stats.endpoints import playergamelog

# 获取 2023-24 赛季常规赛比赛日志
gamelog = playergamelog.PlayerGameLog(
    player_id='2544',
    season='2023-24',
    season_type_all_star='Regular Season'
)

games = gamelog.player_game_log.get_data_frame()

# 查看最近10场比赛
recent_games = games.head(10)
print(recent_games[['GAME_DATE', 'MATCHUP', 'MIN', 'PTS', 'REB', 'AST']])

# 计算场均数据
avg_pts = games['PTS'].mean()
print(f"场均得分: {avg_pts:.1f}")
```

---

### 6. PlayerGameLogs（多球员比赛日志）

**端点描述：** 批量获取多个球员的比赛日志

**使用场景：** 比较多个球员在相同条件下的表现

---

## 球员仪表板

### 7. PlayerDashboardByClutch（关键时刻表现）

**端点描述：** 获取球员在关键时刻（Clutch Time）的统计表现

**URL：** `https://stats.nba.com/stats/playerdashboardbyclutch`

**关键时刻定义：** 第四节或加时赛最后 5 分钟，分差在 5 分以内

**参数：**
- **PlayerID**（player_id）：球员 ID
- **Season**（season）：赛季
- **MeasureType**（measure_type）：测量类型（Base/Advanced/Misc 等）

**MeasureType 可选值：**
- `Base`：基础数据
- `Advanced`：高级数据
- `Misc`：杂项数据
- `Scoring`：得分数据
- `Usage`：使用率数据

**返回数据集：**
- **OverallPlayerDashboard**：整体表现
- **ClutchPlayerDashboard**：关键时刻表现
- **NonClutchPlayerDashboard**：非关键时刻表现

**使用示例：**
```python
from nba_api.stats.endpoints import playerdashboardbyclutch

clutch = playerdashboardbyclutch.PlayerDashboardByClutch(
    player_id='2544',
    season='2023-24',
    measure_type='Base'
)

# 关键时刻数据
clutch_stats = clutch.clutch_player_dashboard.get_data_frame()
print(clutch_stats[['GP', 'W', 'L', 'MIN', 'PTS', 'FG_PCT']])
```

---

### 8. PlayerDashboardByGameSplits（按比赛分类）

**端点描述：** 获取球员按不同比赛条件分类的统计

**分类维度：**
- 主场 vs 客场
- 胜利 vs 失败
- 赛前休息天数
- 比赛开始时间（日间/夜间）
- 月份

**返回数据集：**
- **OverallPlayerDashboard**：整体数据
- **LocationPlayerDashboard**：主客场数据
- **WinsLossesPlayerDashboard**：胜负场数据
- **MonthPlayerDashboard**：按月份数据
- **PrePostAllStarPlayerDashboard**：全明星前后数据
- **DaysRestPlayerDashboard**：按休息天数数据

---

### 9. PlayerDashboardByGeneralSplits（按一般分类）

**端点描述：** 按赛季类型、球队、位置等一般条件分类

**分类维度：**
- 赛季类型（常规赛/季后赛）
- 时期（上半场/下半场/加时）
- 场上位置

---

### 10. PlayerDashboardByOpponent（对阵对手）

**端点描述：** 获取球员对阵各支球队的统计表现

**URL：** `https://stats.nba.com/stats/playerdashboardbyopponent`

**返回数据集：**
- **OverallPlayerDashboard**：整体数据
- **OpponentPlayerDashboard**：对阵各队数据（30 行，每支球队一行）

**使用示例：**
```python
from nba_api.stats.endpoints import playerdashboardbyopponent

opponent = playerdashboardbyopponent.PlayerDashboardByOpponent(
    player_id='2544',
    season='2023-24'
)

vs_teams = opponent.opponent_player_dashboard.get_data_frame()

# 找出得分最高的对手
vs_teams_sorted = vs_teams.sort_values('PTS', ascending=False)
print(vs_teams_sorted[['VS_TEAM_ABBREVIATION', 'GP', 'PTS', 'FG_PCT']].head(10))
```

---

### 11. PlayerDashboardByShootingSplits（按投篮分类）

**端点描述：** 按投篮距离、区域、命中情况分类

**分类维度：**
- 投篮距离（5ft、10ft、15ft等范围）
- 投篮区域（油漆区、中距离、三分等）
- 投篮类型（跳投、上篮、扣篮等）
- 助攻情况（助攻投篮 vs 自主投篮）

**返回数据集：**
- **Shot5FTPlayerDashboard**：5英尺内投篮
- **Shot8FTPlayerDashboard**：8英尺内投篮
- **ShotAreaPlayerDashboard**：按区域投篮
- **AssistedShotPlayerDashboard**：助攻投篮数据
- **ShotTypePlayerDashboard**：按投篮类型

---

### 12. PlayerDashboardByTeamPerformance（按球队表现）

**端点描述：** 按球队得分、篮板、助攻等表现分类

**分类维度：**
- 球队得分范围（80-89分、90-99分等）
- 对手得分范围
- 分差范围

---

### 13. PlayerDashboardByYearOverYear（逐年对比）

**端点描述：** 球员各赛季数据的年度对比

**使用场景：** 观察球员成长轨迹和状态变化

---

## 进阶统计

### 14. PlayerPassTracking（传球追踪）

**端点描述：** 获取球员的传球数据（基于 SportVU 追踪）

**URL：** `https://stats.nba.com/stats/playerdashptpass`

**参数：**
- **PlayerID**（player_id）：球员 ID
- **Season**（season）：赛季
- **PerMode**（per_mode）：统计模式

**返回数据集：**

#### PassesMade（传球数据）
包含字段：
- **PASSES_MADE**：传球次数
- **PASSES_RECEIVED**：接球次数
- **AST**：助攻数
- **SECONDARY_AST**：次要助攻（助攻前的传球）
- **POTENTIAL_AST**：潜在助攻（传球后队友投篮但未进）
- **AST_PTS_CREATED**：助攻创造的得分
- **AST_ADJ**：调整后助攻

**使用示例：**
```python
from nba_api.stats.endpoints import playerdashptpass

passing = playerdashptpass.PlayerDashPtPass(
    player_id='2544',
    season='2023-24'
)

pass_data = passing.passes_made.get_data_frame()
print(pass_data[['PASSES_MADE', 'AST', 'SECONDARY_AST', 'AST_PTS_CREATED']])
```

---

### 15. PlayerReboundTracking（篮板追踪）

**端点描述：** 获取球员的详细篮板数据

**URL：** `https://stats.nba.com/stats/playerdashptreb`

**返回数据集：**

#### ReboundTrack（篮板追踪数据）
包含字段：
- **REB**：总篮板
- **CONTESTED_REB**：争抢篮板
- **UNCONTESTED_REB**：无争抢篮板
- **REB_CHANCES**：篮板机会
- **REB_CHANCE_PCT**：篮板机会转化率
- **DEFERRED_REB**：让出的篮板
- **OREB**/**DREB**：进攻/防守篮板细分

---

### 16. PlayerShotTracking（投篮追踪）

**端点描述：** 获取球员的投篮追踪数据（受干扰程度等）

**URL：** `https://stats.nba.com/stats/playerdashptshots`

**返回数据集：**

#### ShotTrack（投篮追踪）
包含字段：
- **FGA**：出手次数
- **FG2A**/**FG3A**：2分/3分出手
- **FGM**：命中次数
- **EFG_PCT**：有效命中率
- 按防守者距离分类：
  - **0-2 Feet - Very Tight**：非常紧密防守
  - **2-4 Feet - Tight**：紧密防守
  - **4-6 Feet - Open**：开放机会
  - **6+ Feet - Wide Open**：大空位

**使用示例：**
```python
from nba_api.stats.endpoints import playerdashptshots

shots = playerdashptshots.PlayerDashPtShots(
    player_id='203999',  # Nikola Jokić
    season='2023-24'
)

shot_data = shots.general_shooting.get_data_frame()

# 查看不同防守压力下的命中率
print(shot_data[[
    'FGA', 'FG_PCT',
    'FGA_FREQUENCY',  # 出手频率
    'CLOSE_DEF_DIST_RANGE'  # 防守者距离范围
]])
```

---

### 17. PlayerDefenseTracking（防守追踪）

**端点描述：** 获取球员的防守追踪数据

**URL：** `https://stats.nba.com/stats/playerdashptdefend`

**返回数据集：**
- **DefendingShots**：防守投篮数据（按防守位置分类）
- 包含对手命中率、防守频率等

---

### 18. PlayerSpeedDistanceTracking（速度距离追踪）

**端点描述：** 获取球员的移动速度和距离数据

**返回数据集：**
包含字段：
- **DIST_MILES**：跑动距离（英里）
- **DIST_MILES_OFF**：持球跑动距离
- **DIST_MILES_DEF**：防守跑动距离
- **AVG_SPEED**：平均速度
- **AVG_SPEED_OFF**：持球平均速度
- **AVG_SPEED_DEF**：防守平均速度

---

### 19. PlayerEstimatedMetrics（估算指标）

**端点描述：** 获取球员的估算高级指标

**返回字段：**
- **E_OFF_RATING**：估算进攻效率
- **E_DEF_RATING**：估算防守效率
- **E_NET_RATING**：估算净效率
- **E_PACE**：估算节奏
- **E_AST_RATIO**：估算助攻比率
- **E_OREB_PCT**/**E_DREB_PCT**：估算篮板率
- **E_TOV_PCT**：估算失误率
- **E_USG_PCT**：估算使用率

---

## 其他球员数据

### 20. PlayerAwards（球员奖项）

**端点描述：** 获取球员获得的所有奖项和荣誉

**URL：** `https://stats.nba.com/stats/playerawards`

**返回数据集：**
- **PlayerAwards**：奖项列表（MVP、DPOY、全明星、最佳阵容等）

**使用示例：**
```python
from nba_api.stats.endpoints import playerawards

awards = playerawards.PlayerAwards(player_id='2544')
award_list = awards.player_awards.get_data_frame()

print(award_list[['SEASON', 'DESCRIPTION', 'TYPE']])
```

---

### 21. PlayerCompare（球员对比）

**端点描述：** 对比多个球员的统计数据

**使用场景：** 并排比较 2-5 名球员的表现

---

### 22. PlayerVsPlayer（球员对位）

**端点描述：** 获取两名球员直接对位时的数据

**使用场景：** 分析球员在直接对位时的表现

---

### 23. PlayerFantasyProfile（梦幻篮球档案）

**端点描述：** 获取适用于梦幻篮球的球员数据

**返回数据：** 梦幻积分、排名、预测等

---

### 24. PlayerIndex（球员索引）

**端点描述：** 获取符合特定条件的球员列表

**参数：**
- **Season**：赛季
- **TeamID**：球队 ID（可选）
- **SeasonType**：赛季类型

**使用场景：** 查找某赛季某球队的所有球员

---

### 25. CommonPlayerInfo（球员基本信息）

**端点描述：** 获取球员的基本个人信息

**URL：** `https://stats.nba.com/stats/commonplayerinfo`

**返回数据集：**

#### CommonPlayerInfo（基本信息）
包含字段：
- **个人信息**：DISPLAY_FIRST_LAST（姓名）、BIRTHDATE（生日）、COUNTRY（国籍）
- **身体数据**：HEIGHT（身高）、WEIGHT（体重）
- **职业信息**：DRAFT_YEAR、DRAFT_ROUND、DRAFT_NUMBER（选秀信息）
- **当前状态**：TEAM_ID、TEAM_NAME、JERSEY（球衣号码）、POSITION（位置）
- **经验**：SEASON_EXP（NBA经验）、FROM_YEAR（首个赛季）、TO_YEAR（最后赛季）

#### PlayerHeadlineStats（头条统计）
本赛季的关键统计数据（PTS、REB、AST 等）

**使用示例：**
```python
from nba_api.stats.endpoints import commonplayerinfo

info = commonplayerinfo.CommonPlayerInfo(player_id='2544')

# 基本信息
player_info = info.common_player_info.get_data_frame()
print(player_info[['DISPLAY_FIRST_LAST', 'HEIGHT', 'WEIGHT',
                    'DRAFT_YEAR', 'DRAFT_NUMBER', 'POSITION']])

# 本赛季统计
headline = info.player_headline_stats.get_data_frame()
print(headline[['PTS', 'REB', 'AST']])
```

---

## 使用指南

### 1. 如何获取 Player ID

```python
from nba_api.stats.static import players

# 方法1：通过姓名查找
lebron = players.find_players_by_full_name('LeBron James')
player_id = lebron[0]['id']  # 2544

# 方法2：搜索所有现役球员
active = players.get_active_players()
for player in active:
    if 'Curry' in player['full_name']:
        print(f"{player['full_name']}: {player['id']}")
```

### 2. 完整球员分析示例

```python
from nba_api.stats.endpoints import (
    playercareerstats,
    playergamelog,
    playerdashboardbyclutch,
    playerdashptpass
)

player_id = '2544'  # LeBron James
season = '2023-24'

# 1. 职业生涯数据
career = playercareerstats.PlayerCareerStats(
    player_id=player_id,
    per_mode='PerGame'
)
career_df = career.season_totals_regular_season.get_data_frame()

# 2. 本赛季比赛日志
gamelog = playergamelog.PlayerGameLog(
    player_id=player_id,
    season=season
)
games_df = gamelog.player_game_log.get_data_frame()

# 3. 关键时刻表现
clutch = playerdashboardbyclutch.PlayerDashboardByClutch(
    player_id=player_id,
    season=season
)
clutch_df = clutch.clutch_player_dashboard.get_data_frame()

# 4. 传球数据
passing = playerdashptpass.PlayerDashPtPass(
    player_id=player_id,
    season=season
)
pass_df = passing.passes_made.get_data_frame()

# 合并分析
print(f"职业生涯场均: {career_df['PTS'].iloc[-1]:.1f} 分")
print(f"本赛季场均: {games_df['PTS'].mean():.1f} 分")
print(f"关键时刻命中率: {clutch_df['FG_PCT'].iloc[0]:.1%}")
print(f"场均传球: {pass_df['PASSES_MADE'].iloc[0]:.0f} 次")
```

### 3. 多维度分析

```python
from nba_api.stats.endpoints import (
    playerdashboardbyopponent,
    playerdashboardbygamesplits,
    playerdashboardbyshootingsplits
)

player_id = '203999'  # Nikola Jokić

# 对阵各队表现
vs_teams = playerdashboardbyopponent.PlayerDashboardByOpponent(
    player_id=player_id,
    season='2023-24'
)

# 主客场表现
splits = playerdashboardbygamesplits.PlayerDashboardByGameSplits(
    player_id=player_id,
    season='2023-24'
)

# 投篮热区
shooting = playerdashboardbyshootingsplits.PlayerDashboardByShootingSplits(
    player_id=player_id,
    season='2023-24'
)

# 提取数据
opponents_df = vs_teams.opponent_player_dashboard.get_data_frame()
location_df = splits.location_player_dashboard.get_data_frame()
shot_area_df = shooting.shot_area_player_dashboard.get_data_frame()

# 分析
print("对阵得分最多的球队:")
print(opponents_df.nlargest(5, 'PTS')[['VS_TEAM_ABBREVIATION', 'GP', 'PTS']])

print("\n主客场对比:")
print(location_df[['GROUP_VALUE', 'GP', 'W_PCT', 'PTS', 'FG_PCT']])

print("\n投篮区域分布:")
print(shot_area_df[['GROUP_VALUE', 'FGA', 'FG_PCT', 'FG3A', 'FG3_PCT']])
```

### 4. 趋势分析

```python
import pandas as pd
import matplotlib.pyplot as plt

from nba_api.stats.endpoints import playergamelog

# 获取整个赛季数据
gamelog = playergamelog.PlayerGameLog(
    player_id='2544',
    season='2023-24'
)

games = gamelog.player_game_log.get_data_frame()

# 转换日期
games['GAME_DATE'] = pd.to_datetime(games['GAME_DATE'])
games = games.sort_values('GAME_DATE')

# 计算滚动平均
games['PTS_MA5'] = games['PTS'].rolling(window=5).mean()
games['AST_MA5'] = games['AST'].rolling(window=5).mean()

# 绘制趋势图
plt.figure(figsize=(12, 6))
plt.plot(games['GAME_DATE'], games['PTS'], alpha=0.3, label='得分')
plt.plot(games['GAME_DATE'], games['PTS_MA5'], linewidth=2, label='得分(5场均值)')
plt.xlabel('日期')
plt.ylabel('得分')
plt.title('球员得分趋势')
plt.legend()
plt.show()
```

### 5. 性能优化

```python
# 使用缓存避免重复请求
player_cache = {}

def get_player_stats(player_id, season):
    cache_key = f"{player_id}_{season}"
    if cache_key not in player_cache:
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            timeout=30
        )
        player_cache[cache_key] = gamelog.get_data_frames()[0]
    return player_cache[cache_key]

# 批量处理
player_ids = ['2544', '203999', '1629029']
all_stats = []

for pid in player_ids:
    try:
        stats = get_player_stats(pid, '2023-24')
        all_stats.append(stats)
    except Exception as e:
        print(f"获取球员 {pid} 数据失败: {e}")

# 合并分析
combined = pd.concat(all_stats, ignore_index=True)
```

---

## 常见使用场景

### 场景 1：球员赛季报告
```python
# 职业生涯 + 本赛季日志 + 关键时刻 + 进阶数据
```

### 场景 2：球员对比分析
```python
# 多个球员的相同指标对比
```

### 场景 3：选秀球探报告
```python
# 大学数据 + 选秀前预测 + 新秀赛季表现
```

### 场景 4：梦幻篮球
```python
# 近期状态 + 赛程分析 + 对阵历史
```

### 场景 5：投注分析
```python
# 主客场差异 + 对阵特定球队 + 休息天数影响
```

---

## 注意事项

1. **Player ID**：使用静态模块或 CommonPlayerInfo 获取正确的 ID
2. **赛季格式**：必须是 "YYYY-YY" 格式（如 "2023-24"）
3. **数据延迟**：实时数据可能有几分钟延迟
4. **空数据**：新秀或特定场景可能返回空数据集
5. **请求限制**：避免过于频繁的请求，建议添加延迟
6. **PerMode**：不同模式会影响数据的展示方式

---

## 相关资源

- [总览文档](./NBA_API_OVERVIEW.md)
- [静态数据模块](./API_STATIC_DATA.md)
- [比赛数据接口](./API_GAME_DATA.md)
- [球队统计接口](./API_TEAM_STATS.md)
- [联赛数据接口](./API_LEAGUE_DATA.md)

**GitHub 端点文档：**
- [PlayerCareerStats](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/playercareerstats.md)
- [PlayerGameLog](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/playergamelog.md)
- [PlayerDashboard 系列](https://github.com/swar/nba_api/tree/master/docs/nba_api/stats/endpoints)
