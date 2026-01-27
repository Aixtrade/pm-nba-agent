"""基础使用示例"""

from pm_nba_agent.parsers import parse_polymarket_url
from pm_nba_agent.nba import get_team_info, find_game_by_teams_and_date, get_live_game_data

# URL 解析
url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"
print("=" * 60)
print("1. URL 解析")
print("=" * 60)
event_info = parse_polymarket_url(url)
print(f"球队1: {event_info.team1_abbr}")
print(f"球队2: {event_info.team2_abbr}")
print(f"日期: {event_info.game_date}")
print()

# 获取球队信息
print("=" * 60)
print("2. 球队信息查询")
print("=" * 60)
team1 = get_team_info(event_info.team1_abbr)
team2 = get_team_info(event_info.team2_abbr)
print(f"{team1.full_name} ({team1.city}, {team1.state})")
print(f"  成立年份: {team1.year_founded}")
print(f"{team2.full_name} ({team2.city}, {team2.state})")
print(f"  成立年份: {team2.year_founded}")
print()

# 查找比赛
print("=" * 60)
print("3. 查找比赛")
print("=" * 60)
game_id = find_game_by_teams_and_date(
    event_info.team1_abbr,
    event_info.team2_abbr,
    event_info.game_date
)
if game_id:
    print(f"✓ 找到比赛: {game_id}")
else:
    print("✗ 未找到比赛")
    exit(1)
print()

# 获取比赛数据
print("=" * 60)
print("4. 获取比赛数据")
print("=" * 60)
game_data = get_live_game_data(game_id)
if game_data:
    print(f"状态: {game_data.game_info.status}")
    print(f"节数: Q{game_data.game_info.period}")
    print(f"\n{game_data.away_team.name}: {game_data.away_team.score}")
    print(f"{game_data.home_team.name}: {game_data.home_team.score}")

    # 球员统计
    print(f"\n上场球员数量: {sum(1 for p in game_data.players if p.on_court)}")
    print(f"总球员数量: {len(game_data.players)}")
else:
    print("✗ 获取数据失败")
