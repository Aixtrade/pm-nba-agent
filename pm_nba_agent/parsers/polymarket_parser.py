"""Polymarket URL 解析器"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PolymarketEventInfo:
    """Polymarket 事件信息"""
    team1_abbr: str
    team2_abbr: str
    game_date: str
    url: str


def parse_polymarket_url(url: str) -> Optional[PolymarketEventInfo]:
    """
    从 Polymarket URL 提取比赛信息

    Args:
        url: Polymarket 事件 URL，格式如 https://polymarket.com/event/nba-orl-cle-2026-01-26

    Returns:
        PolymarketEventInfo 对象，如果解析失败返回 None

    Examples:
        >>> info = parse_polymarket_url('https://polymarket.com/event/nba-orl-cle-2026-01-26')
        >>> info.team1_abbr
        'ORL'
        >>> info.team2_abbr
        'CLE'
        >>> info.game_date
        '2026-01-26'
    """
    # 正则提取: nba-{team1}-{team2}-{date}
    pattern = r'/event/nba-([a-z]+)-([a-z]+)-(\d{4}-\d{2}-\d{2})'
    match = re.search(pattern, url.lower())

    if not match:
        return None

    team1_abbr = match.group(1).upper()
    team2_abbr = match.group(2).upper()
    game_date = match.group(3)

    return PolymarketEventInfo(
        team1_abbr=team1_abbr,
        team2_abbr=team2_abbr,
        game_date=game_date,
        url=url
    )


def validate_team_abbreviation(abbr: str) -> bool:
    """
    验证球队缩写格式

    Args:
        abbr: 球队缩写，如 'ORL'

    Returns:
        True 如果格式有效
    """
    return bool(re.match(r'^[A-Z]{2,3}$', abbr))
