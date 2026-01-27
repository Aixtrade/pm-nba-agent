"""关键因素分析器。"""

from __future__ import annotations

from ..models.analysis import Factor, KeyFactors, MatchupAnalysis, StrengthComparison
from ..models.team_data import TeamPregameData


class KeyFactorsAnalyzer:
    """根据基础指标输出关键影响因素。"""

    def analyze(
        self,
        home: TeamPregameData,
        away: TeamPregameData,
        matchup: MatchupAnalysis,
        comparison: StrengthComparison,
    ) -> KeyFactors:
        """识别关键因素并生成摘要。"""
        factors: list[Factor] = []

        home_home_pct = home.home_away_splits.home_win_pct
        home_away_pct = home.home_away_splits.away_win_pct
        if home_home_pct - home_away_pct >= 0.1:
            factors.append(Factor(
                name="Home Court Strength",
                impact="High",
                description=f"主队主场胜率 {home_home_pct:.1%} 明显高于客场",
                favors="Home",
            ))

        momentum_gap = home.recent_form.momentum - away.recent_form.momentum
        if abs(momentum_gap) >= 12:
            favors = "Home" if momentum_gap > 0 else "Away"
            factors.append(Factor(
                name="Momentum Gap",
                impact="Medium",
                description=f"近期势头差距 {abs(momentum_gap):.0f} 分",
                favors=favors,
            ))

        if matchup.head_to_head and matchup.head_to_head.get("season_record"):
            record = matchup.head_to_head.get("season_record", "0-0")
            if record not in {"0-0", "1-1"}:
                factors.append(Factor(
                    name="Season Series",
                    impact="Low",
                    description=f"本赛季交手战绩 {record}",
                    favors=None,
                ))

        if abs(comparison.overall_diff) >= 8:
            favors = "Home" if comparison.overall_diff > 0 else "Away"
            factors.append(Factor(
                name="Overall Rating Gap",
                impact="High",
                description=f"综合评分差距 {abs(comparison.overall_diff):.1f}",
                favors=favors,
            ))

        if matchup.style_matchup.pace_advantage:
            factors.append(Factor(
                name="Pace Advantage",
                impact="Low",
                description=f"节奏优势在 {matchup.style_matchup.pace_advantage} 方",
                favors=matchup.style_matchup.pace_advantage,
            ))

        factors.sort(key=lambda item: self._impact_score(item.impact), reverse=True)
        summary = self._build_summary(factors)

        return KeyFactors(
            top_factors=factors[:5],
            summary=summary,
        )

    def _impact_score(self, impact: str) -> int:
        return {"High": 3, "Medium": 2, "Low": 1}.get(impact, 0)

    def _build_summary(self, factors: list[Factor]) -> str:
        if not factors:
            return "关键因素暂无显著差异"
        top_names = ", ".join(f.name for f in factors[:3])
        return f"关键因素: {top_names}"
