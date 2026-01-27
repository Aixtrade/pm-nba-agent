"""NBA 球队信息解析"""

from dataclasses import dataclass
from typing import Optional
from nba_api.stats.static import teams


@dataclass
class TeamInfo:
    """球队信息"""
    id: int
    full_name: str
    abbreviation: str
    nickname: str
    city: str
    state: str
    year_founded: int


def get_team_info(abbreviation: str) -> Optional[TeamInfo]:
    """
    通过球队缩写获取详细信息

    Args:
        abbreviation: 球队缩写，如 'ORL', 'CLE'

    Returns:
        TeamInfo 对象，如果找不到返回 None

    Examples:
        >>> team = get_team_info('ORL')
        >>> team.full_name
        'Orlando Magic'
        >>> team.nickname
        'Magic'
    """
    team_data = teams.find_team_by_abbreviation(abbreviation)

    if not team_data:
        return None

    return TeamInfo(
        id=team_data['id'],
        full_name=team_data['full_name'],
        abbreviation=team_data['abbreviation'],
        nickname=team_data['nickname'],
        city=team_data['city'],
        state=team_data['state'],
        year_founded=team_data['year_founded']
    )


def get_all_teams() -> list[TeamInfo]:
    """
    获取所有 NBA 球队信息

    Returns:
        TeamInfo 对象列表
    """
    all_teams = teams.get_teams()
    return [
        TeamInfo(
            id=team['id'],
            full_name=team['full_name'],
            abbreviation=team['abbreviation'],
            nickname=team['nickname'],
            city=team['city'],
            state=team['state'],
            year_founded=team['year_founded']
        )
        for team in all_teams
    ]
