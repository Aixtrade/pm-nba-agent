"""比赛日志数据收集器。"""

from typing import Optional

from nba_api.stats.endpoints import teamgamelog

from ..models.team_data import GameSummary
from .base import BaseCollector


class GameLogCollector(BaseCollector):
    """收集球队比赛日志数据。"""

    def collect(
        self,
        team_id: int,
        season: str,
        last_n: int = 10,
        verbose: bool = False
    ) -> Optional[list[GameSummary]]:
        """收集指定球队的比赛日志。

        Args:
            team_id: 球队ID
            season: 赛季字符串，如 '2025-26'
            last_n: 最近N场比赛，默认10场
            verbose: 是否输出详细日志

        Returns:
            比赛摘要列表，失败返回 None
        """
        key = f"gamelog_{team_id}_{season}"

        def fetch():
            gamelog_api = teamgamelog.TeamGameLog(
                team_id=str(team_id),
                season=season,
                season_type_all_star='Regular Season'
            )
            df = gamelog_api.team_game_log.get_data_frame()

            # 只取最近 N 场
            df = df.head(last_n)

            games = []
            for _, row in df.iterrows():
                # 解析对手和主客场
                matchup = str(row['MATCHUP'])
                if ' vs. ' in matchup:
                    is_home = True
                    opponent = matchup.split(' vs. ')[1]
                elif ' @ ' in matchup:
                    is_home = False
                    opponent = matchup.split(' @ ')[1]
                else:
                    is_home = True
                    opponent = 'Unknown'

                # 计算对手得分
                points = int(row['PTS'])
                plus_minus = int(row['PLUS_MINUS'])
                opp_points = points - plus_minus

                games.append(GameSummary(
                    game_id=str(row['Game_ID']),
                    date=str(row['GAME_DATE']),
                    opponent=opponent,
                    is_home=is_home,
                    result=str(row['WL']),
                    points=points,
                    opp_points=opp_points,
                    plus_minus=plus_minus
                ))

            return games

        return self._fetch_with_cache(key, fetch, verbose)
