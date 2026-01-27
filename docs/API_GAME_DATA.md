# NBA API - 比赛数据接口文档

> 本文档整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 目录

- [概述](#概述)
- [Box Score 系列端点](#box-score-系列端点)
  - [传统统计](#1-boxscoretraditionalv2-传统统计)
  - [高级统计](#2-boxscoreadvancedv2-高级统计)
  - [得分统计](#3-boxscorescoringv2-得分统计)
  - [防守统计](#4-boxscoredefensivev2-防守统计)
  - [杂项统计](#5-boxscoremiscv2-杂项统计)
  - [使用率统计](#6-boxscoreusagev2-使用率统计)
  - [四因素统计](#7-boxscorefourfactorsv2-四因素统计)
  - [球员追踪统计](#8-boxscoreplayertrackv2-球员追踪统计)
- [比赛详情端点](#比赛详情端点)
- [使用指南](#使用指南)

---

## 概述

比赛数据接口提供了丰富的 NBA 比赛统计信息，主要包括：

### Box Score 系列（18 个变体）
提供比赛的各种维度统计数据，从传统数据到高级指标

### 比赛详情系列
提供比赛的逐回合数据、轮换信息等详细内容

**关键特点：**
- ✅ 所有端点都需要 `game_id` 参数（10 位数字）
- ✅ 支持按时期（Period）和时间范围筛选数据
- ✅ 同时提供球员级和球队级统计
- ✅ 数据可导出为 DataFrame、JSON 或字典格式

---

## Box Score 系列端点

### 通用参数说明

所有 Box Score V2 端点都使用以下参数：

| 参数名 | Python 变量名 | 类型 | 必需 | 说明 |
|--------|-------------|------|------|------|
| GameID | game_id | string | ✓ | 比赛 ID（10 位数字，如 `0021700807`） |
| StartPeriod | start_period | int | ✓ | 开始节次（1=第1节，5=加时1） |
| EndPeriod | end_period | int | ✓ | 结束节次 |
| StartRange | start_range | int | ✓ | 开始时间范围（秒） |
| EndRange | end_range | int | ✓ | 结束时间范围（秒） |
| RangeType | range_type | int | ✓ | 范围类型（0=整场，1=按时间范围） |

**常用参数值：**
```python
# 获取整场比赛数据
start_period=1, end_period=10,
start_range=0, end_range=0, range_type=0

# 获取前两节数据
start_period=1, end_period=2,
start_range=0, end_range=0, range_type=0
```

---

### 1. BoxScoreTraditionalV2（传统统计）

**端点描述：** 获取比赛的传统盒子分数统计，包括得分、篮板、助攻等基础数据

**URL：** `https://stats.nba.com/stats/boxscoretraditionalv2`

**返回数据集：**

#### PlayerStats（球员统计）- 29 个字段
包含字段：
- **基本信息**：GAME_ID、TEAM_ID、TEAM_ABBREVIATION、TEAM_CITY、PLAYER_ID、PLAYER_NAME、START_POSITION、COMMENT
- **上场时间**：MIN
- **投篮**：FGM、FGA、FG_PCT、FG3M、FG3A、FG3_PCT、FTM、FTA、FT_PCT
- **篮板**：OREB、DREB、REB
- **其他**：AST、STL、BLK、TO、PF、PTS、PLUS_MINUS

#### TeamStarterBenchStats（首发替补统计）- 25 个字段
区分首发和替补球员的统计数据

#### TeamStats（球队统计）- 26 个字段
球队层面的汇总统计

**使用示例：**
```python
from nba_api.stats.endpoints import boxscoretraditionalv2

# 获取比赛的传统统计数据
boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(
    game_id='0021700807',
    start_period=1,
    end_period=10,
    start_range=0,
    end_range=0,
    range_type=0
)

# 获取球员统计
player_stats = boxscore.player_stats.get_data_frame()

# 获取球队统计
team_stats = boxscore.team_stats.get_data_frame()
```

---

### 2. BoxScoreAdvancedV2（高级统计）

**端点描述：** 获取比赛的高级统计数据，包括进攻效率、防守效率、真实命中率等

**URL：** `https://stats.nba.com/stats/boxscoreadvancedv2`

**参数：** 与通用参数相同

**返回数据集：**

#### PlayerStats（球员高级统计）- 33 个字段
包含字段：
- **基本信息**：GAME_ID、TEAM_ID、PLAYER_ID、PLAYER_NAME 等
- **上场时间**：MIN
- **效率评分**：OFF_RATING（进攻效率）、DEF_RATING（防守效率）、NET_RATING（净效率）
- **高级指标**：
  - AST_PCT（助攻率）
  - AST_TOV（助攻失误比）
  - AST_RATIO（助攻比率）
  - OREB_PCT（进攻篮板率）
  - DREB_PCT（防守篮板率）
  - REB_PCT（总篮板率）
  - TM_TOV_PCT（球队失误率）
  - EFG_PCT（有效命中率）
  - TS_PCT（真实命中率）
  - USG_PCT（使用率）
  - PACE（节奏）
  - PIE（球员影响估值）

#### TeamStats（球队高级统计）- 30 个字段
球队层面的高级效率指标

**使用示例：**
```python
from nba_api.stats.endpoints import boxscoreadvancedv2

boxscore_adv = boxscoreadvancedv2.BoxScoreAdvancedV2(
    game_id='0021700807'
)

# 获取高级统计
advanced_stats = boxscore_adv.player_stats.get_data_frame()

# 查看球员效率
print(advanced_stats[['PLAYER_NAME', 'OFF_RATING', 'DEF_RATING', 'NET_RATING']])
```

---

### 3. BoxScoreScoringV2（得分统计）

**端点描述：** 获取比赛的得分构成统计，包括各种得分方式的占比

**URL：** `https://stats.nba.com/stats/boxscorescoringv2`

**参数：** 与通用参数相同

**返回数据集：**

#### sqlPlayersScoring（球员得分统计）- 24 个字段
包含字段：
- **基本信息**：GAME_ID、TEAM_ID、PLAYER_ID、PLAYER_NAME 等
- **得分占比**：
  - PCT_FGA_2PT（2 分球出手占比）
  - PCT_FGA_3PT（3 分球出手占比）
  - PCT_PTS_2PT（2 分球得分占比）
  - PCT_PTS_2PT_MR（中距离得分占比）
  - PCT_PTS_3PT（3 分球得分占比）
  - PCT_PTS_FB（快攻得分占比）
  - PCT_PTS_FT（罚球得分占比）
  - PCT_PTS_OFF_TOV（对手失误得分占比）
  - PCT_PTS_PAINT（油漆区得分占比）
  - PCT_AST_2PM（2 分球助攻占比）
  - PCT_UAST_2PM（2 分球非助攻占比）
  - PCT_AST_3PM（3 分球助攻占比）
  - PCT_UAST_3PM（3 分球非助攻占比）

#### sqlTeamsScoring（球队得分统计）- 23 个字段
球队层面的得分构成数据

**使用场景：** 分析球队或球员的得分方式、判断进攻风格

---

### 4. BoxScoreDefensiveV2（防守统计）

**端点描述：** 获取比赛的防守统计数据，包括对位防守表现

**URL：** `https://stats.nba.com/stats/boxscoredefensivev2`

**参数：**
- **GameID**（game_id）: 比赛 ID（必需）

**返回数据集：**

#### PlayerStats（球员防守统计）- 31 个字段
包含字段：
- **基本防守数据**：STEALS、BLOCKS、DEFENSIVE_REBOUNDS
- **对位防守**：
  - MATCHUP_MINUTES（对位时间）
  - MATCHUP_ASSISTS（对位时允许的助攻）
  - MATCHUP_TURNOVERS（对位时造成的失误）
  - MATCHUP_FIELD_GOALS_MADE/ATTEMPTED（对位时对手投篮）
  - MATCHUP_FIELD_GOAL_PERCENTAGE（对位时对手命中率）

#### TeamStats（球队防守统计）- 7 个字段
球队基本防守信息

**使用示例：**
```python
from nba_api.stats.endpoints import boxscoredefensivev2

defense = boxscoredefensivev2.BoxScoreDefensiveV2(
    game_id='0021700807'
)

player_defense = defense.player_stats.get_data_frame()

# 查看防守表现
print(player_defense[['PLAYER_NAME', 'STEALS', 'BLOCKS',
                       'MATCHUP_FIELD_GOAL_PERCENTAGE']])
```

---

### 5. BoxScoreMiscV2（杂项统计）

**端点描述：** 获取比赛的杂项统计数据，包括二次进攻、快攻等特殊情况得分

**URL：** `https://stats.nba.com/stats/boxscoremiscv2`

**参数：** 与通用参数相同

**返回数据集：**

#### sqlPlayersMisc（球员杂项统计）- 22 个字段
包含字段：
- **己方得分**：
  - PTS_OFF_TOV（对手失误得分）
  - PTS_2ND_CHANCE（二次进攻得分）
  - PTS_FB（快攻得分）
  - PTS_PAINT（油漆区得分）
- **对手得分**：
  - OPP_PTS_OFF_TOV（己方失误丢分）
  - OPP_PTS_2ND_CHANCE（对手二次进攻得分）
  - OPP_PTS_FB（对手快攻得分）
  - OPP_PTS_PAINT（对手油漆区得分）
- **犯规数据**：
  - BLK（盖帽）、BLKA（被盖帽）
  - PF（犯规）、PFD（造犯规）

#### sqlTeamsMisc（球队杂项统计）- 19 个字段
球队层面的杂项数据

**使用场景：** 分析快攻效率、二次进攻能力、造犯规能力等

---

### 6. BoxScoreUsageV2（使用率统计）

**端点描述：** 获取比赛的使用率统计，显示球员在各项数据中的占比

**URL：** `https://stats.nba.com/stats/boxscoreusagev2`

**参数：** 与通用参数相同

**返回数据集：**

#### sqlPlayersUsage（球员使用率）- 27 个字段
包含字段：
- **USG_PCT**：使用率（球员结束回合占比）
- **各项占比**：
  - PCT_FGM/PCT_FGA（投篮占比）
  - PCT_FG3M/PCT_FG3A（三分球占比）
  - PCT_FTM/PCT_FTA（罚球占比）
  - PCT_OREB/PCT_DREB/PCT_REB（篮板占比）
  - PCT_AST（助攻占比）
  - PCT_TOV（失误占比）
  - PCT_STL（抢断占比）
  - PCT_BLK/PCT_BLKA（盖帽占比）
  - PCT_PF/PCT_PFD（犯规占比）
  - PCT_PTS（得分占比）

#### sqlTeamsUsage（球队使用率）- 25 个字段
球队各项数据的分布

**使用场景：** 分析球员在球队中的作用和贡献占比

---

### 7. BoxScoreFourFactorsV2（四因素统计）

**端点描述：** 获取比赛的四因素分析数据（篮球分析的核心指标）

**URL：** `https://stats.nba.com/stats/boxscorefourfactorsv2`

**参数：** 与通用参数相同

**四因素说明：**
1. **有效命中率（EFG_PCT）**：考虑三分球价值的命中率
2. **罚球率（FTA_RATE）**：造罚球能力
3. **失误率（TM_TOV_PCT）**：失误控制能力
4. **进攻篮板率（OREB_PCT）**：二次进攻机会

**返回数据集：**

#### sqlPlayersFourFactors（球员四因素）- 16 个字段
包含字段：
- **进攻四因素**：EFG_PCT、FTA_RATE、TM_TOV_PCT、OREB_PCT
- **防守四因素**：OPP_EFG_PCT、OPP_FTA_RATE、OPP_TOV_PCT、OPP_OREB_PCT

#### sqlTeamsFourFactors（球队四因素）- 14 个字段
球队层面的四因素数据

**使用示例：**
```python
from nba_api.stats.endpoints import boxscorefourfactorsv2

four_factors = boxscorefourfactorsv2.BoxScoreFourFactorsV2(
    game_id='0021700807'
)

factors = four_factors.sql_players_four_factors.get_data_frame()

# 查看球员四因素表现
print(factors[['PLAYER_NAME', 'EFG_PCT', 'FTA_RATE',
                'TM_TOV_PCT', 'OREB_PCT']])
```

---

### 8. BoxScorePlayerTrackV2（球员追踪统计）

**端点描述：** 获取比赛的球员追踪数据（基于运动追踪技术）

**URL：** `https://stats.nba.com/stats/boxscoreplayertrackv2`

**参数：** 与通用参数相同

**返回数据集：**

#### PlayerStats（球员追踪统计）
包含字段（基于 SportVU 追踪系统）：
- **移动数据**：
  - SPEED（平均速度）
  - DISTANCE（移动距离）
- **触球数据**：
  - TOUCHES（触球次数）
  - AVG_SEC_PER_TOUCH（平均持球时间）
  - AVG_DRIB_PER_TOUCH（平均每次触球运球数）
- **传球数据**：
  - PASSES_MADE（传球次数）
  - PASSES_RECEIVED（接球次数）
- **对抗数据**：
  - CONTESTED_SHOTS（受干扰投篮）
  - DEFLECTIONS（干扰球次数）

#### TeamStats（球队追踪统计）
球队层面的追踪数据汇总

**使用场景：** 深度分析球员活动量、持球习惯、传球倾向等

---

### 其他 Box Score 端点

#### 9. BoxScoreSummaryV2
**功能：** 比赛摘要信息（比分、场馆、裁判等）

#### 10. BoxScoreHustleV2
**功能：** 拼抢数据（争球、扑地板球、干扰等）

#### 11. BoxScoreMatchupsV2
**功能：** 球员对位数据

---

## 比赛详情端点

### PlayByPlayV2（逐回合数据）

**端点描述：** 获取比赛的逐回合详细数据，记录每个事件

**URL：** `https://stats.nba.com/stats/playbyplayv2`

**参数：**

| 参数名 | Python 变量名 | 类型 | 必需 | 说明 |
|--------|-------------|------|------|------|
| GameID | game_id | string | ✓ | 比赛 ID（10 位数字） |
| StartPeriod | start_period | int | ✓ | 开始节次 |
| EndPeriod | end_period | int | ✓ | 结束节次 |

**返回数据集：**

#### PlayByPlay（逐回合数据）- 34 个字段
包含字段：
- **事件信息**：
  - EVENTNUM（事件编号）
  - EVENTMSGTYPE（事件类型：投篮、犯规、换人等）
  - EVENTMSGACTIONTYPE（事件子类型）
- **时间信息**：
  - PERIOD（节次）
  - PCTIMESTRING（节内时间）
  - WCTIMESTRING（实际时间）
- **描述信息**：
  - HOMEDESCRIPTION（主队事件描述）
  - VISITORDESCRIPTION（客队事件描述）
  - NEUTRALDESCRIPTION（中性事件描述）
- **比分信息**：
  - SCORE（当前比分）
  - SCOREMARGIN（分差）
- **球员信息**（最多3名球员）：
  - PLAYER1_ID/NAME/TEAM_*（主要球员）
  - PLAYER2_ID/NAME/TEAM_*（关联球员1）
  - PLAYER3_ID/NAME/TEAM_*（关联球员2）
- **视频**：VIDEO_AVAILABLE_FLAG

#### AvailableVideo
视频可用性标志

**使用示例：**
```python
from nba_api.stats.endpoints import playbyplayv2

pbp = playbyplayv2.PlayByPlayV2(
    game_id='0021700807',
    start_period=1,
    end_period=10
)

plays = pbp.play_by_play.get_data_frame()

# 查看所有进球事件
scores = plays[plays['EVENTMSGTYPE'] == 1]  # 1 = 投篮命中
print(scores[['PCTIMESTRING', 'PLAYER1_NAME', 'HOMEDESCRIPTION', 'SCORE']])
```

**事件类型代码：**
- 1: 投篮命中
- 2: 投篮未中
- 3: 罚球
- 4: 篮板
- 5: 失误
- 6: 犯规
- 8: 换人
- 10: 跳球
- 12: 节开始
- 13: 节结束

---

### GameRotation（球员轮换）

**端点描述：** 获取比赛的球员轮换数据，显示球员上下场时间

**URL：** `https://stats.nba.com/stats/gamerotation`

**参数：**
- **GameID**（game_id）: 比赛 ID
- **LeagueID**（league_id）: 联赛 ID（默认 "00"）

**返回数据集：**
- **HomeTeam/VisitorTeam**：主客队轮换数据
- 字段包括：球员上场时间段、在场时比分情况等

---

### WinProbabilityPBP（胜率逐回合）

**端点描述：** 获取比赛中每个回合的实时胜率预测

**URL：** `https://stats.nba.com/stats/winprobabilitypbp`

**使用场景：** 分析比赛走势、关键时刻判断

---

## 使用指南

### 1. 如何获取 Game ID

```python
from nba_api.stats.endpoints import leagueGameFinder

# 查找特定球队的比赛
game_finder = leagueGameFinder.LeagueGameFinder(
    team_id_nullable='1610612744',  # 勇士队
    season_nullable='2023-24'
)

games = game_finder.get_data_frames()[0]
game_id = games.iloc[0]['GAME_ID']
print(f"比赛 ID: {game_id}")
```

### 2. 完整分析示例

```python
from nba_api.stats.endpoints import (
    boxscoretraditionalv2,
    boxscoreadvancedv2,
    playbyplayv2
)

game_id = '0021700807'

# 1. 获取传统统计
traditional = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
player_stats = traditional.player_stats.get_data_frame()

# 2. 获取高级统计
advanced = boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id)
advanced_stats = advanced.player_stats.get_data_frame()

# 3. 合并数据
full_stats = player_stats.merge(
    advanced_stats[['PLAYER_ID', 'OFF_RATING', 'DEF_RATING', 'NET_RATING']],
    on='PLAYER_ID'
)

# 4. 获取逐回合数据
pbp = playbyplayv2.PlayByPlayV2(game_id=game_id)
plays = pbp.play_by_play.get_data_frame()

# 分析关键时刻
clutch_plays = plays[
    (plays['PERIOD'] >= 4) &  # 第四节及加时
    (plays['PCTIMESTRING'] <= '00:05:00')  # 最后5分钟
]
```

### 3. 性能优化建议

```python
# 只获取需要的节次数据
boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(
    game_id='0021700807',
    start_period=4,  # 只获取第四节
    end_period=4,
    start_range=0,
    end_range=0,
    range_type=0
)

# 使用字典格式（更快）
data = boxscore.get_dict()

# 添加超时设置
boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(
    game_id='0021700807',
    timeout=30
)
```

### 4. 常见使用场景

#### 场景 1：比赛完整报告
```python
# 传统数据 + 高级数据 + 四因素
```

#### 场景 2：球员表现分析
```python
# 得分方式 + 使用率 + 防守表现
```

#### 场景 3：比赛关键时刻分析
```python
# 逐回合数据 + 胜率变化
```

#### 场景 4：球队战术分析
```python
# 轮换数据 + 对位数据 + 追踪数据
```

---

## 注意事项

1. **Game ID 格式**：必须是 10 位数字字符串（如 `"0021700807"`）
2. **时期参数**：常规赛 1-4 节，第 5 期开始为加时
3. **时间范围**：`range_type=0` 时忽略 start_range 和 end_range
4. **数据可用性**：某些高级数据可能不适用于所有比赛
5. **请求频率**：避免过于频繁的 API 请求
6. **数据延迟**：比赛结束后数据可能需要一段时间才能完全可用

---

## 相关资源

- [总览文档](./NBA_API_OVERVIEW.md)
- [静态数据模块](./API_STATIC_DATA.md)
- [球员统计接口](./API_PLAYER_STATS.md)
- [球队统计接口](./API_TEAM_STATS.md)
- [Live API 接口](./API_LIVE_ENDPOINTS.md)

**GitHub 端点文档：**
- [BoxScoreTraditionalV2](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/boxscoretraditionalv2.md)
- [BoxScoreAdvancedV2](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/boxscoreadvancedv2.md)
- [PlayByPlayV2](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/playbyplayv2.md)
