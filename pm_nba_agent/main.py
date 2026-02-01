"""主流程：从 Polymarket URL 获取 NBA 比赛数据"""

import json
import sys
from typing import Optional

from loguru import logger

from .parsers import parse_polymarket_url
from .nba import get_team_info, find_game_by_teams_and_date, get_live_game_data
from .models import GameData
from .logging_config import configure_logging


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
        logger.info("解析 URL: {}", url)

    event_info = parse_polymarket_url(url)
    if not event_info:
        logger.error("URL 解析失败")
        return None

    if verbose:
        logger.info(
            "解析成功: {} vs {}, 日期: {}",
            event_info.team1_abbr,
            event_info.team2_abbr,
            event_info.game_date,
        )

    # 步骤 2: 获取球队详细信息
    if verbose:
        logger.info("获取球队信息...")

    team1 = get_team_info(event_info.team1_abbr)
    team2 = get_team_info(event_info.team2_abbr)

    if not team1:
        logger.error("找不到球队: {}", event_info.team1_abbr)
        return None
    if not team2:
        logger.error("找不到球队: {}", event_info.team2_abbr)
        return None

    if verbose:
        logger.info("{} ({})", team1.full_name, team1.abbreviation)
        logger.info("{} ({})", team2.full_name, team2.abbreviation)

    # 步骤 3: 查找比赛
    if verbose:
        logger.info("查找比赛 (日期: {})...", event_info.game_date)

    game_id = find_game_by_teams_and_date(
        event_info.team1_abbr,
        event_info.team2_abbr,
        event_info.game_date
    )

    if not game_id:
        logger.error("找不到比赛")
        return None

    if verbose:
        logger.info("找到比赛 ID: {}", game_id)

    # 步骤 4: 获取比赛详细数据
    if verbose:
        logger.info("获取比赛数据...")

    game_data = get_live_game_data(game_id)

    if not game_data:
        logger.error("获取比赛数据失败")
        return None

    if verbose:
        logger.info("数据获取成功")
        logger.info("比赛状态: {}", game_data.game_info.status)
        logger.info("{}: {}", game_data.away_team.name, game_data.away_team.score)
        logger.info("{}: {}", game_data.home_team.name, game_data.home_team.score)

    return game_data


def main(url: Optional[str] = None):
    """主函数示例"""
    # 示例 URL
    test_url = url or "https://polymarket.com/event/nba-orl-cle-2026-01-26"

    logger.info("{}", "=" * 60)
    logger.info("Polymarket NBA 事件数据获取工具")
    logger.info("{}", "=" * 60)

    game_data = get_game_data_from_url(test_url, verbose=True)

    if game_data:
        logger.info("{}", "=" * 60)
        logger.info("完整数据 (JSON 格式)")
        logger.info("{}", "=" * 60)
        logger.info(json.dumps(game_data.to_dict(), indent=2, ensure_ascii=False))

        # 显示在场球员
        logger.info("{}", "=" * 60)
        logger.info("在场球员")
        logger.info("{}", "=" * 60)
        on_court_players = [p for p in game_data.players if p.on_court]
        for player in on_court_players:
            logger.info(
                "{} ({}) - {}分 {}篮板 {}助攻",
                player.name,
                player.team,
                player.stats["points"],
                player.stats["rebounds"],
                player.stats["assists"],
            )


if __name__ == "__main__":
    cli_url = sys.argv[1] if len(sys.argv) > 1 else None
    configure_logging()
    main(cli_url)
