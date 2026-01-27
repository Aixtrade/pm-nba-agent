# NBA API - Live API 接口文档

> 本文档整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 目录

- [概述](#概述)
- [ScoreBoard（实时比分板）](#scoreboard实时比分板)
- [BoxScore（实时比赛统计）](#boxscore实时比赛统计)
- [PlayByPlay（实时逐回合）](#playbyplay实时逐回合)
- [使用指南](#使用指南)

---

## 概述

Live API 是 nba_api 提供的实时数据接口，用于获取当前比赛的即时信息。

### 核心特点

- ✅ **实时数据**：提供正在进行的比赛的实时更新
- ✅ **低延迟**：数据延迟通常在几秒到几十秒
- ✅ **不同数据源**：使用 `cdn.nba.com` 而非 `stats.nba.com`
- ✅ **JSON格式**：原生 JSON 数据结构
- ✅ **无需认证**：公开访问，无需特殊权限

### 主要端点

1. **ScoreBoard**：今日所有比赛的比分板
2. **BoxScore**：特定比赛的详细统计
3. **PlayByPlay**：特定比赛的逐回合数据

**与 Stats API 的区别：**

| 特性 | Live API | Stats API |
|------|---------|-----------|
| 数据源 | cdn.nba.com | stats.nba.com |
| 数据时效 | 实时（秒级延迟） | 历史/完整数据 |
| 数据格式 | JSON | 多种格式 |
| 使用场景 | 实时追踪、比分更新 | 历史分析、深度统计 |
| 数据完整性 | 进行中的比赛 | 已完成的比赛 |

---

## ScoreBoard（实时比分板）

### 端点描述

获取今日所有比赛的实时比分板，包括比分、状态、球队信息等。

### URL

`https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json`

### 参数

**无参数**：自动返回今日比赛（基于NBA总部所在时区）

### 导入方式

```python
from nba_api.live.nba.endpoints import scoreboard
```

### 返回数据结构

#### 主要字段

```python
{
    "meta": {
        "version": 版本号,
        "code": 状态码,
        "request": 请求时间,
        "time": 响应时间
    },
    "scoreboard": {
        "gameDate": "比赛日期",
        "leagueId": "联赛ID",
        "leagueName": "联赛名称",
        "games": [
            {
                "gameId": "比赛ID",
                "gameCode": "比赛代码",
                "gameStatus": 比赛状态,
                "gameStatusText": "比赛状态文本",
                "period": 当前节次,
                "gameClock": "比赛时钟",
                "gameTimeUTC": "UTC时间",
                "gameEt": "东部时间",
                "regulationPeriods": 常规节数,
                "seriesGameNumber": "系列赛场次",
                "seriesText": "系列赛文本",
                "homeTeam": {
                    "teamId": 球队ID,
                    "teamName": "球队名称",
                    "teamCity": "城市",
                    "teamTricode": "三字母缩写",
                    "score": 得分,
                    "inBonus": 是否进入加罚,
                    "timeoutsRemaining": 剩余暂停,
                    "periods": [节次得分列表]
                },
                "awayTeam": {
                    // 同homeTeam结构
                },
                "gameLeaders": {
                    "homeLeaders": {
                        "personId": 球员ID,
                        "name": "姓名",
                        "points": 得分,
                        "rebounds": 篮板,
                        "assists": 助攻
                    },
                    "awayLeaders": {
                        // 同homeLeaders结构
                    }
                }
            }
        ]
    }
}
```

#### 比赛状态码

- **1**：未开始（Scheduled）
- **2**：进行中（Live）
- **3**：已结束（Final）

### 使用示例

#### 示例 1：获取今日比赛列表

```python
from nba_api.live.nba.endpoints import scoreboard

# 获取今日比分板
board = scoreboard.ScoreBoard()

# 方法1：获取字典格式
games_dict = board.get_dict()
print(f"比赛日期: {games_dict['scoreboard']['gameDate']}")
print(f"今日比赛数: {len(games_dict['scoreboard']['games'])}")

# 方法2：获取JSON字符串
games_json = board.get_json()

# 遍历所有比赛
for game in games_dict['scoreboard']['games']:
    home = game['homeTeam']
    away = game['awayTeam']

    print(f"\n{away['teamTricode']} @ {home['teamTricode']}")
    print(f"比分: {away['score']} - {home['score']}")
    print(f"状态: {game['gameStatusText']}")
    print(f"节次: 第{game['period']}节 {game['gameClock']}")
```

#### 示例 2：筛选进行中的比赛

```python
from nba_api.live.nba.endpoints import scoreboard

board = scoreboard.ScoreBoard()
games = board.get_dict()['scoreboard']['games']

# 筛选进行中的比赛
live_games = [g for g in games if g['gameStatus'] == 2]

if len(live_games) > 0:
    print(f"当前有 {len(live_games)} 场比赛正在进行:")

    for game in live_games:
        home = game['homeTeam']
        away = game['awayTeam']

        print(f"\n{away['teamTricode']} {away['score']} @ {home['teamTricode']} {home['score']}")
        print(f"第{game['period']}节 {game['gameClock']}")

        # 显示领袖
        leaders = game['gameLeaders']
        if 'homeLeaders' in leaders and leaders['homeLeaders']:
            hl = leaders['homeLeaders']
            print(f"  主队领袖: {hl['name']} - {hl['points']}分/{hl['rebounds']}板/{hl['assists']}助")

        if 'awayLeaders' in leaders and leaders['awayLeaders']:
            al = leaders['awayLeaders']
            print(f"  客队领袖: {al['name']} - {al['points']}分/{al['rebounds']}板/{al['assists']}助")
else:
    print("当前没有进行中的比赛")
```

#### 示例 3：比分更新监控

```python
import time
from nba_api.live.nba.endpoints import scoreboard

def monitor_games(interval=30):
    """
    每隔指定秒数更新一次比分

    Args:
        interval: 更新间隔（秒）
    """
    while True:
        board = scoreboard.ScoreBoard()
        games = board.get_dict()['scoreboard']['games']

        live_games = [g for g in games if g['gameStatus'] == 2]

        print(f"\n{'='*60}")
        print(f"更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        if live_games:
            for game in live_games:
                home = game['homeTeam']
                away = game['awayTeam']

                print(f"\n{away['teamCity']} {away['teamName']} ({away['score']})")
                print(f"  @ ")
                print(f"{home['teamCity']} {home['teamName']} ({home['score']})")
                print(f"状态: 第{game['period']}节 {game['gameClock']}")
        else:
            print("当前没有进行中的比赛")

        time.sleep(interval)

# 使用示例（注意：这会无限循环）
# monitor_games(interval=30)  # 每30秒更新一次
```

---

## BoxScore（实时比赛统计）

### 端点描述

获取特定比赛的详细统计数据，包括球员统计、球队统计等。

### URL

`https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json`

### 参数

| 参数名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| GameID | string | ✓ | 比赛ID（10位数字） |

### 导入方式

```python
from nba_api.live.nba.endpoints import boxscore
```

### 返回数据结构

#### 主要字段

```python
{
    "meta": {...},  # 元数据
    "game": {
        "gameId": "比赛ID",
        "gameTimeLocal": "当地时间",
        "gameTimeUTC": "UTC时间",
        "gameEt": "东部时间",
        "attendance": 上座人数,
        "sellout": 是否售罄,
        "arena": {
            "arenaId": 场馆ID,
            "arenaName": "场馆名称",
            "arenaCity": "城市",
            "arenaState": "州",
            "arenaCountry": "国家"
        },
        "officials": [
            {
                "personId": 裁判ID,
                "name": "裁判姓名",
                "nameI": "姓名缩写",
                "firstName": "名",
                "familyName": "姓",
                "jerseyNum": "号码",
                "assignment": "职位"
            }
        ],
        "homeTeam": {
            "teamId": 球队ID,
            "teamName": "球队名",
            "teamCity": "城市",
            "teamTricode": "缩写",
            "score": 得分,
            "inBonus": 加罚状态,
            "timeoutsRemaining": 剩余暂停,
            "periods": [节次得分],
            "players": [
                {
                    "status": "状态",
                    "order": 顺序,
                    "personId": 球员ID,
                    "jerseyNum": "球衣号",
                    "name": "姓名",
                    "nameI": "姓名缩写",
                    "position": "位置",
                    "starter": "是否首发",
                    "oncourt": "是否在场",
                    "played": "是否出场",
                    "statistics": {
                        "assists": 助攻,
                        "blocks": 盖帽,
                        "blocksReceived": 被盖,
                        "fieldGoalsAttempted": 投篮出手,
                        "fieldGoalsMade": 投篮命中,
                        "fieldGoalsPercentage": 命中率,
                        "foulsOffensive": 进攻犯规,
                        "foulsDrawn": 造犯规,
                        "foulsPersonal": 个人犯规,
                        "foulsTechnical": 技术犯规,
                        "freeThrowsAttempted": 罚球出手,
                        "freeThrowsMade": 罚球命中,
                        "freeThrowsPercentage": 罚球命中率,
                        "minus": 在场失分,
                        "minutes": "上场时间",
                        "minutesCalculated": "计算时间",
                        "plus": 在场得分,
                        "plusMinusPoints": 正负值,
                        "points": 得分,
                        "pointsFastBreak": 快攻得分,
                        "pointsInThePaint": 油漆区得分,
                        "pointsSecondChance": 二次进攻得分,
                        "reboundsDefensive": 防守篮板,
                        "reboundsOffensive": 进攻篮板,
                        "reboundsTotal": 总篮板,
                        "steals": 抢断,
                        "threePointersAttempted": 三分出手,
                        "threePointersMade": 三分命中,
                        "threePointersPercentage": 三分命中率,
                        "turnovers": 失误,
                        "twoPointersAttempted": 两分出手,
                        "twoPointersMade": 两分命中,
                        "twoPointersPercentage": 两分命中率
                    }
                }
            ],
            "statistics": {
                // 球队统计（字段同球员统计）
            }
        },
        "awayTeam": {
            // 同homeTeam结构
        }
    }
}
```

### 使用示例

#### 示例 1：获取比赛详细统计

```python
from nba_api.live.nba.endpoints import boxscore

# 使用比赛ID获取BoxScore
game_id = '0022300500'
box = boxscore.BoxScore(game_id=game_id)

# 获取数据
game_data = box.get_dict()['game']

# 比赛信息
print(f"比赛: {game_data['awayTeam']['teamTricode']} @ {game_data['homeTeam']['teamTricode']}")
print(f"场馆: {game_data['arena']['arenaName']}, {game_data['arena']['arenaCity']}")
print(f"上座: {game_data.get('attendance', 'N/A')}")

# 裁判信息
print("\n裁判:")
for official in game_data['officials']:
    print(f"  {official['name']} - {official['assignment']}")

# 主队球员统计
print(f"\n{game_data['homeTeam']['teamName']} 球员统计:")
for player in game_data['homeTeam']['players']:
    if player['played'] == '1':
        stats = player['statistics']
        print(f"{player['name']:20} {stats['minutes']:>6} {stats['points']:>3}分 "
              f"{stats['reboundsTotal']:>2}板 {stats['assists']:>2}助 "
              f"{stats['fieldGoalsMade']}-{stats['fieldGoalsAttempted']} FG")
```

#### 示例 2：球队统计对比

```python
from nba_api.live.nba.endpoints import boxscore

game_id = '0022300500'
box = boxscore.BoxScore(game_id=game_id)
game = box.get_dict()['game']

home_stats = game['homeTeam']['statistics']
away_stats = game['awayTeam']['statistics']

print(f"{game['awayTeam']['teamTricode']} vs {game['homeTeam']['teamTricode']}\n")

stats_to_compare = [
    ('points', '得分'),
    ('fieldGoalsPercentage', '命中率'),
    ('threePointersPercentage', '三分命中率'),
    ('freeThrowsPercentage', '罚球命中率'),
    ('reboundsTotal', '篮板'),
    ('assists', '助攻'),
    ('steals', '抢断'),
    ('blocks', '盖帽'),
    ('turnovers', '失误')
]

for stat_key, stat_name in stats_to_compare:
    away_val = away_stats.get(stat_key, 0)
    home_val = home_stats.get(stat_key, 0)

    print(f"{stat_name:10} {away_val:>8} - {home_val:<8}")
```

#### 示例 3：查找比赛领袖

```python
from nba_api.live.nba.endpoints import boxscore

def find_game_leaders(game_id):
    """找出比赛中各项统计的领袖"""
    box = boxscore.BoxScore(game_id=game_id)
    game = box.get_dict()['game']

    all_players = []

    # 收集所有出场球员
    for team_key in ['homeTeam', 'awayTeam']:
        team = game[team_key]
        for player in team['players']:
            if player['played'] == '1':
                stats = player['statistics']
                all_players.append({
                    'name': player['name'],
                    'team': team['teamTricode'],
                    'points': stats.get('points', 0),
                    'rebounds': stats.get('reboundsTotal', 0),
                    'assists': stats.get('assists', 0),
                    'steals': stats.get('steals', 0),
                    'blocks': stats.get('blocks', 0)
                })

    # 找出各项领袖
    leaders = {
        '得分王': max(all_players, key=lambda x: x['points']),
        '篮板王': max(all_players, key=lambda x: x['rebounds']),
        '助攻王': max(all_players, key=lambda x: x['assists']),
        '抢断王': max(all_players, key=lambda x: x['steals']),
        '盖帽王': max(all_players, key=lambda x: x['blocks'])
    }

    print("比赛领袖:\n")
    for title, player in leaders.items():
        print(f"{title}: {player['name']} ({player['team']}) - "
              f"{player['points']}分/{player['rebounds']}板/{player['assists']}助")

# 使用示例
# find_game_leaders('0022300500')
```

---

## PlayByPlay（实时逐回合）

### 端点描述

获取比赛的逐回合详细数据，记录每个事件。

### URL

`https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json`

### 参数

| 参数名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| GameID | string | ✓ | 比赛ID（10位数字） |

### 导入方式

```python
from nba_api.live.nba.endpoints import playbyplay
```

### 返回数据结构

#### 主要字段

```python
{
    "meta": {...},
    "game": {
        "gameId": "比赛ID",
        "actions": [
            {
                "actionNumber": 事件编号,
                "clock": "时钟",
                "timeActual": "实际时间",
                "period": 节次,
                "periodType": "节次类型",
                "actionType": "事件类型",
                "subType": "子类型",
                "descriptor": "描述符",
                "qualifiers": ["限定符"],
                "personId": 球员ID,
                "x": X坐标,
                "y": Y坐标,
                "shotDistance": 投篮距离,
                "shotResult": "投篮结果",
                "isFieldGoal": 是否投篮,
                "scoreHome": 主队得分,
                "scoreAway": 客队得分,
                "pointsTotal": 该事件得分,
                "description": "事件描述",
                "personIdsFilter": [相关球员ID]
            }
        ]
    }
}
```

#### 事件类型

常见的actionType值：
- **1**：投篮命中
- **2**：投篮未中
- **3**：罚球
- **4**：篮板
- **5**：失误
- **6**：犯规
- **7**：违例
- **8**：换人
- **9**：暂停
- **10**：跳球
- **12**：节开始
- **13**：节结束

### 使用示例

#### 示例 1：获取逐回合数据

```python
from nba_api.live.nba.endpoints import playbyplay

game_id = '0022300500'
pbp = playbyplay.PlayByPlay(game_id=game_id)

game_data = pbp.get_dict()['game']
actions = game_data['actions']

print(f"比赛ID: {game_data['gameId']}")
print(f"总事件数: {len(actions)}\n")

# 显示最近10个事件
print("最近10个事件:")
for action in actions[-10:]:
    print(f"[Q{action['period']} {action['clock']}] {action.get('description', 'N/A')}")
```

#### 示例 2：统计投篮数据

```python
from nba_api.live.nba.endpoints import playbyplay

game_id = '0022300500'
pbp = playbyplay.PlayByPlay(game_id=game_id)
actions = pbp.get_dict()['game']['actions']

# 筛选投篮事件
shot_actions = [a for a in actions if a.get('isFieldGoal') == 1]

print(f"总投篮次数: {len(shot_actions)}")

# 按球员统计
from collections import defaultdict
player_shots = defaultdict(lambda: {'made': 0, 'missed': 0, 'total': 0})

for shot in shot_actions:
    person_id = shot.get('personId')
    if person_id:
        player_shots[person_id]['total'] += 1
        if shot.get('shotResult') == 'Made':
            player_shots[person_id]['made'] += 1
        else:
            player_shots[person_id]['missed'] += 1

# 显示投篮统计
for person_id, stats in player_shots.items():
    if stats['total'] >= 5:  # 至少5次出手
        pct = stats['made'] / stats['total'] * 100
        print(f"球员ID {person_id}: {stats['made']}/{stats['total']} ({pct:.1f}%)")
```

#### 示例 3：分析得分流

```python
from nba_api.live.nba.endpoints import playbyplay

def analyze_scoring_runs(game_id):
    """分析比赛中的得分流"""
    pbp = playbyplay.PlayByPlay(game_id=game_id)
    actions = pbp.get_dict()['game']['actions']

    # 筛选有得分的事件
    scoring_actions = [a for a in actions if a.get('pointsTotal', 0) > 0]

    current_run = {'team': None, 'points': 0, 'start_idx': 0}
    runs = []

    for idx, action in enumerate(scoring_actions):
        # 判断得分球队（简化处理）
        score_home = action.get('scoreHome', 0)
        score_away = action.get('scoreAway', 0)

        # 记录得分流
        # (实际实现需要更复杂的逻辑来判断球队)

    return runs

# 使用示例
# runs = analyze_scoring_runs('0022300500')
```

---

## 使用指南

### 1. 实时比分追踪应用

```python
from nba_api.live.nba.endpoints import scoreboard, boxscore
import time

def live_score_tracker():
    """实时比分追踪"""
    print("NBA实时比分追踪器")
    print("="*60)

    while True:
        try:
            # 获取比分板
            board = scoreboard.ScoreBoard()
            games = board.get_dict()['scoreboard']['games']

            # 清屏（可选）
            # import os
            # os.system('clear' if os.name == 'posix' else 'cls')

            print(f"\n更新时间: {time.strftime('%H:%M:%S')}")
            print("="*60)

            if not games:
                print("今日没有比赛")
            else:
                for game in games:
                    home = game['homeTeam']
                    away = game['awayTeam']

                    status_text = game['gameStatusText']
                    if game['gameStatus'] == 2:  # 进行中
                        status_text = f"第{game['period']}节 {game['gameClock']}"

                    print(f"\n{away['teamTricode']:3} {away['score']:>3}  @  "
                          f"{home['teamTricode']:3} {home['score']:>3}  |  {status_text}")

            time.sleep(10)  # 每10秒更新一次

        except KeyboardInterrupt:
            print("\n\n追踪器已停止")
            break
        except Exception as e:
            print(f"错误: {e}")
            time.sleep(10)

# 运行追踪器（注意：会无限循环）
# live_score_tracker()
```

### 2. 比赛数据完整分析

```python
from nba_api.live.nba.endpoints import boxscore, playbyplay

def full_game_analysis(game_id):
    """比赛完整分析"""

    # 1. 获取BoxScore
    box = boxscore.BoxScore(game_id=game_id)
    game = box.get_dict()['game']

    print("="*60)
    print(f"比赛分析: {game['awayTeam']['teamName']} @ {game['homeTeam']['teamName']}")
    print("="*60)

    # 2. 球队统计对比
    print("\n【球队统计】")
    home_stats = game['homeTeam']['statistics']
    away_stats = game['awayTeam']['statistics']

    print(f"{'统计项':<15} {'客队':>10} {'主队':>10}")
    print("-"*40)
    for key in ['points', 'fieldGoalsPercentage', 'threePointersPercentage',
                'reboundsTotal', 'assists', 'turnovers']:
        away_val = away_stats.get(key, 0)
        home_val = home_stats.get(key, 0)
        print(f"{key:<15} {away_val:>10} {home_val:>10}")

    # 3. 球员表现
    print("\n【球员表现 - 主队】")
    for player in game['homeTeam']['players']:
        if player['played'] == '1':
            stats = player['statistics']
            if stats.get('points', 0) >= 10:  # 得分10+
                print(f"{player['name']:20} {stats['points']}分/{stats['reboundsTotal']}板/{stats['assists']}助")

    # 4. 关键时刻
    print("\n【关键时刻】")
    pbp = playbyplay.PlayByPlay(game_id=game_id)
    actions = pbp.get_dict()['game']['actions']

    # 第四节最后2分钟
    clutch_actions = [a for a in actions
                     if a.get('period') == 4 and a.get('clock', '')  and
                     a['clock'] <= 'PT02M00.00S']

    for action in clutch_actions[-10:]:  # 最后10个事件
        if action.get('description'):
            print(f"[{action['clock']}] {action['description']}")

full_game_analysis('0022300500')
```

### 3. 获取特定球队今日比赛

```python
from nba_api.live.nba.endpoints import scoreboard

def get_team_game_today(team_tricode):
    """
    获取特定球队今日比赛

    Args:
        team_tricode: 球队三字母缩写（如 'GSW', 'LAL'）

    Returns:
        game_id 或 None
    """
    board = scoreboard.ScoreBoard()
    games = board.get_dict()['scoreboard']['games']

    for game in games:
        if (game['homeTeam']['teamTricode'] == team_tricode or
            game['awayTeam']['teamTricode'] == team_tricode):

            print(f"找到比赛:")
            print(f"  {game['awayTeam']['teamTricode']} @ {game['homeTeam']['teamTricode']}")
            print(f"  状态: {game['gameStatusText']}")
            print(f"  比分: {game['awayTeam']['score']} - {game['homeTeam']['score']}")

            return game['gameId']

    print(f"{team_tricode} 今日没有比赛")
    return None

# 使用示例
game_id = get_team_game_today('GSW')
if game_id:
    print(f"比赛ID: {game_id}")
```

### 4. 从ScoreBoard到详细数据

```python
from nba_api.live.nba.endpoints import scoreboard, boxscore

def get_all_games_details():
    """获取今日所有比赛的详细数据"""

    # 1. 获取今日比赛列表
    board = scoreboard.ScoreBoard()
    games = board.get_dict()['scoreboard']['games']

    print(f"今日共有 {len(games)} 场比赛\n")

    # 2. 遍历获取每场比赛详情
    for game in games:
        game_id = game['gameId']
        print(f"\n{'='*60}")
        print(f"比赛ID: {game_id}")

        try:
            # 获取BoxScore
            box = boxscore.BoxScore(game_id=game_id)
            game_data = box.get_dict()['game']

            # 打印比赛信息
            print(f"对阵: {game_data['awayTeam']['teamName']} @ {game_data['homeTeam']['teamName']}")
            print(f"场馆: {game_data['arena']['arenaName']}")

            # 打印双方最佳球员
            for team_key in ['awayTeam', 'homeTeam']:
                team = game_data[team_key]
                players = [p for p in team['players'] if p['played'] == '1']

                if players:
                    # 按得分排序
                    top_scorer = max(players, key=lambda p: p['statistics'].get('points', 0))
                    stats = top_scorer['statistics']

                    print(f"{team['teamTricode']} 最佳: {top_scorer['name']} "
                          f"- {stats['points']}分/{stats['reboundsTotal']}板/{stats['assists']}助")

        except Exception as e:
            print(f"获取详情失败: {e}")

# get_all_games_details()
```

---

## 注意事项

1. **数据延迟**：Live API 通常有 10-30 秒的延迟
2. **比赛时间**：ScoreBoard 基于 NBA 总部时区（美国东部时间）
3. **Game ID 格式**：必须是 10 位数字字符串
4. **数据可用性**：
   - 比赛开始前：基本信息可用，统计数据为空
   - 比赛进行中：数据实时更新
   - 比赛结束后：数据继续可用，但建议用 Stats API 获取完整数据
5. **请求频率**：
   - ScoreBoard：建议 10-30 秒更新一次
   - BoxScore/PlayByPlay：建议 5-15 秒更新一次
6. **错误处理**：比赛未开始或 Game ID 无效时可能返回错误
7. **JSON 格式**：Live API 只支持 JSON 格式，无 DataFrame 转换

---

## 最佳实践

### 1. 轮询策略

```python
import time

class GameMonitor:
    def __init__(self, game_id, update_interval=10):
        self.game_id = game_id
        self.update_interval = update_interval
        self.running = False

    def start(self):
        """开始监控"""
        self.running = True
        while self.running:
            try:
                self.update()
                time.sleep(self.update_interval)
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                print(f"Error: {e}")

    def update(self):
        """更新数据"""
        from nba_api.live.nba.endpoints import boxscore

        box = boxscore.BoxScore(game_id=self.game_id)
        game = box.get_dict()['game']

        # 处理数据...
        self.display(game)

    def display(self, game):
        """显示数据"""
        home = game['homeTeam']
        away = game['awayTeam']
        print(f"{away['teamTricode']} {away['score']} @ "
              f"{home['teamTricode']} {home['score']}")

    def stop(self):
        """停止监控"""
        self.running = False
        print("Monitor stopped")

# 使用
# monitor = GameMonitor('0022300500', update_interval=15)
# monitor.start()
```

### 2. 数据缓存

```python
import json
import time
from pathlib import Path

class LiveDataCache:
    def __init__(self, cache_dir='./cache', ttl=10):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl  # 缓存有效期（秒）

    def get(self, key, fetch_func):
        """获取数据（带缓存）"""
        cache_file = self.cache_dir / f"{key}.json"

        # 检查缓存
        if cache_file.exists():
            cache_time = cache_file.stat().st_mtime
            if time.time() - cache_time < self.ttl:
                with open(cache_file, 'r') as f:
                    return json.load(f)

        # 缓存过期或不存在，重新获取
        data = fetch_func()

        # 保存缓存
        with open(cache_file, 'w') as f:
            json.dump(data, f)

        return data

# 使用示例
cache = LiveDataCache(ttl=15)

def fetch_scoreboard():
    from nba_api.live.nba.endpoints import scoreboard
    board = scoreboard.ScoreBoard()
    return board.get_dict()

# 第一次调用会请求API
data1 = cache.get('scoreboard', fetch_scoreboard)

# 15秒内的调用会使用缓存
data2 = cache.get('scoreboard', fetch_scoreboard)
```

---

## 相关资源

- [总览文档](./NBA_API_OVERVIEW.md)
- [静态数据模块](./API_STATIC_DATA.md)
- [比赛数据接口](./API_GAME_DATA.md) - Stats API 的比赛数据（用于历史分析）
- [球员统计接口](./API_PLAYER_STATS.md)
- [球队统计接口](./API_TEAM_STATS.md)

**GitHub 文档：**
- [Live API ScoreBoard](https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/scoreboard.md)
- [Live API BoxScore](https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/boxscore.md)
- [Live API PlayByPlay](https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/playbyplay.md)

---

**提示**：Live API 适合实时追踪和比分更新，如需深度分析和历史数据，请使用 Stats API。
