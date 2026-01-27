"""球队统计数据收集器。"""

from typing import Optional

from nba_api.stats.endpoints import leaguedashteamstats, teamdashboardbygeneralsplits

from ..models.team_data import HomeAwaySplits, TeamStatistics
from .base import BaseCollector


class TeamStatsCollector(BaseCollector):
    """收集球队统计数据。"""

    def collect(
        self,
        team_id: int,
        season: str,
        verbose: bool = False,
    ) -> Optional[TeamStatistics]:
        """统一入口，默认返回基础+高级统计。"""
        return self.collect_basic_and_advanced(team_id, season, verbose)

    def collect_basic_and_advanced(
        self,
        team_id: int,
        season: str,
        verbose: bool = False
    ) -> Optional[TeamStatistics]:
        """收集球队的基础和高级统计数据。

        Args:
            team_id: 球队ID
            season: 赛季字符串，如 '2025-26'
            verbose: 是否输出详细日志

        Returns:
            球队统计数据，失败返回 None
        """
        # 先尝试从全局数据中获取（优化）
        key_basic = f"league_stats_basic_{season}"
        key_advanced = f"league_stats_advanced_{season}"

        # 获取基础统计
        def fetch_basic():
            stats_api = leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                season_type_all_star='Regular Season',
                measure_type_detailed_defense='Base',
                per_mode_detailed='PerGame'
            )
            return stats_api.league_dash_team_stats.get_data_frame()

        df_basic = self._fetch_with_cache(key_basic, fetch_basic, verbose)
        if df_basic is None:
            return None

        # 获取高级统计
        def fetch_advanced():
            stats_api = leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                season_type_all_star='Regular Season',
                measure_type_detailed_defense='Advanced',
                per_mode_detailed='PerGame'
            )
            return stats_api.league_dash_team_stats.get_data_frame()

        df_advanced = self._fetch_with_cache(key_advanced, fetch_advanced, verbose)
        if df_advanced is None:
            return None

        # 过滤指定球队
        team_basic = df_basic[df_basic['TEAM_ID'] == team_id]
        team_advanced = df_advanced[df_advanced['TEAM_ID'] == team_id]

        if team_basic.empty or team_advanced.empty:
            if verbose:
                print(f"  ❌ 未找到球队 {team_id} 的统计数据")
            return None

        basic_row = team_basic.iloc[0]
        advanced_row = team_advanced.iloc[0]

        return TeamStatistics(
            # 基础统计
            ppg=float(basic_row.get('PTS', 0)),
            opp_ppg=float(basic_row.get('OPP_PTS', 0)) if 'OPP_PTS' in basic_row else 0.0,
            fg_pct=float(basic_row.get('FG_PCT', 0)),
            fg3_pct=float(basic_row.get('FG3_PCT', 0)),
            ft_pct=float(basic_row.get('FT_PCT', 0)),
            rpg=float(basic_row.get('REB', 0)),
            apg=float(basic_row.get('AST', 0)),
            spg=float(basic_row.get('STL', 0)),
            bpg=float(basic_row.get('BLK', 0)),
            tov=float(basic_row.get('TOV', 0)),
            # 高级统计
            off_rating=float(advanced_row.get('OFF_RATING', 0)),
            def_rating=float(advanced_row.get('DEF_RATING', 0)),
            net_rating=float(advanced_row.get('NET_RATING', 0)),
            pace=float(advanced_row.get('PACE', 0)),
            ts_pct=float(advanced_row.get('TS_PCT', 0)),
            efg_pct=float(advanced_row.get('EFG_PCT', 0))
        )

    def collect_splits(
        self,
        team_id: int,
        season: str,
        verbose: bool = False
    ) -> Optional[HomeAwaySplits]:
        """收集球队的主客场统计数据。

        Args:
            team_id: 球队ID
            season: 赛季字符串，如 '2025-26'
            verbose: 是否输出详细日志

        Returns:
            主客场统计数据，失败返回 None
        """
        key = f"splits_{team_id}_{season}"

        def fetch():
            splits_api = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
                team_id=str(team_id),
                season=season,
                season_type_all_star='Regular Season'
            )
            df = splits_api.overall_team_dashboard.get_data_frame()

            # 查找主场和客场数据
            home_row = df[df['GROUP_VALUE'] == 'Home']
            away_row = df[df['GROUP_VALUE'] == 'Road']

            if home_row.empty or away_row.empty:
                return None

            home = home_row.iloc[0]
            away = away_row.iloc[0]

            # 解析战绩字符串 "25-15"
            def parse_record(record_str):
                try:
                    w, l = record_str.split('-')
                    return int(w), int(l)
                except:
                    return 0, 0

            home_w, home_l = parse_record(str(home.get('W_L', '0-0')))
            away_w, away_l = parse_record(str(away.get('W_L', '0-0')))

            return HomeAwaySplits(
                home_wins=home_w,
                home_losses=home_l,
                home_win_pct=float(home.get('W_PCT', 0)),
                home_ppg=float(home.get('PTS', 0)),
                home_opp_ppg=float(home.get('OPP_PTS', 0)) if 'OPP_PTS' in home else 0.0,
                away_wins=away_w,
                away_losses=away_l,
                away_win_pct=float(away.get('W_PCT', 0)),
                away_ppg=float(away.get('PTS', 0)),
                away_opp_ppg=float(away.get('OPP_PTS', 0)) if 'OPP_PTS' in away else 0.0
            )

        return self._fetch_with_cache(key, fetch, verbose)
