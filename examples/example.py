"""使用示例"""

from pm_nba_agent.main import get_game_data_from_url

# Polymarket 比赛 URL
url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"

# 获取比赛数据
game_data = get_game_data_from_url(url, verbose=False)

if game_data:
    # 显示比赛概况
    print(f"🏀 {game_data.away_team.name} @ {game_data.home_team.name}")
    print(f"📊 比分: {game_data.away_team.score} - {game_data.home_team.score}")
    print(f"⏰ 状态: {game_data.game_info.status}")
    print()

    # 显示得分领先者
    top_scorers = sorted(game_data.players, key=lambda x: x.stats['points'], reverse=True)[:3]
    print("🏆 得分榜:")
    for i, player in enumerate(top_scorers, 1):
        print(f"  {i}. {player.name} ({player.team}) - {player.stats['points']}分")
    print()

    # 转换为字典（可用于 API 返回或存储）
    data_dict = game_data.to_dict()
    print(f"✅ 数据包含 {len(data_dict['players'])} 名球员的详细统计")
