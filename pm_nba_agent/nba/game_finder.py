"""NBA 比赛查找"""

from typing import Optional
from datetime import datetime
from nba_api.stats.endpoints import scoreboardv2
from nba_api.live.nba.endpoints import scoreboard
import time


def find_game_by_teams_and_date(
    team1_abbr: str,
    team2_abbr: str,
    game_date: str,
    use_live_api: bool = True
) -> Optional[str]:
    """
    根据球队缩写和日期查找比赛 game_id

    Args:
        team1_abbr: 球队1缩写，如 'ORL'
        team2_abbr: 球队2缩写，如 'CLE'
        game_date: 比赛日期，格式 'YYYY-MM-DD'
        use_live_api: 是否优先使用 Live API（推荐，速度更快）

    Returns:
        game_id 字符串，如果找不到返回 None

    Examples:
        >>> game_id = find_game_by_teams_and_date('ORL', 'CLE', '2026-01-26')
        >>> game_id
        '0022600123'
    """
    # 优先尝试 Live API（适用于正在进行或今天的比赛）
    if use_live_api:
        try:
            game_id = _find_game_live(team1_abbr, team2_abbr)
            if game_id:
                return game_id
        except Exception as e:
            print(f"Live API 查询失败: {e}, 尝试使用 Stats API")

    # 降级到 Stats API 查询特定日期
    return _find_game_stats(team1_abbr, team2_abbr, game_date)


def _find_game_live(team1_abbr: str, team2_abbr: str) -> Optional[str]:
    """
    使用 Live API 查找今日比赛

    Args:
        team1_abbr: 球队1缩写
        team2_abbr: 球队2缩写

    Returns:
        game_id 或 None
    """
    time.sleep(0.6)  # API 限流控制

    games = scoreboard.ScoreBoard()
    games_dict = games.get_dict()

    # 遍历查找匹配的比赛
    for game in games_dict['scoreboard']['games']:
        home_team = game['homeTeam']['teamTricode']
        away_team = game['awayTeam']['teamTricode']

        # 检查两个球队是否匹配（不考虑主客场顺序）
        teams_set = {home_team, away_team}
        target_set = {team1_abbr.upper(), team2_abbr.upper()}

        if teams_set == target_set:
            return game['gameId']

    return None


def _find_game_stats(team1_abbr: str, team2_abbr: str, game_date: str) -> Optional[str]:
    """
    使用 Stats API 查找特定日期比赛

    Args:
        team1_abbr: 球队1缩写
        team2_abbr: 球队2缩写
        game_date: 比赛日期，格式 'YYYY-MM-DD'

    Returns:
        game_id 或 None
    """
    time.sleep(0.6)  # API 限流控制

    # ScoreboardV2 需要 MM/DD/YYYY 格式
    try:
        dt = datetime.strptime(game_date, '%Y-%m-%d')
        formatted_date = dt.strftime('%m/%d/%Y')
    except ValueError:
        print(f"无效的日期格式: {game_date}")
        return None

    try:
        board = scoreboardv2.ScoreboardV2(
            game_date=formatted_date,
            league_id='00',
            day_offset=0
        )

        game_header = board.game_header.get_dict()

        # 遍历所有比赛
        for game in game_header['data']:
            # game_header 数据结构: [GAME_ID, GAME_DATE_EST, ...]
            # 需要检查球队缩写
            game_id = game[2]  # GAME_ID
            home_team_id = game[6]  # HOME_TEAM_ID
            visitor_team_id = game[7]  # VISITOR_TEAM_ID

            # 通过 line_score 获取球队缩写
            line_score = board.line_score.get_dict()

            home_abbr = None
            away_abbr = None

            for line in line_score['data']:
                if line[1] == game_date and line[2] == game_id:  # GAME_DATE_EST, GAME_ID
                    team_abbr = line[4]  # TEAM_ABBREVIATION
                    team_id = line[3]  # TEAM_ID

                    if team_id == home_team_id:
                        home_abbr = team_abbr
                    elif team_id == visitor_team_id:
                        away_abbr = team_abbr

            if home_abbr and away_abbr:
                teams_set = {home_abbr, away_abbr}
                target_set = {team1_abbr.upper(), team2_abbr.upper()}

                if teams_set == target_set:
                    return game_id

    except Exception as e:
        print(f"Stats API 查询失败: {e}")
        return None

    return None


def get_todays_games() -> list[dict]:
    """
    获取今日所有比赛列表

    Returns:
        比赛信息列表，每个元素包含 game_id, home_team, away_team, status
    """
    time.sleep(0.6)

    try:
        games = scoreboard.ScoreBoard()
        games_dict = games.get_dict()

        result = []
        for game in games_dict['scoreboard']['games']:
            result.append({
                'game_id': game['gameId'],
                'home_team': game['homeTeam']['teamTricode'],
                'away_team': game['awayTeam']['teamTricode'],
                'status': game['gameStatusText'],
                'home_score': game['homeTeam']['score'],
                'away_score': game['awayTeam']['score'],
            })

        return result
    except Exception as e:
        print(f"获取今日比赛失败: {e}")
        return []
