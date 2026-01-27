"""赛前分析数据模型。"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StyleMatchup:
    """球队风格对比分析。"""

    pace_advantage: Optional[str]  # 节奏优势方，如 "Home" 或 None
    pace_diff: float  # 节奏差异
    three_point_advantage: Optional[str]  # 三分优势方
    fg3_pct_diff: float  # 三分命中率差异
    defense_advantage: Optional[str]  # 防守优势方
    def_rating_diff: float  # 防守效率差异

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'pace_advantage': self.pace_advantage,
            'pace_diff': self.pace_diff,
            'three_point_advantage': self.three_point_advantage,
            'fg3_pct_diff': self.fg3_pct_diff,
            'defense_advantage': self.defense_advantage,
            'def_rating_diff': self.def_rating_diff
        }


@dataclass
class MatchupAnalysis:
    """对阵分析结果。"""

    head_to_head: dict  # 对阵历史（HeadToHeadRecord.to_dict()）
    style_matchup: StyleMatchup  # 风格对比

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'head_to_head': self.head_to_head,
            'style_matchup': self.style_matchup.to_dict()
        }


@dataclass
class ComparisonItem:
    """单项对比。"""

    metric: str  # 指标名称
    home_value: float  # 主队数值
    away_value: float  # 客队数值
    advantage: Optional[str]  # 优势方，"Home" / "Away" / None
    diff: float  # 差异值

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'metric': self.metric,
            'home_value': self.home_value,
            'away_value': self.away_value,
            'advantage': self.advantage,
            'diff': self.diff
        }


@dataclass
class StrengthComparison:
    """实力对比分析。"""

    home_overall: float  # 主队综合评分 (0-100)
    away_overall: float  # 客队综合评分 (0-100)
    overall_advantage: Optional[str]  # 整体优势方
    overall_diff: float  # 综合评分差异

    comparisons: list[ComparisonItem]  # 各项对比

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'home_overall': self.home_overall,
            'away_overall': self.away_overall,
            'overall_advantage': self.overall_advantage,
            'overall_diff': self.overall_diff,
            'comparisons': [c.to_dict() for c in self.comparisons]
        }


@dataclass
class Factor:
    """关键因素。"""

    name: str  # 因素名称
    impact: str  # 影响力等级："High" / "Medium" / "Low"
    description: str  # 描述
    favors: Optional[str]  # 有利于哪方："Home" / "Away" / None

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'name': self.name,
            'impact': self.impact,
            'description': self.description,
            'favors': self.favors
        }


@dataclass
class KeyFactors:
    """关键因素列表。"""

    top_factors: list[Factor]  # 按影响力排序的因素列表
    summary: str  # 摘要

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'top_factors': [f.to_dict() for f in self.top_factors],
            'summary': self.summary
        }
