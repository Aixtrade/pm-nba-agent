"""主流程：从 Polymarket URL 获取 NBA 比赛数据"""

import json
from typing import Optional

from .parsers import parse_polymarket_url
from .nba import get_team_info, find_game_by_teams_and_date, get_live_game_data
from .models import GameData


def get_game_data_from_url(url: str, verbose: bool = True) -> Optional[GameData]:
    """
    从 Polymarket URL 获取 NBA 比赛完整数据

    Args:
        url: Polymarket 事件 URL
        verbose: 是否打印详细日志

    Returns:
        GameData 对象，失败返回 None

    Examples:
        >>> url = 'https://polymarket.com/event/nba-orl-cle-2026-01-26'
        >>> game_data = get_game_data_from_url(url)
        >>> print(f"{game_data.away_team.name} vs {game_data.home_team.name}")
        Orlando Magic vs Cleveland Cavaliers
    """
    # 步骤 1: 解析 URL
    if verbose:
        print(f"解析 URL: {url}")

    event_info = parse_polymarket_url(url)
    if not event_info:
        print("❌ URL 解析失败")
        return None

    if verbose:
        print(f"✓ 解析成功: {event_info.team1_abbr} vs {event_info.team2_abbr}, 日期: {event_info.game_date}")

    # 步骤 2: 获取球队详细信息
    if verbose:
        print(f"\n获取球队信息...")

    team1 = get_team_info(event_info.team1_abbr)
    team2 = get_team_info(event_info.team2_abbr)

    if not team1:
        print(f"❌ 找不到球队: {event_info.team1_abbr}")
        return None
    if not team2:
        print(f"❌ 找不到球队: {event_info.team2_abbr}")
        return None

    if verbose:
        print(f"✓ {team1.full_name} ({team1.abbreviation})")
        print(f"✓ {team2.full_name} ({team2.abbreviation})")

    # 步骤 3: 查找比赛
    if verbose:
        print(f"\n查找比赛 (日期: {event_info.game_date})...")

    game_id = find_game_by_teams_and_date(
        event_info.team1_abbr,
        event_info.team2_abbr,
        event_info.game_date
    )

    if not game_id:
        print(f"❌ 找不到比赛")
        return None

    if verbose:
        print(f"✓ 找到比赛 ID: {game_id}")

    # 步骤 4: 获取比赛详细数据
    if verbose:
        print(f"\n获取比赛数据...")

    game_data = get_live_game_data(game_id)

    if not game_data:
        print(f"❌ 获取比赛数据失败")
        return None

    if verbose:
        print(f"✓ 数据获取成功")
        print(f"\n比赛状态: {game_data.game_info.status}")
        print(f"{game_data.away_team.name}: {game_data.away_team.score}")
        print(f"{game_data.home_team.name}: {game_data.home_team.score}")

    return game_data


def main():
    """主函数示例"""
    # 示例 URL
    test_url = "https://polymarket.com/event/nba-orl-cle-2026-01-26"

    print("=" * 60)
    print("Polymarket NBA 事件数据获取工具")
    print("=" * 60)
    print()

    game_data = get_game_data_from_url(test_url, verbose=True)

    if game_data:
        print("\n" + "=" * 60)
        print("完整数据 (JSON 格式)")
        print("=" * 60)
        print(json.dumps(game_data.to_dict(), indent=2, ensure_ascii=False))

        # 显示在场球员
        print("\n" + "=" * 60)
        print("在场球员")
        print("=" * 60)
        on_court_players = [p for p in game_data.players if p.on_court]
        for player in on_court_players:
            print(f"{player.name} ({player.team}) - {player.stats['points']}分 "
                  f"{player.stats['rebounds']}篮板 {player.stats['assists']}助攻")


if __name__ == '__main__':
    main()
