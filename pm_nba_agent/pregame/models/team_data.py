"""球队赛前数据模型。"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TeamStandings:
    """球队排名和战绩数据。"""

    wins: int
    losses: int
    win_pct: float
    conference_rank: int
    division_rank: int
    last_10: str  # 最近10场战绩，如 "7-3"
    streak: str  # 连胜/连败，如 "W2" 或 "L3"

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'wins': self.wins,
            'losses': self.losses,
            'win_pct': self.win_pct,
            'conference_rank': self.conference_rank,
            'division_rank': self.division_rank,
            'last_10': self.last_10,
            'streak': self.streak
        }


@dataclass
class GameSummary:
    """单场比赛摘要。"""

    game_id: str
    date: str
    opponent: str
    is_home: bool
    result: str  # 'W' 或 'L'
    points: int
    opp_points: int
    plus_minus: int

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'game_id': self.game_id,
            'date': self.date,
            'opponent': self.opponent,
            'is_home': self.is_home,
            'result': self.result,
            'points': self.points,
            'opp_points': self.opp_points,
            'plus_minus': self.plus_minus
        }


@dataclass
class RecentForm:
    """最近比赛表现统计。"""

    last_n_games: int  # 最近N场
    wins: int
    losses: int
    win_pct: float
    avg_points: float
    avg_opp_points: float
    avg_margin: float
    momentum: float  # 势头评分 (0-100)

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'last_n_games': self.last_n_games,
            'wins': self.wins,
            'losses': self.losses,
            'win_pct': self.win_pct,
            'avg_points': self.avg_points,
            'avg_opp_points': self.avg_opp_points,
            'avg_margin': self.avg_margin,
            'momentum': self.momentum
        }


@dataclass
class HomeAwaySplits:
    """主客场数据对比。"""

    home_wins: int
    home_losses: int
    home_win_pct: float
    home_ppg: float
    home_opp_ppg: float

    away_wins: int
    away_losses: int
    away_win_pct: float
    away_ppg: float
    away_opp_ppg: float

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'home': {
                'wins': self.home_wins,
                'losses': self.home_losses,
                'win_pct': self.home_win_pct,
                'ppg': self.home_ppg,
                'opp_ppg': self.home_opp_ppg
            },
            'away': {
                'wins': self.away_wins,
                'losses': self.away_losses,
                'win_pct': self.away_win_pct,
                'ppg': self.away_ppg,
                'opp_ppg': self.away_opp_ppg
            }
        }


@dataclass
class TeamStatistics:
    """球队统计数据。"""

    # 基础统计
    ppg: float  # 场均得分
    opp_ppg: float  # 场均失分
    fg_pct: float  # 投篮命中率
    fg3_pct: float  # 三分命中率
    ft_pct: float  # 罚球命中率
    rpg: float  # 场均篮板
    apg: float  # 场均助攻
    spg: float  # 场均抢断
    bpg: float  # 场均盖帽
    tov: float  # 场均失误

    # 高级统计
    off_rating: float  # 进攻效率
    def_rating: float  # 防守效率
    net_rating: float  # 净效率
    pace: float  # 节奏
    ts_pct: float  # 真实命中率
    efg_pct: float  # 有效命中率

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'basic': {
                'ppg': self.ppg,
                'opp_ppg': self.opp_ppg,
                'fg_pct': self.fg_pct,
                'fg3_pct': self.fg3_pct,
                'ft_pct': self.ft_pct,
                'rpg': self.rpg,
                'apg': self.apg,
                'spg': self.spg,
                'bpg': self.bpg,
                'tov': self.tov
            },
            'advanced': {
                'off_rating': self.off_rating,
                'def_rating': self.def_rating,
                'net_rating': self.net_rating,
                'pace': self.pace,
                'ts_pct': self.ts_pct,
                'efg_pct': self.efg_pct
            }
        }


@dataclass
class TeamPregameData:
    """完整的球队赛前数据。"""

    team_id: int
    team_name: str
    team_abbr: str

    standings: TeamStandings
    recent_games: list[GameSummary]
    recent_form: RecentForm
    season_stats: TeamStatistics
    home_away_splits: HomeAwaySplits

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'team_info': {
                'id': self.team_id,
                'name': self.team_name,
                'abbr': self.team_abbr
            },
            'standings': self.standings.to_dict(),
            'recent_games': [g.to_dict() for g in self.recent_games],
            'recent_form': self.recent_form.to_dict(),
            'season_stats': self.season_stats.to_dict(),
            'home_away_splits': self.home_away_splits.to_dict()
        }
