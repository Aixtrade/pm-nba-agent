"""实力对比分析器。"""

from __future__ import annotations

from ..models.analysis import ComparisonItem, StrengthComparison
from ..models.team_data import TeamPregameData, TeamStatistics


class StrengthComparator:
    """对比两队整体与分项实力。"""

    def compare(self, home: TeamPregameData, away: TeamPregameData) -> StrengthComparison:
        """生成实力对比结果。"""
        comparisons = [
            self._compare_metric("Offense Rating", home.season_stats.off_rating, away.season_stats.off_rating),
            self._compare_defense("Defense Rating", home.season_stats.def_rating, away.season_stats.def_rating),
            self._compare_metric("Net Rating", home.season_stats.net_rating, away.season_stats.net_rating),
            self._compare_metric("Rebounds", home.season_stats.rpg, away.season_stats.rpg, threshold=1.5),
            self._compare_metric("3PT%", home.season_stats.fg3_pct, away.season_stats.fg3_pct, threshold=0.02),
        ]

        home_overall = self._overall_score(home.season_stats)
        away_overall = self._overall_score(away.season_stats)
        overall_diff = home_overall - away_overall

        if abs(overall_diff) < 5:
            overall_advantage = None
        else:
            overall_advantage = "Home" if overall_diff > 0 else "Away"

        return StrengthComparison(
            home_overall=home_overall,
            away_overall=away_overall,
            overall_advantage=overall_advantage,
            overall_diff=overall_diff,
            comparisons=comparisons,
        )

    def _overall_score(self, stats: TeamStatistics) -> float:
        """计算综合评分（0-100）。"""
        score = 50.0
        score += stats.net_rating * 2.0
        score += (stats.off_rating - 110.0) * 0.5
        score += (110.0 - stats.def_rating) * 0.5
        score += (stats.fg3_pct - 0.35) * 50.0
        score += (stats.rpg - 44.0) * 0.3
        return max(0.0, min(100.0, score))

    def _compare_metric(
        self,
        metric: str,
        home_value: float,
        away_value: float,
        threshold: float = 1.0,
    ) -> ComparisonItem:
        """通用正向指标对比。"""
        diff = home_value - away_value
        if abs(diff) < threshold:
            advantage = None
        else:
            advantage = "Home" if diff > 0 else "Away"
        return ComparisonItem(
            metric=metric,
            home_value=home_value,
            away_value=away_value,
            advantage=advantage,
            diff=diff,
        )

    def _compare_defense(self, metric: str, home_value: float, away_value: float) -> ComparisonItem:
        """防守效率数值越低越好。"""
        diff = home_value - away_value
        if abs(diff) < 2.0:
            advantage = None
        else:
            advantage = "Home" if diff < 0 else "Away"
        return ComparisonItem(
            metric=metric,
            home_value=home_value,
            away_value=away_value,
            advantage=advantage,
            diff=diff,
        )
