# NBA API - 联赛数据接口文档

> 本文档整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 目录

- [概述](#概述)
- [排名与排行](#排名与排行)
- [联赛球员统计](#联赛球员统计)
- [联赛球队统计](#联赛球队统计)
- [比赛查找与赛程](#比赛查找与赛程)
- [其他联赛功能](#其他联赛功能)
- [使用指南](#使用指南)

---

## 概述

联赛数据接口提供了约 20 个端点，涵盖整个联盟范围的数据：

### 主要分类

1. **排名与排行**：球队排名、球员排行榜
2. **联赛球员统计**：全联盟球员的各项统计
3. **联赛球队统计**：全联盟球队的各项统计
4. **比赛查找与赛程**：查找比赛、获取赛程
5. **其他功能**：阵容可视化、协同进攻等

**关键特点：**
- ✅ 提供全联盟维度的数据对比
- ✅ 支持多种筛选和排序条件
- ✅ 适合排行榜和对比分析
- ✅ 数据覆盖所有球队和球员

---

## 排名与排行

### 1. LeagueStandings（联赛排名）

**端点描述：** 获取联赛球队排名和战绩

**URL：** `https://stats.nba.com/stats/leaguestandings`

**参数：**
- **Season**（season）：赛季
- **SeasonType**（season_type）：赛季类型
- **LeagueID**（league_id）：联赛 ID

**返回数据集：**

#### Standings（排名）
包含字段：
- **球队信息**：TeamID、TeamCity、TeamName、Conference、Division
- **战绩数据**：W、L、W_PCT、HOME、ROAD、DIV、CONF
- **排名**：ConferenceRank、DivisionRank、PlayoffRank
- **近期表现**：L10（最近10场）、STREAK（连胜/连败）
- **对位战绩**：东西部、分区对战记录

**使用示例：**
```python
from nba_api.stats.endpoints import leaguestandings

standings = leaguestandings.LeagueStandings(
    season='2023-24',
    season_type='Regular Season'
)

ranks = standings.standings.get_data_frame()

# 东部排名
east = ranks[ranks['Conference'] == 'East'].sort_values('ConferenceRank')
print("东部排名:")
print(east[['ConferenceRank', 'TeamCity', 'W', 'L', 'W_PCT', 'L10', 'STREAK']])

# 西部排名
west = ranks[ranks['Conference'] == 'West'].sort_values('ConferenceRank')
print("\n西部排名:")
print(west[['ConferenceRank', 'TeamCity', 'W', 'L', 'W_PCT', 'L10', 'STREAK']])
```

---

### 2. LeagueStandingsV3（联赛排名V3）

**端点描述：** 更新版本的联赛排名，包含更多排名指标

**URL：** `https://stats.nba.com/stats/leaguestandingsv3`

**增强功能：**
- 更详细的季后赛排名信息
- 附加的战绩分类数据

---

### 3. LeagueLeaders（联赛领袖）

**端点描述：** 获取联盟各项统计的领先球员

**URL：** `https://stats.nba.com/stats/leagueleaders`

**参数：**
- **Season**（season）：赛季
- **SeasonType**（season_type）：赛季类型
- **StatCategory**（stat_category）：统计类别
- **PerMode**（per_mode）：统计模式

**StatCategory 可选值：**
- `PTS`：得分
- `REB`：篮板
- `AST`：助攻
- `STL`：抢断
- `BLK`：盖帽
- `FG_PCT`：命中率
- `FG3_PCT`：三分命中率
- `FT_PCT`：罚球命中率
- 等等

**返回数据集：**

#### LeagueLeaders（排行榜）
包含字段：
- **RANK**：排名
- **PLAYER**：球员姓名
- **PLAYER_ID**：球员 ID
- **TEAM**：球队
- **GP**：比赛场次
- **MIN**：上场时间
- 选定的统计类别及相关数据

**使用示例：**
```python
from nba_api.stats.endpoints import leagueleaders

# 得分榜
scoring = leagueleaders.LeagueLeaders(
    season='2023-24',
    season_type='Regular Season',
    stat_category_abbreviation='PTS',
    per_mode48='PerGame'
)

scorers = scoring.league_leaders.get_data_frame()
print("得分榜（场均）:")
print(scorers[['RANK', 'PLAYER', 'TEAM', 'GP', 'PTS']].head(20))

# 助攻榜
assists = leagueleaders.LeagueLeaders(
    season='2023-24',
    stat_category_abbreviation='AST'
)
assisters = assists.league_leaders.get_data_frame()
print("\n助攻榜:")
print(assisters[['RANK', 'PLAYER', 'AST']].head(10))
```

---

## 联赛球员统计

### 4. LeagueDashPlayerStats（联赛球员统计仪表板）

**端点描述：** 获取全联盟所有球员的统计数据

**URL：** `https://stats.nba.com/stats/leaguedashplayerstats`

**参数：**
- **Season**（season）：赛季
- **SeasonType**（season_type）：赛季类型
- **MeasureType**（measure_type）：测量类型
- **PerMode**（per_mode）：统计模式

**MeasureType 可选值：**
- `Base`：基础统计
- `Advanced`：高级统计
- `Misc`：杂项统计
- `Four Factors`：四因素
- `Scoring`：得分统计
- `Opponent`：对手统计
- `Usage`：使用率统计
- `Defense`：防守统计

**返回数据集：**

#### LeagueDashPlayerStats（球员统计）
根据 MeasureType 返回不同字段的统计数据

**使用示例：**
```python
from nba_api.stats.endpoints import leaguedashplayerstats

# 获取基础统计
stats = leaguedashplayerstats.LeagueDashPlayerStats(
    season='2023-24',
    season_type='Regular Season',
    measure_type='Base',
    per_mode='PerGame'
)

player_stats = stats.league_dash_player_stats.get_data_frame()

# 筛选出场超过20分钟的球员
qualified = player_stats[player_stats['MIN'] >= 20]

# 按得分排序
top_scorers = qualified.sort_values('PTS', ascending=False)
print("场均得分榜（>=20分钟）:")
print(top_scorers[['PLAYER_NAME', 'TEAM_ABBREVIATION', 'GP',
                   'MIN', 'PTS', 'REB', 'AST']].head(20))

# 高级统计
advanced = leaguedashplayerstats.LeagueDashPlayerStats(
    season='2023-24',
    measure_type='Advanced'
)
adv_stats = advanced.league_dash_player_stats.get_data_frame()

# 按净效率排序
top_net = adv_stats.sort_values('NET_RATING', ascending=False)
print("\n净效率榜:")
print(top_net[['PLAYER_NAME', 'MIN', 'OFF_RATING',
               'DEF_RATING', 'NET_RATING']].head(10))
```

---

### 5. LeagueDashPlayerClutch（球员关键时刻统计）

**端点描述：** 全联盟球员在关键时刻的表现统计

**URL：** `https://stats.nba.com/stats/leaguedashplayerclutch`

**使用场景：** 找出关键时刻表现最好的球员

---

### 6. LeagueDashPlayerShotLocations（球员投篮位置）

**端点描述：** 全联盟球员按投篮位置分类的统计

**URL：** `https://stats.nba.com/stats/leaguedashplayershotlocations`

**返回数据：** 各区域的投篮次数和命中率

---

### 7. LeagueDashPlayerPtShot（球员投篮追踪）

**端点描述：** 全联盟球员的投篮追踪数据

**使用场景：** 分析全联盟的投篮趋势和热区

---

### 8. LeagueDashPtStats（球员追踪统计）

**端点描述：** 全联盟球员的运动追踪统计数据

**URL：** `https://stats.nba.com/stats/leaguedashptstats`

**包含数据类型：**
- **SpeedDistance**：速度和距离
- **Rebounding**：篮板追踪
- **Passing**：传球追踪
- **Touches**：触球数据
- **Defense**：防守追踪
- **Drives**：突破数据
- **CatchShoot**：接球投篮
- **PullUpShot**：急停跳投

---

## 联赛球队统计

### 9. LeagueDashTeamStats（联赛球队统计仪表板）

**端点描述：** 获取全联盟所有球队的统计数据

**URL：** `https://stats.nba.com/stats/leaguedashteamstats`

**参数：** 与 LeagueDashPlayerStats 类似

**返回数据集：**

#### LeagueDashTeamStats（球队统计）
根据 MeasureType 返回不同类型的球队统计

**使用示例：**
```python
from nba_api.stats.endpoints import leaguedashteamstats

# 基础统计
team_stats = leaguedashteamstats.LeagueDashTeamStats(
    season='2023-24',
    measure_type='Base',
    per_mode='PerGame'
)

teams = team_stats.league_dash_team_stats.get_data_frame()

# 进攻排名
offense = teams.sort_values('PTS', ascending=False)
print("场均得分榜:")
print(offense[['TEAM_NAME', 'W', 'L', 'W_PCT', 'PTS', 'FG_PCT']].head(10))

# 防守排名
defense = teams.sort_values('OPP_PTS')
print("\n防守效率榜（失分最少）:")
print(defense[['TEAM_NAME', 'W', 'L', 'OPP_PTS', 'OPP_FG_PCT']].head(10))

# 高级统计
advanced = leaguedashteamstats.LeagueDashTeamStats(
    season='2023-24',
    measure_type='Advanced'
)
adv = advanced.league_dash_team_stats.get_data_frame()

# 净效率排名
net_rating = adv.sort_values('NET_RATING', ascending=False)
print("\n净效率榜:")
print(net_rating[['TEAM_NAME', 'OFF_RATING', 'DEF_RATING', 'NET_RATING']].head(10))
```

---

### 10. LeagueDashTeamClutch（球队关键时刻统计）

**端点描述：** 全联盟球队在关键时刻的表现统计

---

### 11. LeagueDashTeamShotLocations（球队投篮位置）

**端点描述：** 全联盟球队按投篮位置分类的统计

---

### 12. LeagueDashTeamPtShot（球队投篮追踪）

**端点描述：** 全联盟球队的投篮追踪数据

---

### 13. LeagueHustleStatsPlayer（球员拼抢统计）

**端点描述：** 全联盟球员的拼抢数据（扑球、争球等）

**URL：** `https://stats.nba.com/stats/leaguehustlestatplayer`

**返回数据：**
- **CONTESTED_SHOTS**：干扰投篮
- **CHARGES_DRAWN**：造进攻犯规
- **DEFLECTIONS**：干扰球
- **LOOSE_BALLS_RECOVERED**：抢到松球
- **SCREEN_ASSISTS**：掩护助攻
- **BOX_OUTS**：卡位

---

### 14. LeagueHustleStatsTeam（球队拼抢统计）

**端点描述：** 全联盟球队的拼抢数据汇总

---

## 比赛查找与赛程

### 15. LeagueGameFinder（联赛比赛查找器）

**端点描述：** 根据条件查找符合的比赛

**URL：** `https://stats.nba.com/stats/leaguegamefinder`

**参数：**
- **Season**（season_nullable）：赛季
- **TeamID**（team_id_nullable）：球队 ID
- **PlayerID**（player_or_team）：球员 ID
- **DateFrom**（date_from_nullable）：起始日期
- **DateTo**（date_to_nullable）：结束日期
- **VsTeamID**（vs_team_id_nullable）：对阵球队 ID

**返回数据集：**

#### LeagueGameFinderResults（比赛结果）
包含符合条件的所有比赛及其统计数据

**使用示例：**
```python
from nba_api.stats.endpoints import leaguegamefinder

# 查找勇士队 2023-24 赛季的所有比赛
game_finder = leaguegamefinder.LeagueGameFinder(
    team_id_nullable='1610612744',
    season_nullable='2023-24'
)

games = game_finder.league_game_finder_results.get_data_frame()

print(f"共找到 {len(games)} 场比赛")
print(games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS', 'REB', 'AST']].head(10))

# 查找得分超过120分的比赛
high_scoring = games[games['PTS'] >= 120]
print(f"\n得分>=120的比赛: {len(high_scoring)} 场")

# 查找对阵湖人的比赛
vs_lakers = leaguegamefinder.LeagueGameFinder(
    team_id_nullable='1610612744',
    vs_team_id_nullable='1610612747',
    season_nullable='2023-24'
)
lakers_games = vs_lakers.league_game_finder_results.get_data_frame()
print("\n对阵湖人:")
print(lakers_games[['GAME_DATE', 'MATCHUP', 'WL', 'PTS']])
```

---

### 16. LeagueGameLog（联赛比赛日志）

**端点描述：** 获取某赛季所有比赛的日志

**URL：** `https://stats.nba.com/stats/leaguegamelog`

**参数：**
- **Season**（season）：赛季
- **SeasonType**（season_type）：赛季类型
- **PlayerOrTeam**（player_or_team）：球员或球队视角
- **Sorter**（sorter）：排序字段
- **Direction**（direction）：排序方向

**使用场景：** 获取全联盟某天/某周的所有比赛数据

---

### 17. LeagueSeasonMatchups（赛季对位）

**端点描述：** 获取赛季中的球员对位数据

**使用场景：** 分析球员之间的对位表现

---

## 其他联赛功能

### 18. LeagueLineupViz（阵容可视化）

**端点描述：** 获取各种阵容组合的统计数据

**URL：** `https://stats.nba.com/stats/leaguelineupviz`

**使用场景：** 分析五人阵容的效率和表现

---

### 19. SynergyPlayTypes（协同进攻类型）

**端点描述：** 获取基于 Synergy Sports 的进攻类型统计

**URL：** `https://stats.nba.com/stats/synergyplaytypes`

**进攻类型包括：**
- **Isolation**：单打
- **PRBallHandler**：挡拆持球人
- **PRRollman**：挡拆掩护人
- **Postup**：低位单打
- **Spotup**：定点投篮
- **Handoff**：手递手
- **Cut**：空切
- **OffScreen**：绕掩护
- **OffRebound**：二次进攻
- **Transition**：快攻

**参数：**
- **PlayType**（play_type）：进攻类型
- **Season**（season）：赛季
- **PlayerOrTeam**（player_or_team）：球员或球队维度

**使用示例：**
```python
from nba_api.stats.endpoints import synergyplaytypes

# 获取全联盟球员的单打数据
isolation = synergyplaytypes.SynergyPlayTypes(
    play_type_nullable='Isolation',
    season='2023-24',
    player_or_team_abbreviation='P',  # P=Player, T=Team
    type_grouping_nullable='offensive'
)

iso_stats = isolation.synergy_play_type.get_data_frame()

# 单打效率最高的球员
top_iso = iso_stats.sort_values('PPP', ascending=False)  # PPP = Points Per Possession
print("单打效率榜（PPP）:")
print(top_iso[['PLAYER_NAME', 'TEAM_ABBREVIATION', 'POSS_PCT',
               'PPP', 'PERCENTILE']].head(20))

# 挡拆持球数据
pick_roll = synergyplaytypes.SynergyPlayTypes(
    play_type_nullable='PRBallHandler',
    season='2023-24',
    player_or_team_abbreviation='P'
)

pr_stats = pick_roll.synergy_play_type.get_data_frame()
print("\n挡拆持球效率榜:")
print(pr_stats.sort_values('PPP', ascending=False)[
    ['PLAYER_NAME', 'POSS_PCT', 'PPP', 'FG_PCT']].head(15))
```

---

### 20. VideoStatus（视频状态）

**端点描述：** 获取比赛视频的可用状态

**使用场景：** 检查比赛录像是否可用

---

## 使用指南

### 1. 全联盟排行榜

```python
from nba_api.stats.endpoints import leaguedashplayerstats

# 创建多个排行榜
categories = {
    'PTS': '得分',
    'REB': '篮板',
    'AST': '助攻',
    'STL': '抢断',
    'BLK': '盖帽',
    'FG_PCT': '命中率',
    'FG3_PCT': '三分命中率'
}

for stat, name in categories.items():
    stats = leaguedashplayerstats.LeagueDashPlayerStats(
        season='2023-24',
        per_mode='PerGame'
    )

    data = stats.league_dash_player_stats.get_data_frame()

    # 筛选出场次>=20场
    qualified = data[data['GP'] >= 20]

    # 按统计类别排序
    top_players = qualified.nlargest(10, stat)

    print(f"\n{name}榜:")
    print(top_players[['PLAYER_NAME', 'TEAM_ABBREVIATION', 'GP', stat]])
```

### 2. 球队实力对比

```python
from nba_api.stats.endpoints import leaguedashteamstats

# 获取高级统计
advanced = leaguedashteamstats.LeagueDashTeamStats(
    season='2023-24',
    measure_type='Advanced'
)

teams = advanced.league_dash_team_stats.get_data_frame()

# 四象限分析（进攻效率 vs 防守效率）
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 8))
plt.scatter(teams['OFF_RATING'], teams['DEF_RATING'])

for idx, row in teams.iterrows():
    plt.annotate(row['TEAM_ABBREVIATION'],
                (row['OFF_RATING'], row['DEF_RATING']))

plt.xlabel('进攻效率 (OFF_RATING)')
plt.ylabel('防守效率 (DEF_RATING)')
plt.title('球队四象限分析')
plt.axhline(teams['DEF_RATING'].mean(), color='gray', linestyle='--')
plt.axvline(teams['OFF_RATING'].mean(), color='gray', linestyle='--')
plt.gca().invert_yaxis()  # 防守效率越低越好
plt.show()
```

### 3. 比赛数据批量分析

```python
from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd

# 获取所有比赛
game_finder = leaguegamefinder.LeagueGameFinder(
    season_nullable='2023-24',
    season_type_nullable='Regular Season'
)

all_games = game_finder.league_game_finder_results.get_data_frame()

# 分析比分趋势
print(f"平均得分: {all_games['PTS'].mean():.1f}")
print(f"最高得分: {all_games['PTS'].max()}")
print(f"最低得分: {all_games['PTS'].min()}")

# 分析主场优势
home_games = all_games[all_games['MATCHUP'].str.contains('vs.')]
away_games = all_games[all_games['MATCHUP'].str.contains('@')]

home_wins = (home_games['WL'] == 'W').sum()
away_wins = (away_games['WL'] == 'W').sum()

print(f"\n主场胜率: {home_wins/len(home_games):.1%}")
print(f"客场胜率: {away_wins/len(away_games):.1%}")
```

### 4. 进攻类型分析

```python
from nba_api.stats.endpoints import synergyplaytypes

play_types = ['Isolation', 'PRBallHandler', 'Postup', 'Spotup', 'Transition']

results = {}

for pt in play_types:
    synergy = synergyplaytypes.SynergyPlayTypes(
        play_type_nullable=pt,
        season='2023-24',
        player_or_team_abbreviation='T'  # 球队维度
    )

    data = synergy.synergy_play_type.get_data_frame()
    results[pt] = data

# 对比各球队在不同进攻类型中的效率
team_id = '1610612744'  # 勇士队

for pt_name, df in results.items():
    team_data = df[df['TEAM_ID'] == int(team_id)]
    if not team_data.empty:
        print(f"\n{pt_name}:")
        print(team_data[['TEAM_NAME', 'POSS_PCT', 'PPP', 'PERCENTILE']])
```

---

## 常见使用场景

### 场景 1：赛季总结报告
```python
# 排行榜 + 球队排名 + 关键数据对比
```

### 场景 2：MVP 候选分析
```python
# 球员统计排名 + 球队战绩 + 关键时刻表现
```

### 场景 3：球队建设建议
```python
# 全联盟数据对比 + 短板分析 + 市场调研
```

### 场景 4：数据可视化
```python
# 导出数据 + 图表分析 + 趋势预测
```

---

## 注意事项

1. **数据量大**：联赛级端点返回大量数据，注意筛选
2. **性能考虑**：合理使用筛选条件减少数据量
3. **数据更新**：赛季进行中数据会不断更新
4. **比较基准**：注意统计模式（Totals/PerGame/Per36）
5. **资格要求**：某些排行榜有出场次数/时间要求

---

## 相关资源

- [总览文档](./NBA_API_OVERVIEW.md)
- [静态数据模块](./API_STATIC_DATA.md)
- [比赛数据接口](./API_GAME_DATA.md)
- [球员统计接口](./API_PLAYER_STATS.md)
- [球队统计接口](./API_TEAM_STATS.md)

**GitHub 端点文档：**
- [LeagueDashPlayerStats](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leaguedashplayerstats.md)
- [LeagueGameFinder](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leaguegamefinder.md)
- [SynergyPlayTypes](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/synergyplaytypes.md)
