"""对阵历史数据收集器（简化版）。"""

from dataclasses import dataclass
from typing import Optional

from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.static import teams

from .base import BaseCollector


@dataclass
class HeadToHeadRecord:
    """对阵历史战绩（简化版）。"""

    season_record: str  # 本赛季战绩，如 "2-1"
    last_5_record: str  # 最近5场战绩（MVP版本与season相同）
    last_meeting: Optional[str]  # 上次交手日期
    avg_margin: float  # 平均分差

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            'season_record': self.season_record,
            'last_5_record': self.last_5_record,
            'last_meeting': self.last_meeting,
            'avg_margin': self.avg_margin
        }


class MatchupHistoryCollector(BaseCollector):
    """收集对阵历史数据（简化版）。"""

    def collect(
        self,
        team1_id: int,
        team2_id: int,
        season: str,
        verbose: bool = False
    ) -> Optional[HeadToHeadRecord]:
        """收集两队本赛季的对阵历史。

        Args:
            team1_id: 球队1 ID
            team2_id: 球队2 ID
            season: 赛季字符串，如 '2025-26'
            verbose: 是否输出详细日志

        Returns:
            对阵历史战绩，失败返回空记录
        """
        key = f"matchup_{team1_id}_{team2_id}_{season}"

        def fetch():
            try:
                # 获取球队2的缩写（用于匹配）
                all_teams = teams.get_teams()
                team2_abbr = None
                for t in all_teams:
                    if t['id'] == team2_id:
                        team2_abbr = t['abbreviation']
                        break

                if not team2_abbr:
                    return self._empty_record()

                # 查找球队1本赛季所有比赛
                games_api = leaguegamefinder.LeagueGameFinder(
                    team_id_nullable=str(team1_id),
                    season_nullable=season
                )
                df = games_api.league_game_finder_results.get_data_frame()

                if df.empty:
                    return self._empty_record()

                # 筛选对阵球队2的比赛
                # MATCHUP 格式: "LAL vs. BOS" 或 "LAL @ BOS"
                matchup_games = df[df['MATCHUP'].str.contains(team2_abbr, na=False)]

                if matchup_games.empty:
                    return self._empty_record()

                # 计算战绩
                wins = len(matchup_games[matchup_games['WL'] == 'W'])
                losses = len(matchup_games[matchup_games['WL'] == 'L'])
                total = wins + losses

                # 平均分差
                avg_margin = float(matchup_games['PLUS_MINUS'].mean()) if not matchup_games.empty else 0.0

                # 上次交手日期
                last_meeting = str(matchup_games.iloc[0]['GAME_DATE']) if not matchup_games.empty else None

                return HeadToHeadRecord(
                    season_record=f"{wins}-{losses}",
                    last_5_record=f"{wins}-{losses}",  # MVP版本简化
                    last_meeting=last_meeting,
                    avg_margin=avg_margin
                )

            except Exception as e:
                if verbose:
                    print(f"  ⚠️  对阵历史获取失败: {e}")
                return self._empty_record()

        result = self._fetch_with_cache(key, fetch, verbose)
        return result if result else self._empty_record()

    def _empty_record(self) -> HeadToHeadRecord:
        """返回空记录。"""
        return HeadToHeadRecord(
            season_record="0-0",
            last_5_record="0-0",
            last_meeting=None,
            avg_margin=0.0
        )
