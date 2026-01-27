"""赛前报告数据模型。"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GameBasicInfo:
    """比赛基本信息。"""

    home_team: str  # 主队名称
    away_team: str  # 客队名称
    game_date: str  # 比赛日期
    season: str  # 赛季

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'home_team': self.home_team,
            'away_team': self.away_team,
            'game_date': self.game_date,
            'season': self.season
        }


@dataclass
class PregameReport:
    """完整的赛前分析报告。"""

    game_info: GameBasicInfo
    home_team: dict  # TeamPregameData.to_dict()
    away_team: dict  # TeamPregameData.to_dict()
    matchup_analysis: Optional[dict]  # MatchupAnalysis.to_dict()
    strength_comparison: dict  # StrengthComparison.to_dict()
    key_factors: dict  # KeyFactors.to_dict()

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'game_info': self.game_info.to_dict(),
            'home_team': self.home_team,
            'away_team': self.away_team,
            'matchup_analysis': self.matchup_analysis,
            'strength_comparison': self.strength_comparison,
            'key_factors': self.key_factors
        }
