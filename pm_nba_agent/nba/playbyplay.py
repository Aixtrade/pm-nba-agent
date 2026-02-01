"""NBA 逐回合数据获取"""

from typing import Optional
import time

from loguru import logger
from nba_api.live.nba.endpoints import playbyplay


def get_playbyplay_data(game_id: str, limit: int = 20) -> Optional[list[dict]]:
    """
    获取比赛逐回合数据

    Args:
        game_id: 比赛 ID，如 '0022600123'
        limit: 返回最近的事件数量，默认 20

    Returns:
        逐回合事件列表，每个事件包含：
        - action_number: 事件编号
        - period: 节次
        - clock: 时钟
        - description: 事件描述
        - score_home: 主队得分
        - score_away: 客队得分
        - action_type: 事件类型
        - team_tricode: 球队缩写（如适用）
        - player_name: 球员姓名（如适用）

        如果获取失败返回 None

    Examples:
        >>> actions = get_playbyplay_data('0022600123', limit=10)
        >>> actions[0]['description']
        'D. Lillard 25' 3PT Jump Shot (Made)'
    """
    time.sleep(0.6)  # API 限流控制

    try:
        pbp = playbyplay.PlayByPlay(game_id=game_id)
        pbp_dict = pbp.get_dict()

        game_data = pbp_dict.get('game', {})
        actions = game_data.get('actions', [])

        # 取最近的 limit 条事件
        recent_actions = actions[-limit:] if limit > 0 else actions

        result = []
        for action in recent_actions:
            formatted_action = {
                'action_number': action.get('actionNumber', 0),
                'period': action.get('period', 0),
                'clock': action.get('clock', ''),
                'description': action.get('description', ''),
                'score_home': action.get('scoreHome', '0'),
                'score_away': action.get('scoreAway', '0'),
                'action_type': action.get('actionType', ''),
                'sub_type': action.get('subType', ''),
                'team_tricode': action.get('teamTricode', ''),
                'player_name': action.get('playerNameI', ''),
                'is_field_goal': action.get('isFieldGoal', 0),
                'shot_result': action.get('shotResult', ''),
            }
            result.append(formatted_action)

        return result

    except Exception as e:
        logger.error("获取逐回合数据失败: {}", e)
        return None


def get_playbyplay_since(game_id: str, since_action_number: int = 0) -> Optional[list[dict]]:
    """
    获取指定事件编号之后的所有逐回合数据（用于增量更新）

    Args:
        game_id: 比赛 ID
        since_action_number: 起始事件编号，返回此编号之后的事件

    Returns:
        新事件列表，格式同 get_playbyplay_data

    Examples:
        >>> # 第一次获取
        >>> actions = get_playbyplay_since('0022600123', 0)
        >>> last_num = actions[-1]['action_number'] if actions else 0
        >>> # 之后增量获取
        >>> new_actions = get_playbyplay_since('0022600123', last_num)
    """
    time.sleep(0.6)  # API 限流控制

    try:
        pbp = playbyplay.PlayByPlay(game_id=game_id)
        pbp_dict = pbp.get_dict()

        game_data = pbp_dict.get('game', {})
        actions = game_data.get('actions', [])

        # 筛选新事件
        new_actions = [a for a in actions if a.get('actionNumber', 0) > since_action_number]

        result = []
        for action in new_actions:
            formatted_action = {
                'action_number': action.get('actionNumber', 0),
                'period': action.get('period', 0),
                'clock': action.get('clock', ''),
                'description': action.get('description', ''),
                'score_home': action.get('scoreHome', '0'),
                'score_away': action.get('scoreAway', '0'),
                'action_type': action.get('actionType', ''),
                'sub_type': action.get('subType', ''),
                'team_tricode': action.get('teamTricode', ''),
                'player_name': action.get('playerNameI', ''),
                'is_field_goal': action.get('isFieldGoal', 0),
                'shot_result': action.get('shotResult', ''),
            }
            result.append(formatted_action)

        return result

    except Exception as e:
        logger.error("获取增量逐回合数据失败: {}", e)
        return None
