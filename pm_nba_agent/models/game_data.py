"""NBA 比赛数据模型"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class GameInfo:
    """比赛基本信息"""
    game_id: str
    game_date: str
    status: str
    period: int
    game_clock: str
    game_status_code: int  # 1=未开始, 2=进行中, 3=已结束


@dataclass
class TeamStats:
    """球队统计数据"""
    name: str
    abbreviation: str
    score: int
    statistics: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_live_api(cls, team_data: dict) -> 'TeamStats':
        """从 Live API 数据创建"""
        stats = team_data.get('statistics', {})
        return cls(
            name=team_data.get('teamName', ''),
            abbreviation=team_data.get('teamTricode', ''),
            score=team_data.get('score', 0),
            statistics={
                'rebounds': stats.get('reboundsTotal', 0),
                'assists': stats.get('assists', 0),
                'field_goal_pct': stats.get('fieldGoalsPercentage', 0.0),
                'three_point_pct': stats.get('threePointersPercentage', 0.0),
                'free_throw_pct': stats.get('freeThrowsPercentage', 0.0),
                'turnovers': stats.get('turnovers', 0),
                'steals': stats.get('steals', 0),
                'blocks': stats.get('blocks', 0),
            }
        )


@dataclass
class PlayerStats:
    """球员统计数据"""
    name: str
    team: str
    position: str
    on_court: bool
    stats: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_live_api(cls, player_data: dict, team_abbr: str) -> 'PlayerStats':
        """从 Live API 数据创建"""
        stats = player_data.get('statistics', {})
        return cls(
            name=player_data.get('name', ''),
            team=team_abbr,
            position=player_data.get('position', ''),
            on_court=player_data.get('oncourt', '0') == '1',
            stats={
                'points': stats.get('points', 0),
                'rebounds': stats.get('reboundsTotal', 0),
                'assists': stats.get('assists', 0),
                'minutes': stats.get('minutes', '0:00'),
                'field_goals_made': stats.get('fieldGoalsMade', 0),
                'field_goals_attempted': stats.get('fieldGoalsAttempted', 0),
                'three_pointers_made': stats.get('threePointersMade', 0),
                'three_pointers_attempted': stats.get('threePointersAttempted', 0),
                'free_throws_made': stats.get('freeThrowsMade', 0),
                'free_throws_attempted': stats.get('freeThrowsAttempted', 0),
                'steals': stats.get('steals', 0),
                'blocks': stats.get('blocks', 0),
                'turnovers': stats.get('turnovers', 0),
                'plus_minus': stats.get('plusMinusPoints', 0),
            }
        )


@dataclass
class GameData:
    """完整比赛数据"""
    game_info: GameInfo
    home_team: TeamStats
    away_team: TeamStats
    players: List[PlayerStats] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'game_info': {
                'game_id': self.game_info.game_id,
                'game_date': self.game_info.game_date,
                'status': self.game_info.status,
                'period': self.game_info.period,
                'game_clock': self.game_info.game_clock,
            },
            'teams': {
                'home': {
                    'name': self.home_team.name,
                    'abbreviation': self.home_team.abbreviation,
                    'score': self.home_team.score,
                    'statistics': self.home_team.statistics,
                },
                'away': {
                    'name': self.away_team.name,
                    'abbreviation': self.away_team.abbreviation,
                    'score': self.away_team.score,
                    'statistics': self.away_team.statistics,
                }
            },
            'players': [
                {
                    'name': p.name,
                    'team': p.team,
                    'position': p.position,
                    'on_court': p.on_court,
                    'stats': p.stats,
                }
                for p in self.players
            ]
        }
