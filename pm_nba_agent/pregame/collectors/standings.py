"""球队排名数据收集器。"""

from typing import Optional, cast

from nba_api.stats.endpoints import leaguestandingsv3
from nba_api.stats.library.parameters import SeasonType

from ..models.team_data import TeamStandings
from .base import BaseCollector


class StandingsCollector(BaseCollector):
    """收集联盟排名数据。"""

    def collect(
        self,
        season: str,
        verbose: bool = False,
    ) -> Optional[dict[int, TeamStandings]]:
        """收集指定赛季的球队排名数据。

        Args:
            season: 赛季字符串，如 '2025-26'
            verbose: 是否输出详细日志

        Returns:
            字典 {team_id: TeamStandings}，失败返回 None
        """
        key = f"standings_{season}"

        def fetch():
            standings_api = leaguestandingsv3.LeagueStandingsV3(
                season=season,
                season_type=SeasonType.regular,
            )
            df = standings_api.standings.get_data_frame()

            result = {}
            for _, row in df.iterrows():
                team_id = cast(int, self._get_int(row, ["TeamID", "TEAM_ID", "TEAMID"], 0))
                result[team_id] = TeamStandings(
                    wins=cast(int, self._get_int(row, ["WINS", "W"], 0)),
                    losses=cast(int, self._get_int(row, ["LOSSES", "L"], 0)),
                    win_pct=cast(float, self._get_float(row, ["WinPCT", "W_PCT"], 0.0)),
                    conference_rank=cast(int, self._get_int(row, ["ConferenceRank", "CONF_RANK", "Conference"], 0)),
                    division_rank=cast(int, self._get_int(row, ["DivisionRank", "DIV_RANK", "Division"], 0)),
                    last_10=cast(str, self._get_str(row, ["L10", "LAST_10"], "0-0")),
                    streak=cast(str, self._get_str(row, ["strCurrentStreak", "STREAK"], ""))
                )

            return result

        return self._fetch_with_cache(key, fetch, verbose)

    def _get_value(self, row, keys: list[str], default):
        for key in keys:
            if key in row:
                value = row.get(key)
                if value is not None:
                    return value
        return default

    def _get_int(self, row, keys: list[str], default: int) -> int:
        value = self._get_value(row, keys, default)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _get_float(self, row, keys: list[str], default: float) -> float:
        value = self._get_value(row, keys, default)
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _get_str(self, row, keys: list[str], default: str) -> str:
        value = self._get_value(row, keys, default)
        return str(value) if value is not None else default
