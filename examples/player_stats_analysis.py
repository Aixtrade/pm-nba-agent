"""球员数据分析示例"""

from pm_nba_agent.main import get_game_data_from_url

url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"

print("=" * 60)
print("球员数据分析示例")
print("=" * 60)
print()

game_data = get_game_data_from_url(url, verbose=False)

if not game_data:
    print("❌ 无法获取比赛数据")
    exit(1)

print(f"比赛: {game_data.away_team.name} @ {game_data.home_team.name}")
print(f"状态: {game_data.game_info.status}")
print()

# 得分排行榜
print("=" * 60)
print("🏆 得分榜")
print("=" * 60)
sorted_by_points = sorted(game_data.players, key=lambda x: x.stats['points'], reverse=True)
for i, player in enumerate(sorted_by_points[:10], 1):
    status = "🟢" if player.on_court else "⚪"
    print(f"{i:2d}. {status} {player.name:20s} ({player.team}) - {player.stats['points']:2d}分")
print()

# 篮板排行榜
print("=" * 60)
print("🏀 篮板榜")
print("=" * 60)
sorted_by_rebounds = sorted(game_data.players, key=lambda x: x.stats['rebounds'], reverse=True)
for i, player in enumerate(sorted_by_rebounds[:5], 1):
    print(f"{i}. {player.name:20s} ({player.team}) - {player.stats['rebounds']:2d}篮板")
print()

# 助攻排行榜
print("=" * 60)
print("🤝 助攻榜")
print("=" * 60)
sorted_by_assists = sorted(game_data.players, key=lambda x: x.stats['assists'], reverse=True)
for i, player in enumerate(sorted_by_assists[:5], 1):
    print(f"{i}. {player.name:20s} ({player.team}) - {player.stats['assists']:2d}助攻")
print()

# 效率值分析（简单版：得分 + 篮板 + 助攻）
print("=" * 60)
print("📊 效率值排行 (得分+篮板+助攻)")
print("=" * 60)
for player in game_data.players:
    player.efficiency = (
        player.stats['points'] +
        player.stats['rebounds'] +
        player.stats['assists']
    )

sorted_by_efficiency = sorted(game_data.players, key=lambda x: x.efficiency, reverse=True)
for i, player in enumerate(sorted_by_efficiency[:5], 1):
    print(f"{i}. {player.name:20s} ({player.team}) - {player.efficiency:2d} "
          f"({player.stats['points']}分+{player.stats['rebounds']}板+{player.stats['assists']}助)")
print()

# 投篮命中率分析（至少5次出手）
print("=" * 60)
print("🎯 投篮命中率 (至少5次出手)")
print("=" * 60)
shooters = [
    p for p in game_data.players
    if p.stats['field_goals_attempted'] >= 5
]
for player in shooters:
    fga = player.stats['field_goals_attempted']
    fgm = player.stats['field_goals_made']
    fg_pct = (fgm / fga * 100) if fga > 0 else 0
    player.fg_pct = fg_pct

sorted_by_fg = sorted(shooters, key=lambda x: x.fg_pct, reverse=True)
for i, player in enumerate(sorted_by_fg[:5], 1):
    print(f"{i}. {player.name:20s} ({player.team}) - "
          f"{player.fg_pct:.1f}% ({player.stats['field_goals_made']}/{player.stats['field_goals_attempted']})")
print()

# 当前在场球员
print("=" * 60)
print("🟢 当前在场球员")
print("=" * 60)
on_court = [p for p in game_data.players if p.on_court]
for team in [game_data.home_team.abbreviation, game_data.away_team.abbreviation]:
    team_players = [p for p in on_court if p.team == team]
    team_name = game_data.home_team.name if team == game_data.home_team.abbreviation else game_data.away_team.name
    print(f"\n{team_name}:")
    for player in team_players:
        print(f"  {player.name} ({player.position or 'N/A'}) - "
              f"{player.stats['points']}分 {player.stats['rebounds']}板 {player.stats['assists']}助")
