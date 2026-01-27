# NBA API - 选秀及其他数据接口文档

> 本文档整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 目录

- [概述](#概述)
- [选秀相关端点](#选秀相关端点)
- [通用数据端点](#通用数据端点)
- [专项功能端点](#专项功能端点)
- [使用指南](#使用指南)

---

## 概述

本文档涵盖选秀数据及其他综合功能端点，共约 43 个：

### 主要分类

1. **选秀相关**（7个）：选秀历史、选秀榜、联合试训等
2. **通用数据**（15个）：球员信息、球队信息、赛季信息等
3. **专项功能**（21个）：助攻追踪、防守中心、累积统计等

**关键特点：**
- ✅ 提供历史和当前选秀数据
- ✅ 包含球员和球队的基础信息
- ✅ 提供特殊统计和分析功能
- ✅ 支持多维度数据查询

---

## 选秀相关端点

### 1. DraftHistory（选秀历史）

**端点描述：** 获取NBA选秀的完整历史记录

**URL：** `https://stats.nba.com/stats/drafthistory`

**参数：**
- **LeagueID**（league_id）：联赛 ID
- **Season**（season_year_nullable）：选秀年份

**返回数据集：**

#### DraftHistory（选秀历史）
包含字段：
- **PERSON_ID**：球员 ID
- **PLAYER_NAME**：球员姓名
- **SEASON**：选秀年份
- **ROUND_NUMBER**：轮次
- **ROUND_PICK**：轮内顺位
- **OVERALL_PICK**：总顺位
- **TEAM_ID**、**TEAM_CITY**、**TEAM_NAME**、**TEAM_ABBREVIATION**：选中球队信息
- **ORGANIZATION**：大学/组织
- **ORGANIZATION_TYPE**：组织类型（College/High School等）

**使用示例：**
```python
from nba_api.stats.endpoints import drafthistory

# 获取所有选秀历史
draft = drafthistory.DraftHistory()
history = draft.draft_history.get_data_frame()

# 查看2023年选秀
draft_2023 = history[history['SEASON'] == '2023']
print("2023年选秀:")
print(draft_2023[['OVERALL_PICK', 'PLAYER_NAME', 'TEAM_ABBREVIATION',
                  'ORGANIZATION']].head(30))

# 状元秀列表
first_picks = history[history['OVERALL_PICK'] == 1]
print("\n历年状元:")
print(first_picks[['SEASON', 'PLAYER_NAME', 'TEAM_ABBREVIATION']])

# 按大学统计
college_counts = history['ORGANIZATION'].value_counts()
print("\n选秀球员最多的大学:")
print(college_counts.head(10))
```

---

### 2. DraftBoard（选秀榜）

**端点描述：** 获取特定年份的选秀榜和球员排名

**URL：** `https://stats.nba.com/stats/draftboard`

**参数：**
- **SeasonYear**（season_year）：选秀年份（如 "2023"）

**使用场景：** 查看选秀大会上的球员排名和选择顺序

---

### 3. DraftCombineStats（选秀联合试训统计）

**端点描述：** 获取选秀联合试训的测量数据和统计

**URL：** `https://stats.nba.com/stats/draftcombinestats`

**参数：**
- **SeasonYear**（season_year）：选秀年份

**返回数据集：**

#### DraftCombineStats（试训统计）
包含字段：
- **身体测量**：HEIGHT_WO_SHOES、HEIGHT_W_SHOES、WEIGHT、WINGSPAN、STANDING_REACH
- **体能测试**：BODY_FAT_PCT、HAND_LENGTH、HAND_WIDTH
- **运动能力**：
  - BENCH_PRESS（卧推次数）
  - VERTICAL_LEAP_MAX、VERTICAL_LEAP_MAX_REACH（最大弹跳）
  - VERTICAL_LEAP_NO_STEP、VERTICAL_LEAP_NO_STEP_REACH（原地弹跳）
  - LANE_AGILITY_TIME（折返跑时间）
  - THREE_QUARTER_SPRINT（3/4场冲刺时间）

**使用示例：**
```python
from nba_api.stats.endpoints import draftcombinestats

# 获取2023年选秀试训数据
combine = draftcombinestats.DraftCombineStats(season_year='2023')
stats = combine.draft_combine_stats.get_data_frame()

print("2023选秀试训数据:")
print(stats[['PLAYER_NAME', 'HEIGHT_WO_SHOES', 'WEIGHT', 'WINGSPAN',
             'VERTICAL_LEAP_MAX', 'BENCH_PRESS']].head(20))

# 找出弹跳最高的球员
top_vert = stats.nlargest(10, 'VERTICAL_LEAP_MAX')
print("\n弹跳最高:")
print(top_vert[['PLAYER_NAME', 'HEIGHT_WO_SHOES', 'VERTICAL_LEAP_MAX']])

# 找出臂展最长的球员
top_wingspan = stats.nlargest(10, 'WINGSPAN')
print("\n臂展最长:")
print(top_wingspan[['PLAYER_NAME', 'HEIGHT_WO_SHOES', 'WINGSPAN']])
```

---

### 4. DraftCombineDrillResults（选秀试训训练结果）

**端点描述：** 获取选秀试训中的详细训练项目结果

**使用场景：** 更详细的试训表现数据

---

### 5. DraftCombinePlayerAnthro（选秀试训身体测量）

**端点描述：** 专门的身体测量数据端点

**包含数据：** 身高、体重、臂展、手掌大小等

---

### 6. DraftCombineSpotShooting（选秀试训定点投篮）

**端点描述：** 选秀试训中的定点投篮测试结果

**使用场景：** 评估新秀的投篮能力

---

### 7. DraftCombineNonStationaryShooting（选秀试训移动投篮）

**端点描述：** 选秀试训中的移动投篮测试结果

**使用场景：** 评估新秀的动态投篮能力

---

## 通用数据端点

### 8. CommonAllPlayers（所有球员）

**端点描述：** 获取指定赛季的所有NBA球员列表

**URL：** `https://stats.nba.com/stats/commonallplayers`

**参数：**
- **Season**（season）：赛季（如 "2023-24"）
- **IsOnlyCurrentSeason**（is_only_current_season）：是否只返回当前赛季

**返回数据集：**

#### CommonAllPlayers（球员列表）
包含字段：
- **PERSON_ID**：球员 ID
- **DISPLAY_FIRST_LAST**：显示姓名
- **ROSTERSTATUS**：名单状态（1=现役，0=非现役）
- **FROM_YEAR**/**TO_YEAR**：职业生涯起止年份
- **TEAM_ID**、**TEAM_CITY**、**TEAM_NAME**、**TEAM_ABBREVIATION**：当前球队信息

**使用示例：**
```python
from nba_api.stats.endpoints import commonallplayers

# 获取2023-24赛季所有球员
players = commonallplayers.CommonAllPlayers(
    season='2023-24',
    is_only_current_season=1
)

all_players = players.common_all_players.get_data_frame()

# 现役球员
active = all_players[all_players['ROSTERSTATUS'] == 1]
print(f"现役球员数: {len(active)}")

# 按球队统计
team_counts = active.groupby('TEAM_ABBREVIATION').size().sort_values(ascending=False)
print("\n各队人数:")
print(team_counts)
```

---

### 9. CommonPlayerInfo（球员基本信息）

详见 [球员统计接口文档](./API_PLAYER_STATS.md#25-commonplayerinfo球员基本信息)

---

### 10. CommonTeamYears（球队年份）

**端点描述：** 获取所有球队的存续年份信息

**URL：** `https://stats.nba.com/stats/commonteamyears`

**返回数据：** 每支球队的成立年份、历史名称变更等

---

### 11. CommonTeamRoster（球队名单）

详见 [球队统计接口文档](./API_TEAM_STATS.md#13-commonteamroster球队名单)

---

### 12. CommonPlayoffSeries（季后赛系列赛）

**端点描述：** 获取季后赛系列赛的信息

**URL：** `https://stats.nba.com/stats/commonplayoffseries`

**参数：**
- **Season**（season）：赛季
- **LeagueID**（league_id）：联赛 ID

**返回数据：** 季后赛对阵、系列赛比分等

---

### 13. ScoreboardV2（比分板V2）

**端点描述：** 获取特定日期的所有比赛比分板

**URL：** `https://stats.nba.com/stats/scoreboardv2`

**参数：**
- **GameDate**（game_date）：比赛日期（YYYY-MM-DD格式）
- **LeagueID**（league_id）：联赛 ID
- **DayOffset**（day_offset）：日期偏移

**返回数据集：**
- **GameHeader**：比赛基本信息
- **LineScore**：各节比分
- **SeriesStandings**：系列赛战绩（季后赛）
- **LastMeeting**：最近交手记录
- **EastConfStandingsByDay**/**WestConfStandingsByDay**：当日东西部排名
- **Available**：可用性信息

**使用示例：**
```python
from nba_api.stats.endpoints import scoreboardv2
from datetime import date

# 获取特定日期的比分板
scoreboard = scoreboardv2.ScoreboardV2(
    game_date='2024-01-27',
    day_offset=0
)

# 比赛列表
games = scoreboard.game_header.get_data_frame()
print("今日比赛:")
print(games[['GAME_ID', 'HOME_TEAM_ID', 'VISITOR_TEAM_ID', 'GAME_STATUS_TEXT']])

# 比分详情
scores = scoreboard.line_score.get_data_frame()
print("\n比分:")
print(scores[['TEAM_ABBREVIATION', 'PTS_QTR1', 'PTS_QTR2',
              'PTS_QTR3', 'PTS_QTR4', 'PTS']])
```

---

### 14. HomePageLeaders（主页领袖）

**端点描述：** 获取NBA官网主页展示的当日领袖数据

**使用场景：** 快速获取当日表现最佳的球员

---

### 15. HomePageV2（主页V2）

**端点描述：** 获取NBA官网主页的各类数据

**返回数据：** 当日赛事、新闻、领袖榜等综合信息

---

## 专项功能端点

### 16. AssistTracker（助攻追踪）

**端点描述：** 追踪球员的助攻和被助攻数据

**URL：** `https://stats.nba.com/stats/assisttracker`

**参数：**
- **Season**（season）：赛季
- **SeasonType**（season_type）：赛季类型

**返回数据：** 球员之间的助攻传球关系

**使用场景：** 分析球队的传球网络和化学反应

---

### 17. AssistLeaders（助攻领袖）

**端点描述：** 获取助攻榜领先球员

**使用场景：** 快速查看助攻王候选

---

### 18. DefenseHub（防守中心）

**端点描述：** 防守相关的综合数据中心

**URL：** `https://stats.nba.com/stats/defensehub`

**返回数据：** 各类防守统计和排行

**使用场景：** 防守球员和最佳防守球员分析

---

### 19. HustleStatsBoxScore（拼抢数据盒子分数）

**端点描述：** 获取比赛的拼抢数据

**包含数据：** 扑球、干扰、争球、掩护助攻等

---

### 20. InfographicFanDuelPlayer（球员信息图）

**端点描述：** 用于信息图展示的球员数据

**使用场景：** 数据可视化和展示

---

### 21. PlayerEstimatedMetrics（球员估算指标）

详见 [球员统计接口文档](./API_PLAYER_STATS.md#19-playerestimatedmetrics估算指标)

---

### 22. CumeStatsPlayer（球员累积统计）

**端点描述：** 获取球员的累积统计数据

**URL：** `https://stats.nba.com/stats/cumestatsplayer`

**使用场景：** 查看球员赛季累积的统计曲线

---

### 23. CumeStatsTeam（球队累积统计）

**端点描述：** 获取球队的累积统计数据

**使用场景：** 查看球队赛季累积的统计曲线

---

### 24. CumeStatsPlayerGames（球员比赛累积）

**端点描述：** 按比赛累积的球员统计

**使用场景：** 生成球员赛季统计趋势图

---

### 25. PlayerCompare（球员对比）

详见 [球员统计接口文档](./API_PLAYER_STATS.md#21-playercompare球员对比)

---

### 26. TeamPlayerDashboard（球队球员仪表板）

**端点描述：** 球队所有球员的汇总仪表板

**使用场景：** 分析球队内部球员贡献分布

---

### 27. PlayoffPicture（季后赛形势）

**端点描述：** 获取当前的季后赛形势和排名

**URL：** `https://stats.nba.com/stats/playoffpicture`

**返回数据：** 东西部季后赛席位争夺情况

---

### 28. PlayerNextNGames（球员未来N场比赛）

**端点描述：** 获取球员未来几场比赛的对手信息

**使用场景：** 梦幻篮球和投注分析

---

### 29. TeamHistoricalLeaders（球队历史领袖）

**端点描述：** 球队历史各项统计的领先球员

详见 [球队统计接口文档](./API_TEAM_STATS.md#11-franchiseleaders球队历史领袖)

---

### 30. MatchupsRollup（对位汇总）

**端点描述：** 球员对位数据的汇总统计

**使用场景：** 分析球员在不同对位中的表现

---

### 31. PlayerGameStreakFinder（球员连续表现查找）

**端点描述：** 查找球员的连续得分、篮板等记录

**URL：** `https://stats.nba.com/stats/playergamestreakfinder`

**使用场景：** 查找连续20+得分、三双等记录

---

### 32. TeamGameStreakFinder（球队连续表现查找）

**端点描述：** 查找球队的连胜、连续得分等记录

**使用场景：** 查找球队连胜记录、连续得分超过110分等

---

### 33. LeaguePlayerOnDetails（球员在场详情）

**端点描述：** 球员在场时球队的表现数据

**使用场景：** 分析球员对球队影响力

---

### 34. LeagueSeasonMatchups（赛季对位详情）

**端点描述：** 赛季中球员之间的对位详细数据

---

### 35. VideoDetails（视频详情）

**端点描述：** 获取比赛或事件的视频详情

**使用场景：** 获取视频链接和可用性

---

### 36. VideoEventsAsset（视频事件资产）

**端点描述：** 比赛事件的视频资产信息

---

### 37. BoxScoreSimilarityScore（比赛相似度评分）

**端点描述：** 计算不同比赛数据的相似度

**使用场景：** 找出统计数据相似的比赛

---

### 38. ShotChartDetail（投篮图表详情）

**端点描述：** 获取球员或球队的投篮图表数据

**URL：** `https://stats.nba.com/stats/shotchartdetail`

**参数：**
- **PlayerID**（player_id）：球员 ID（0=全队）
- **TeamID**（team_id）：球队 ID
- **Season**（season）：赛季
- **ContextMeasure**（context_measure）：FGA或FG3A

**返回数据集：**

#### Shot_Chart_Detail（投篮详情）
包含每次投篮的：
- **LOC_X**、**LOC_Y**：投篮位置坐标
- **SHOT_DISTANCE**：投篮距离
- **SHOT_MADE_FLAG**：是否命中
- **SHOT_ATTEMPTED_FLAG**：是否出手
- **SHOT_TYPE**：投篮类型（2PT/3PT）
- **SHOT_ZONE_BASIC**：基本区域
- **SHOT_ZONE_AREA**：详细区域
- **SHOT_ZONE_RANGE**：距离范围
- **EVENT_TYPE**：事件类型

**使用示例：**
```python
from nba_api.stats.endpoints import shotchartdetail

# 获取球员投篮图表
shot_chart = shotchartdetail.ShotChartDetail(
    player_id='2544',
    team_id=0,
    season_nullable='2023-24',
    season_type_all_star='Regular Season',
    context_measure_simple='FGA'
)

shots = shot_chart.shot_chart_detail.get_data_frame()

print(f"总出手: {len(shots)}")
print(f"命中: {shots['SHOT_MADE_FLAG'].sum()}")
print(f"命中率: {shots['SHOT_MADE_FLAG'].mean():.1%}")

# 按区域统计
zone_stats = shots.groupby('SHOT_ZONE_BASIC').agg({
    'SHOT_MADE_FLAG': ['sum', 'count', 'mean']
})
print("\n按区域统计:")
print(zone_stats)

# 绘制投篮热图
import matplotlib.pyplot as plt

made = shots[shots['SHOT_MADE_FLAG'] == 1]
missed = shots[shots['SHOT_MADE_FLAG'] == 0]

plt.figure(figsize=(12, 11))
plt.scatter(missed['LOC_X'], missed['LOC_Y'], c='red', alpha=0.3, s=20, label='未中')
plt.scatter(made['LOC_X'], made['LOC_Y'], c='green', alpha=0.5, s=20, label='命中')
plt.legend()
plt.title('投篮图表')
plt.show()
```

---

### 39. ShotChartLineupDetail（阵容投篮图表）

**端点描述：** 特定阵容组合的投篮图表数据

---

### 40. TeamDashLineups（球队阵容仪表板）

**端点描述：** 球队各种阵容组合的统计表现

**URL：** `https://stats.nba.com/stats/teamdashlineups`

**使用场景：** 分析五人阵容的效率和搭配

---

### 41. LeagueDashLineups（联赛阵容仪表板）

**端点描述：** 全联盟各球队阵容组合的统计

**使用场景：** 对比全联盟最佳阵容

---

### 42. PlayerDashPtShotDefend（球员防守投篮追踪）

**端点描述：** 球员防守时对手的投篮数据

详见 [球员统计接口文档](./API_PLAYER_STATS.md#17-playerdefensetracking防守追踪)

---

### 43. LeagueSeasonMatchups（联赛赛季对位）

**端点描述：** 全联盟球员对位的综合数据

---

## 使用指南

### 1. 选秀球探报告

```python
from nba_api.stats.endpoints import (
    drafthistory,
    draftcombinestats,
    commonplayerinfo
)

# 1. 查看选秀历史
draft_year = '2023'
history = drafthistory.DraftHistory()
draft_class = history.draft_history.get_data_frame()
draft_class = draft_class[draft_class['SEASON'] == draft_year]

print(f"{draft_year}年选秀:")
print(draft_class[['OVERALL_PICK', 'PLAYER_NAME', 'TEAM_ABBREVIATION',
                   'ORGANIZATION']].head(15))

# 2. 获取试训数据
combine = draftcombinestats.DraftCombineStats(season_year=draft_year)
measurements = combine.draft_combine_stats.get_data_frame()

# 3. 合并分析
for idx, player in draft_class.head(5).iterrows():
    player_name = player['PLAYER_NAME']
    player_combine = measurements[measurements['PLAYER_NAME'] == player_name]

    if not player_combine.empty:
        print(f"\n{player_name} (第{player['OVERALL_PICK']}顺位):")
        print(f"  身高: {player_combine['HEIGHT_WO_SHOES'].iloc[0]}")
        print(f"  体重: {player_combine['WEIGHT'].iloc[0]}")
        print(f"  臂展: {player_combine['WINGSPAN'].iloc[0]}")
        print(f"  弹跳: {player_combine['VERTICAL_LEAP_MAX'].iloc[0]}")
```

### 2. 投篮分析

```python
from nba_api.stats.endpoints import shotchartdetail

# 获取投篮数据
shots = shotchartdetail.ShotChartDetail(
    player_id='2544',
    team_id=0,
    season_nullable='2023-24',
    context_measure_simple='FGA'
)

shot_data = shots.shot_chart_detail.get_data_frame()

# 分析投篮习惯
print("投篮类型分布:")
print(shot_data['SHOT_TYPE'].value_counts())

print("\n投篮区域:")
print(shot_data['SHOT_ZONE_BASIC'].value_counts())

print("\n距离范围命中率:")
distance_stats = shot_data.groupby('SHOT_ZONE_RANGE')['SHOT_MADE_FLAG'].agg([
    'count', 'sum', 'mean'
])
distance_stats.columns = ['出手', '命中', '命中率']
print(distance_stats)

# 关键时刻投篮
clutch_shots = shot_data[
    (shot_data['PERIOD'] >= 4) &
    (shot_data['MINUTES_REMAINING'] <= 5)
]
print(f"\n关键时刻投篮: {len(clutch_shots)} 次")
print(f"关键时刻命中率: {clutch_shots['SHOT_MADE_FLAG'].mean():.1%}")
```

### 3. 赛程分析

```python
from nba_api.stats.endpoints import scoreboardv2
from datetime import datetime, timedelta

# 获取一周的比赛
start_date = datetime(2024, 1, 27)

for i in range(7):
    current_date = start_date + timedelta(days=i)
    date_str = current_date.strftime('%Y-%m-%d')

    scoreboard = scoreboardv2.ScoreboardV2(game_date=date_str)
    games = scoreboard.game_header.get_data_frame()

    print(f"\n{date_str} ({current_date.strftime('%A')}):")
    print(f"  共 {len(games)} 场比赛")

    if len(games) > 0:
        print(games[['HOME_TEAM_ID', 'VISITOR_TEAM_ID', 'GAME_STATUS_TEXT']])
```

### 4. 阵容分析

```python
from nba_api.stats.endpoints import teamdashlineups

# 获取球队阵容数据
lineups = teamdashlineups.TeamDashLineups(
    team_id='1610612744',
    season='2023-24',
    measure_type='Advanced',
    per_mode='PerGame'
)

lineup_stats = lineups.team_dash_lineups.get_data_frame()

# 筛选出场时间充足的阵容
qualified = lineup_stats[lineup_stats['MIN'] >= 50]

# 按净效率排序
best_lineups = qualified.sort_values('NET_RATING', ascending=False)

print("最佳阵容(>=50分钟):")
print(best_lineups[['GROUP_NAME', 'MIN', 'OFF_RATING',
                    'DEF_RATING', 'NET_RATING']].head(10))

print("\n最差阵容:")
print(best_lineups[['GROUP_NAME', 'MIN', 'NET_RATING']].tail(5))
```

---

## 常见使用场景

### 场景 1：选秀分析
```python
# 选秀历史 + 试训数据 + 大学数据
```

### 场景 2：投篮分析
```python
# 投篮图表 + 区域统计 + 热区分析
```

### 场景 3：阵容优化
```python
# 阵容统计 + 球员搭配 + 效率对比
```

### 场景 4：比赛预览
```python
# 赛程信息 + 对阵历史 + 球队状态
```

---

## 注意事项

1. **选秀数据**：历史数据可能不完整，特别是早期年份
2. **试训数据**：不是所有球员都参加试训
3. **投篮坐标**：坐标系统以篮筐为原点
4. **阵容数据**：需要足够的样本量才有意义
5. **视频资源**：部分视频可能需要NBA League Pass

---

## 相关资源

- [总览文档](./NBA_API_OVERVIEW.md)
- [静态数据模块](./API_STATIC_DATA.md)
- [比赛数据接口](./API_GAME_DATA.md)
- [球员统计接口](./API_PLAYER_STATS.md)
- [球队统计接口](./API_TEAM_STATS.md)
- [联赛数据接口](./API_LEAGUE_DATA.md)

**GitHub 端点文档：**
- [DraftHistory](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/drafthistory.md)
- [ShotChartDetail](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/shotchartdetail.md)
- [TeamDashLineups](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/teamdashlineups.md)
