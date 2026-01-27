"""对阵分析器。"""

from __future__ import annotations

from ..collectors.matchup import HeadToHeadRecord
from ..models.analysis import MatchupAnalysis, StyleMatchup
from ..models.team_data import TeamPregameData


class MatchupAnalyzer:
    """生成对阵风格与历史概览。"""

    def analyze(
        self,
        home_team: TeamPregameData,
        away_team: TeamPregameData,
        h2h: HeadToHeadRecord | None,
    ) -> MatchupAnalysis:
        """综合对阵分析。"""
        head_to_head = h2h.to_dict() if h2h else {}
        style_matchup = self._analyze_style_matchup(home_team, away_team)
        return MatchupAnalysis(
            head_to_head=head_to_head,
            style_matchup=style_matchup,
        )

    def _analyze_style_matchup(
        self,
        home: TeamPregameData,
        away: TeamPregameData,
    ) -> StyleMatchup:
        """对节奏、三分和防守效率做快速对比。"""
        pace_diff = home.season_stats.pace - away.season_stats.pace
        pace_advantage = self._advantage_by_threshold(pace_diff, 2.0)

        fg3_diff = home.season_stats.fg3_pct - away.season_stats.fg3_pct
        three_point_advantage = self._advantage_by_threshold(fg3_diff, 0.02)

        def_rating_diff = home.season_stats.def_rating - away.season_stats.def_rating
        defense_advantage = self._defense_advantage(def_rating_diff)

        return StyleMatchup(
            pace_advantage=pace_advantage,
            pace_diff=pace_diff,
            three_point_advantage=three_point_advantage,
            fg3_pct_diff=fg3_diff,
            defense_advantage=defense_advantage,
            def_rating_diff=def_rating_diff,
        )

    def _advantage_by_threshold(self, diff: float, threshold: float) -> str | None:
        """按阈值判断优势方。"""
        if abs(diff) < threshold:
            return None
        return "Home" if diff > 0 else "Away"

    def _defense_advantage(self, diff: float) -> str | None:
        """防守效率越低越好。"""
        if abs(diff) < 2.0:
            return None
        return "Home" if diff < 0 else "Away"
