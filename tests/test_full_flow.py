"""测试完整流程：从 Polymarket URL 获取比赛数据"""

from pm_nba_agent.main import get_game_data_from_url
import json

# 真实的比赛 URL
url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"

print("=" * 60)
print("测试完整流程")
print("=" * 60)
print()

game_data = get_game_data_from_url(url, verbose=True)

if game_data:
    print("\n" + "=" * 60)
    print("比赛详细信息")
    print("=" * 60)

    data_dict = game_data.to_dict()

    # 显示比赛状态
    print(f"\n比赛 ID: {data_dict['game_info']['game_id']}")
    print(f"状态: {data_dict['game_info']['status']}")
    print(f"节数: Q{data_dict['game_info']['period']}")
    print(f"时钟: {data_dict['game_info']['game_clock']}")

    # 显示比分
    print(f"\n{data_dict['teams']['away']['name']}: {data_dict['teams']['away']['score']}")
    print(f"{data_dict['teams']['home']['name']}: {data_dict['teams']['home']['score']}")

    # 显示球队统计
    print(f"\n球队统计:")
    for team_type in ['home', 'away']:
        team = data_dict['teams'][team_type]
        print(f"\n{team['name']}:")
        print(f"  篮板: {team['statistics']['rebounds']}")
        print(f"  助攻: {team['statistics']['assists']}")
        print(f"  投篮命中率: {team['statistics']['field_goal_pct']:.1%}")
        print(f"  三分命中率: {team['statistics']['three_point_pct']:.1%}")

    # 显示得分前5的球员
    print(f"\n得分榜 (前10):")
    players_sorted = sorted(data_dict['players'], key=lambda x: x['stats']['points'], reverse=True)
    for i, player in enumerate(players_sorted[:10], 1):
        print(f"{i}. {player['name']} ({player['team']}) - "
              f"{player['stats']['points']}分 "
              f"{player['stats']['rebounds']}篮板 "
              f"{player['stats']['assists']}助攻 "
              f"[{'在场' if player['on_court'] else '替补'}]")

    # 输出完整 JSON
    print("\n" + "=" * 60)
    print("完整数据 (JSON)")
    print("=" * 60)
    print(json.dumps(data_dict, indent=2, ensure_ascii=False))
else:
    print("\n❌ 获取数据失败")
