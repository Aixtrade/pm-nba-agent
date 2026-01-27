"""高级使用示例：批量查询和数据分析"""

from pm_nba_agent.nba.game_finder import get_todays_games
from pm_nba_agent.nba.live_stats import get_game_summary
import time

print("=" * 60)
print("高级示例：批量查询今天的所有比赛")
print("=" * 60)
print()

# 获取今天所有比赛
games = get_todays_games()
print(f"今天共有 {len(games)} 场比赛\n")

# 分类统计
live_games = [g for g in games if 'Q' in g['status'] or 'OT' in g['status']]
finished_games = [g for g in games if g['status'] == 'Final']
upcoming_games = [g for g in games if 'pm' in g['status'] or 'am' in g['status']]

print(f"📊 比赛状态统计:")
print(f"  进行中: {len(live_games)} 场")
print(f"  已结束: {len(finished_games)} 场")
print(f"  未开始: {len(upcoming_games)} 场")
print()

# 显示正在进行的比赛详情
if live_games:
    print("=" * 60)
    print("🏀 正在进行的比赛")
    print("=" * 60)
    for game in live_games:
        print(f"\n{game['away_team']} @ {game['home_team']}")
        print(f"  状态: {game['status']}")
        print(f"  比分: {game['away_score']} - {game['home_score']}")

        # 计算分差
        diff = abs(game['home_score'] - game['away_score'])
        leader = game['home_team'] if game['home_score'] > game['away_score'] else game['away_team']
        print(f"  领先: {leader} +{diff}")

        time.sleep(0.6)  # API 限流

# 显示已结束的比赛
if finished_games:
    print("\n" + "=" * 60)
    print("✅ 已结束的比赛")
    print("=" * 60)
    for game in finished_games:
        winner = game['home_team'] if game['home_score'] > game['away_score'] else game['away_team']
        winner_score = max(game['home_score'], game['away_score'])
        loser_score = min(game['home_score'], game['away_score'])

        print(f"\n{game['away_team']} @ {game['home_team']}")
        print(f"  最终比分: {game['away_score']} - {game['home_score']}")
        print(f"  胜者: {winner} ({winner_score}-{loser_score})")

# 显示未开始的比赛
if upcoming_games:
    print("\n" + "=" * 60)
    print("⏰ 即将开始的比赛")
    print("=" * 60)
    for game in upcoming_games:
        print(f"\n{game['away_team']} @ {game['home_team']}")
        print(f"  开始时间: {game['status']}")

# 统计分析
print("\n" + "=" * 60)
print("📈 得分统计")
print("=" * 60)
all_scores = [g['home_score'] + g['away_score'] for g in games if g['status'] == 'Final']
if all_scores:
    avg_total = sum(all_scores) / len(all_scores)
    print(f"已结束比赛平均总分: {avg_total:.1f}")
    print(f"最高总分: {max(all_scores)}")
    print(f"最低总分: {min(all_scores)}")
