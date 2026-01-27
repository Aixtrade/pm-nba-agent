"""测试今天的比赛"""

from pm_nba_agent.nba.game_finder import get_todays_games
import json

print("查询今天的 NBA 比赛...")
print("=" * 60)

games = get_todays_games()

if games:
    print(f"找到 {len(games)} 场比赛:\n")
    for i, game in enumerate(games, 1):
        print(f"{i}. {game['away_team']} @ {game['home_team']}")
        print(f"   Game ID: {game['game_id']}")
        print(f"   状态: {game['status']}")
        print(f"   比分: {game['away_score']} - {game['home_score']}")
        print()
else:
    print("今天没有比赛")

print("\n" + "=" * 60)
print("完整数据:")
print(json.dumps(games, indent=2, ensure_ascii=False))
