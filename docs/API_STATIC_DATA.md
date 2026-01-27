# NBA API - 静态数据模块文档

> 本文档整理自 [nba_api](https://github.com/swar/nba_api) 项目
> 最后更新时间：2026-01-27

## 目录

- [概述](#概述)
- [Teams 模块（球队数据）](#teams-模块球队数据)
- [Players 模块（球员数据）](#players-模块球员数据)
- [实用示例](#实用示例)
- [核心技术特性](#核心技术特性)

---

## 概述

`nba_api` 的静态数据模块提供了访问 NBA 和 WNBA 球队及球员信息的功能，**无需发送 HTTP 请求**。这些模块包含了预加载的数据，可以快速查询球队和球员的基本信息。

**模块位置：**
- `nba_api.stats.static.teams` - 球队数据模块
- `nba_api.stats.static.players` - 球员数据模块

**核心优势：**
- ✅ 无需网络请求，查询速度极快
- ✅ 支持灵活的正则表达式搜索
- ✅ 支持音标符号处理（如 "Dončić"）
- ✅ 提供丰富的过滤和查询函数
- ✅ 同时支持 NBA 和 WNBA 数据

---

## Teams 模块（球队数据）

### 模块导入

```python
from nba_api.stats.static import teams
```

### 返回数据结构

所有球队函数返回的字典包含以下字段：

```python
{
    'id': int,              # 球队 ID
    'full_name': str,       # 球队全名（如 "Los Angeles Lakers"）
    'abbreviation': str,    # 球队缩写（如 "LAL"）
    'nickname': str,        # 球队昵称（如 "Lakers"）
    'city': str,           # 所在城市（如 "Los Angeles"）
    'state': str,          # 所在州（如 "California"）
    'year_founded': int    # 成立年份
}
```

---

### NBA 球队函数

#### 1. `get_teams()`

获取所有 NBA 球队列表

```python
# 函数签名
get_teams() -> list

# 使用示例
all_teams = teams.get_teams()
print(f"共有 {len(all_teams)} 支 NBA 球队")
```

#### 2. `find_teams_by_full_name(regex_pattern)`

通过球队全名搜索球队（支持正则表达式）

**参数：**
- `regex_pattern` (str): 正则表达式模式，用于匹配球队全名（不区分大小写）

```python
# 查找包含 "Lakers" 的球队
lakers = teams.find_teams_by_full_name('Lakers')
# 返回: [{'id': 1610612747, 'full_name': 'Los Angeles Lakers', ...}]

# 查找洛杉矶的所有球队
la_teams = teams.find_teams_by_full_name('Los Angeles')
# 返回: Lakers 和 Clippers
```

#### 3. `find_teams_by_city(regex_pattern)`

通过城市名称搜索球队

```python
# 查找芝加哥的球队
chicago_teams = teams.find_teams_by_city('Chicago')
# 返回: [{'id': 1610612741, 'full_name': 'Chicago Bulls', ...}]
```

#### 4. `find_teams_by_state(regex_pattern)`

通过州名搜索球队

```python
# 查找加州的所有球队
california_teams = teams.find_teams_by_state('California')
# 返回: Lakers, Clippers, Warriors, Kings
```

#### 5. `find_teams_by_nickname(regex_pattern)`

通过球队昵称搜索球队

```python
# 查找昵称为 "Warriors" 的球队
warriors = teams.find_teams_by_nickname('Warriors')
# 返回: [{'id': 1610612744, 'nickname': 'Warriors', ...}]
```

#### 6. `find_teams_by_year_founded(year)`

查找在指定年份成立的球队

**参数：**
- `year` (int): 球队成立年份

```python
# 查找 1946 年成立的球队
teams_1946 = teams.find_teams_by_year_founded(1946)
```

#### 7. `find_teams_by_championship_year(year)`

查找在指定年份获得总冠军的球队

**参数：**
- `year` (int): 获得总冠军的年份

```python
# 查找 2020 年获得总冠军的球队
champs_2020 = teams.find_teams_by_championship_year(2020)
# 返回: [{'id': 1610612747, 'full_name': 'Los Angeles Lakers', ...}]
```

#### 8. `find_team_by_abbreviation(abbreviation)`

通过球队缩写查找单个球队

**参数：**
- `abbreviation` (str): 球队缩写（如 "GSW", "LAL"）

**返回值：** 单个球队字典，如果未找到则返回 `None`

```python
# 查找金州勇士队
warriors = teams.find_team_by_abbreviation('GSW')
# 返回: {'id': 1610612744, 'full_name': 'Golden State Warriors',
#        'abbreviation': 'GSW', 'nickname': 'Warriors',
#        'city': 'Golden State', 'state': 'California', 'year_founded': 1946}
```

#### 9. `find_team_name_by_id(team_id)`

通过球队 ID 获取球队名称

**参数：**
- `team_id` (int): 球队 ID

**返回值：** 球队全名字符串，如果未找到则返回 `None`

```python
# 通过 ID 查找球队名称
team_name = teams.find_team_name_by_id(1610612744)
# 返回: "Golden State Warriors"
```

---

### WNBA 球队函数

WNBA 球队模块提供了与 NBA 相同的函数，只是函数名前加了 `wnba_` 前缀：

| NBA 函数 | WNBA 函数 |
|---------|----------|
| `get_teams()` | `get_wnba_teams()` |
| `find_teams_by_full_name()` | `find_wnba_teams_by_full_name()` |
| `find_teams_by_city()` | `find_wnba_teams_by_city()` |
| `find_teams_by_state()` | `find_wnba_teams_by_state()` |
| `find_teams_by_nickname()` | `find_wnba_teams_by_nickname()` |
| `find_teams_by_year_founded()` | `find_wnba_teams_by_year_founded()` |
| `find_teams_by_championship_year()` | `find_wnba_teams_by_championship_year()` |
| `find_team_by_abbreviation()` | `find_wnba_team_by_abbreviation()` |
| `find_team_name_by_id()` | `find_wnba_team_name_by_id()` |

**使用示例：**

```python
from nba_api.stats.static import teams

# 获取所有 WNBA 球队
wnba_teams = teams.get_wnba_teams()

# 查找洛杉矶的 WNBA 球队
la_wnba = teams.find_wnba_teams_by_city('Los Angeles')
```

---

## Players 模块（球员数据）

### 模块导入

```python
from nba_api.stats.static import players
```

### 返回数据结构

所有球员函数返回的字典包含以下字段：

```python
{
    'id': int,              # 球员 ID
    'full_name': str,       # 球员全名（如 "LeBron James"）
    'first_name': str,      # 名字（如 "LeBron"）
    'last_name': str,       # 姓氏（如 "James"）
    'is_active': bool       # 是否现役（True/False）
}
```

---

### NBA 球员函数

#### 1. `get_players()`

获取所有 NBA 球员列表

```python
# 函数签名
get_players() -> list

# 使用示例
all_players = players.get_players()
print(f"数据库中共有 {len(all_players)} 名球员")
```

#### 2. `get_active_players()`

获取所有现役 NBA 球员

```python
# 获取所有现役球员
active_players = players.get_active_players()
print(f"现役球员数: {len(active_players)}")
```

#### 3. `get_inactive_players()`

获取所有非现役（退役）NBA 球员

```python
# 获取所有退役球员
inactive_players = players.get_inactive_players()
print(f"退役球员数: {len(inactive_players)}")
```

#### 4. `find_players_by_full_name(regex_pattern)`

通过球员全名搜索球员（支持正则表达式，不区分大小写，支持去除音标符号）

**参数：**
- `regex_pattern` (str): 正则表达式模式，用于匹配球员全名

```python
# 查找 LeBron James
lebron = players.find_players_by_full_name('LeBron James')
# 返回: [{'id': 2544, 'full_name': 'LeBron James',
#         'first_name': 'LeBron', 'last_name': 'James', 'is_active': True}]

# 使用部分匹配查找所有包含 "james" 的球员
james_players = players.find_players_by_full_name('james')
# 返回所有名字中包含 "james" 的球员
```

#### 5. `find_players_by_first_name(regex_pattern)`

通过球员名字搜索球员

```python
# 查找名字为 "LeBron" 的球员
lebron_players = players.find_players_by_first_name('LeBron')
```

#### 6. `find_players_by_last_name(regex_pattern)`

通过球员姓氏搜索球员

```python
# 查找姓氏为 "James" 或 "Love" 的球员
players_list = players.find_players_by_last_name('^(James|Love)$')
# 使用正则表达式精确匹配姓氏
```

#### 7. `find_player_by_id(player_id)`

通过球员 ID 查找单个球员

**参数：**
- `player_id` (int): 球员 ID

**返回值：** 单个球员字典，如果未找到则返回 `None`

**注意：** 如果发现多个相同 ID 的球员（异常情况），函数会抛出异常

```python
# 通过 ID 查找 LeBron James
lebron = players.find_player_by_id(2544)
# 返回: {'id': 2544, 'full_name': 'LeBron James',
#        'first_name': 'LeBron', 'last_name': 'James', 'is_active': True}
```

---

### WNBA 球员函数

WNBA 球员模块提供了与 NBA 相同的函数，只是函数名前加了 `wnba_` 前缀：

| NBA 函数 | WNBA 函数 |
|---------|----------|
| `get_players()` | `get_wnba_players()` |
| `get_active_players()` | `get_wnba_active_players()` |
| `get_inactive_players()` | `get_wnba_inactive_players()` |
| `find_players_by_full_name()` | `find_wnba_players_by_full_name()` |
| `find_players_by_first_name()` | `find_wnba_players_by_first_name()` |
| `find_players_by_last_name()` | `find_wnba_players_by_last_name()` |
| `find_player_by_id()` | `find_wnba_player_by_id()` |

**使用示例：**

```python
from nba_api.stats.static import players

# 获取所有 WNBA 球员
wnba_players = players.get_wnba_players()

# 查找现役 WNBA 球员
active_wnba = players.get_wnba_active_players()
```

---

## 实用示例

### 示例 1：获取球队 ID 用于 API 调用

```python
from nba_api.stats.static import teams

# 获取金州勇士队的 ID
warriors = teams.find_team_by_abbreviation('GSW')
warriors_id = warriors['id']  # 1610612744

# 使用球队 ID 调用其他 API
from nba_api.stats.endpoints import teamgamelog
game_log = teamgamelog.TeamGameLog(team_id=warriors_id, season='2023-24')
```

### 示例 2：获取球员 ID 用于 API 调用

```python
from nba_api.stats.static import players

# 获取 LeBron James 的 ID
lebron = players.find_players_by_full_name('LeBron James')[0]
lebron_id = lebron['id']  # 2544

# 使用球员 ID 调用其他 API
from nba_api.stats.endpoints import playergamelog
game_log = playergamelog.PlayerGameLog(player_id=lebron_id, season='2023-24')
```

### 示例 3：批量处理球员数据

```python
from nba_api.stats.static import players

# 获取所有现役球员
active_players = players.get_active_players()

# 遍历并提取球员 ID
player_ids = [player['id'] for player in active_players]

# 按姓氏排序
sorted_players = sorted(active_players, key=lambda x: x['last_name'])

# 输出前10名球员
for player in sorted_players[:10]:
    print(f"{player['full_name']} - ID: {player['id']}")
```

### 示例 4：搜索特定州的所有球队

```python
from nba_api.stats.static import teams

# 获取德克萨斯州的所有球队
texas_teams = teams.find_teams_by_state('Texas')

# 打印球队信息
for team in texas_teams:
    print(f"{team['full_name']} ({team['abbreviation']}) - ID: {team['id']}")
```

**输出：**
```
Dallas Mavericks (DAL) - ID: 1610612742
Houston Rockets (HOU) - ID: 1610612745
San Antonio Spurs (SAS) - ID: 1610612759
```

### 示例 5：使用正则表达式进行复杂搜索

```python
from nba_api.stats.static import players

# 查找所有姓氏以 "J" 开头的球员
j_players = players.find_players_by_last_name('^J')

# 查找名字中包含 "Chris" 或 "Christopher" 的球员
chris_players = players.find_players_by_first_name('Chris(topher)?')

# 查找姓氏为 "James" 的现役球员
james_active = [p for p in players.find_players_by_last_name('James')
                if p['is_active']]
```

---

## 核心技术特性

### 1. 正则表达式支持

所有搜索函数都支持 Python 正则表达式（`re` 模块），并且默认使用不区分大小写的匹配模式（`re.I` 标志）。

**常用正则表达式模式：**

| 模式 | 说明 | 示例 |
|------|------|------|
| `'^Lakers$'` | 精确匹配 | 只匹配 "Lakers" |
| `'Lakers\|Warriors'` | 匹配多个关键词 | 匹配包含 "Lakers" 或 "Warriors" 的内容 |
| `'^L'` | 匹配以 L 开头 | 匹配 "Lakers", "Love" 等 |
| `'s$'` | 匹配以 s 结尾 | 匹配 "Lakers", "Warriors" 等 |
| `'.*James.*'` | 包含 James | 匹配任何包含 "James" 的内容 |

### 2. 音标符号处理

`players` 模块包含 `_strip_accents()` 辅助函数，可以规范化并移除字符串中的音标符号，使搜索更加灵活。

**示例：**
```python
# 搜索 "Luka" 也能匹配 "Luka Dončić"
luka = players.find_players_by_full_name('Luka')
```

### 3. 数据结构

- **球队数据结构包含 7 个字段：** `id`, `full_name`, `abbreviation`, `nickname`, `city`, `state`, `year_founded`
- **球员数据结构包含 5 个字段：** `id`, `full_name`, `first_name`, `last_name`, `is_active`

### 4. 性能优势

静态模块使用预加载的数据，避免了网络请求，查询速度极快，适合：
- 频繁查询 ID 的场景
- 批量处理球员或球队数据
- 构建实时搜索功能
- 本地数据分析

---

## 常见问题

### Q1: 静态数据多久更新一次？

静态数据在 `nba_api` 包发布时更新，建议定期更新包以获取最新数据：

```bash
pip install --upgrade nba_api
```

### Q2: 如何区分现役和退役球员？

方法 1：使用 `is_active` 字段判断
```python
player = players.find_player_by_id(2544)
if player['is_active']:
    print("现役球员")
```

方法 2：直接使用专用函数
```python
active = players.get_active_players()
inactive = players.get_inactive_players()
```

### Q3: 返回值为 None 表示什么？

当使用单个查询函数（如 `find_team_by_abbreviation()` 或 `find_player_by_id()`）时，如果未找到匹配项，会返回 `None`。

```python
team = teams.find_team_by_abbreviation('XYZ')
if team is None:
    print("未找到该球队")
```

### Q4: 如何处理多个匹配结果？

大多数搜索函数返回列表，需要根据实际情况处理：

```python
# 查找所有包含 "Los Angeles" 的球队
la_teams = teams.find_teams_by_city('Los Angeles')

if len(la_teams) == 0:
    print("未找到球队")
elif len(la_teams) == 1:
    print(f"找到1支球队: {la_teams[0]['full_name']}")
else:
    print(f"找到{len(la_teams)}支球队:")
    for team in la_teams:
        print(f"  - {team['full_name']}")
```

---

## 适用场景

### 1. 获取 ID 用于 API 调用

这是静态模块最常见的使用场景：

```python
# 获取球员 ID
lebron = players.find_players_by_full_name('LeBron James')[0]
player_id = lebron['id']

# 使用 ID 调用 Stats API
from nba_api.stats.endpoints import playercareerstats
career = playercareerstats.PlayerCareerStats(player_id=player_id)
```

### 2. 构建球员/球队选择器

用于 Web 应用或桌面应用的下拉菜单：

```python
# 获取所有现役球员用于选择器
active = players.get_active_players()
player_options = [
    {'label': p['full_name'], 'value': p['id']}
    for p in sorted(active, key=lambda x: x['full_name'])
]
```

### 3. 数据分析和统计

进行批量数据处理和统计分析：

```python
# 统计各州的球队数量
from collections import Counter
all_teams = teams.get_teams()
state_counts = Counter(team['state'] for team in all_teams)
print(state_counts.most_common(5))
```

### 4. 实时搜索功能

实现无需网络请求的本地搜索：

```python
def search_player(query):
    """本地搜索球员"""
    results = players.find_players_by_full_name(query)
    return [
        {
            'id': p['id'],
            'name': p['full_name'],
            'status': '现役' if p['is_active'] else '退役'
        }
        for p in results
    ]
```

---

## 总结

`nba_api` 的静态数据模块是使用 NBA API 的基础工具，提供了快速、便捷的方式来查询球队和球员信息。

**主要优势：**
- ✅ 无需网络请求，查询速度快
- ✅ 支持灵活的正则表达式搜索
- ✅ 提供丰富的过滤和查询函数
- ✅ 数据结构清晰，易于使用
- ✅ 同时支持 NBA 和 WNBA

**最佳实践：**
1. 优先使用静态模块获取 ID，避免不必要的 API 调用
2. 使用正则表达式进行灵活搜索
3. 定期更新 `nba_api` 包以获取最新数据
4. 处理返回值时注意检查 `None` 和空列表

---

## 相关资源

- [总览文档](./NBA_API_OVERVIEW.md)
- [比赛数据接口](./API_GAME_DATA.md)
- [球员统计接口](./API_PLAYER_STATS.md)
- [球队统计接口](./API_TEAM_STATS.md)

**GitHub 资源：**
- [Teams 模块文档](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/static/teams.md)
- [Players 模块文档](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/static/players.md)
- [使用示例](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/examples.md)
