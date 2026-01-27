"""球队近期状态分析器。"""

from __future__ import annotations

from typing import Iterable

from ..models.team_data import GameSummary, RecentForm


class TeamFormAnalyzer:
    """分析球队近期表现并输出状态指标。"""

    def analyze_recent_form(self, games: Iterable[GameSummary]) -> RecentForm:
        """计算最近比赛的整体表现。"""
        games_list = list(games) if games else []
        if not games_list:
            return RecentForm(
                last_n_games=0,
                wins=0,
                losses=0,
                win_pct=0.0,
                avg_points=0.0,
                avg_opp_points=0.0,
                avg_margin=0.0,
                momentum=50.0,
            )

        wins = sum(1 for g in games_list if g.result == "W")
        losses = len(games_list) - wins
        total_points = sum(g.points for g in games_list)
        total_opp = sum(g.opp_points for g in games_list)
        avg_points = total_points / len(games_list)
        avg_opp = total_opp / len(games_list)
        avg_margin = (total_points - total_opp) / len(games_list)

        momentum = self._calculate_momentum(games_list, avg_margin)

        return RecentForm(
            last_n_games=len(games_list),
            wins=wins,
            losses=losses,
            win_pct=wins / len(games_list),
            avg_points=avg_points,
            avg_opp_points=avg_opp,
            avg_margin=avg_margin,
            momentum=momentum,
        )

    def _calculate_momentum(self, games: list[GameSummary], avg_margin: float) -> float:
        """计算势头评分（0-100）。"""
        if not games:
            return 50.0

        win_pct = sum(1 for g in games[:5] if g.result == "W") / min(5, len(games))
        win_component = (win_pct - 0.5) * 40
        margin_component = max(-10.0, min(10.0, avg_margin)) / 10.0 * 10.0

        streak_sign, streak_len = self._get_streak(games)
        streak_component = streak_sign * min(10.0, streak_len * 2.0)

        score = 50.0 + win_component + margin_component + streak_component
        return max(0.0, min(100.0, score))

    def _get_streak(self, games: list[GameSummary]) -> tuple[int, int]:
        """计算连续胜负的方向与长度。"""
        if not games:
            return 0, 0

        first_result = games[0].result
        streak_len = 0
        for game in games:
            if game.result == first_result:
                streak_len += 1
            else:
                break

        if first_result == "W":
            return 1, streak_len
        if first_result == "L":
            return -1, streak_len
        return 0, 0
