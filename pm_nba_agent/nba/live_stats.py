"""NBA 实时比赛数据获取"""

from typing import Optional
from nba_api.live.nba.endpoints import boxscore
import time

from ..models.game_data import GameData, GameInfo, TeamStats, PlayerStats


def get_live_game_data(game_id: str) -> Optional[GameData]:
    """
    获取比赛详细数据

    Args:
        game_id: 比赛 ID，如 '0022600123'

    Returns:
        GameData 对象，如果获取失败返回 None

    Examples:
        >>> game_data = get_live_game_data('0022600123')
        >>> game_data.game_info.status
        'Live - Q3'
        >>> game_data.home_team.score
        89
    """
    time.sleep(0.6)  # API 限流控制

    try:
        game = boxscore.BoxScore(game_id=game_id)
        box_dict = game.get_dict()

        # 解析比赛基本信息
        game_data = box_dict['game']

        # 构建比赛状态文本
        status_code = game_data['gameStatus']
        status_text = _get_status_text(status_code, game_data)

        game_info = GameInfo(
            game_id=game_data['gameId'],
            game_date=game_data['gameTimeUTC'][:10],  # 提取日期部分
            status=status_text,
            period=game_data.get('period', 0),
            game_clock=game_data.get('gameClock', ''),
            game_status_code=status_code
        )

        # 解析主队数据
        home_team_data = game_data['homeTeam']
        home_team = TeamStats.from_live_api(home_team_data)

        # 解析客队数据
        away_team_data = game_data['awayTeam']
        away_team = TeamStats.from_live_api(away_team_data)

        # 解析球员数据
        players = []

        # 主队球员
        for player_data in home_team_data.get('players', []):
            if player_data.get('played') == '1':  # 只包含上场球员
                player = PlayerStats.from_live_api(player_data, home_team.abbreviation)
                players.append(player)

        # 客队球员
        for player_data in away_team_data.get('players', []):
            if player_data.get('played') == '1':
                player = PlayerStats.from_live_api(player_data, away_team.abbreviation)
                players.append(player)

        return GameData(
            game_info=game_info,
            home_team=home_team,
            away_team=away_team,
            players=players
        )

    except Exception as e:
        print(f"获取比赛数据失败: {e}")
        return None


def _get_status_text(status_code: int, game_data: dict) -> str:
    """
    根据状态码生成状态文本

    Args:
        status_code: 1=未开始, 2=进行中, 3=已结束
        game_data: 比赛数据字典

    Returns:
        状态文本，如 'Live - Q3', 'Final', 'Scheduled'
    """
    if status_code == 1:
        return 'Scheduled'
    elif status_code == 2:
        period = game_data.get('period', 0)
        if period <= 4:
            return f'Live - Q{period}'
        else:
            ot_num = period - 4
            return f'Live - OT{ot_num}'
    elif status_code == 3:
        return 'Final'
    else:
        return 'Unknown'


def get_game_summary(game_id: str) -> Optional[dict]:
    """
    获取比赛简要信息（不包含球员详细数据）

    Args:
        game_id: 比赛 ID

    Returns:
        包含基本信息和比分的字典
    """
    time.sleep(0.6)

    try:
        game = boxscore.BoxScore(game_id=game_id)
        box_dict = game.get_dict()
        game_data = box_dict['game']

        status_code = game_data['gameStatus']
        status_text = _get_status_text(status_code, game_data)

        return {
            'game_id': game_data['gameId'],
            'status': status_text,
            'period': game_data.get('period', 0),
            'game_clock': game_data.get('gameClock', ''),
            'home_team': {
                'name': game_data['homeTeam']['teamName'],
                'abbreviation': game_data['homeTeam']['teamTricode'],
                'score': game_data['homeTeam']['score'],
            },
            'away_team': {
                'name': game_data['awayTeam']['teamName'],
                'abbreviation': game_data['awayTeam']['teamTricode'],
                'score': game_data['awayTeam']['score'],
            }
        }
    except Exception as e:
        print(f"获取比赛摘要失败: {e}")
        return None
