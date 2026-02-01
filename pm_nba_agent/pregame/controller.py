"""赛前分析主控制器。"""

from __future__ import annotations

from typing import Optional

from loguru import logger

from .analyzers import KeyFactorsAnalyzer, MatchupAnalyzer, StrengthComparator, TeamFormAnalyzer
from .cache import CacheManager
from .collectors import GameLogCollector, MatchupHistoryCollector, StandingsCollector, TeamStatsCollector
from .models.report import GameBasicInfo, PregameReport
from .models.team_data import HomeAwaySplits, TeamPregameData, TeamStandings, TeamStatistics
from ..nba import TeamInfo, get_team_info
from ..parsers import parse_polymarket_url


class PregameController:
    """赛前分析主流程控制器。"""

    def __init__(self, cache_ttl: int = 3600):
        self.cache = CacheManager(ttl=cache_ttl)

        self.standings_collector = StandingsCollector(self.cache)
        self.gamelog_collector = GameLogCollector(self.cache)
        self.team_stats_collector = TeamStatsCollector(self.cache)
        self.matchup_collector = MatchupHistoryCollector(self.cache)

        self.form_analyzer = TeamFormAnalyzer()
        self.matchup_analyzer = MatchupAnalyzer()
        self.strength_comparator = StrengthComparator()
        self.factors_analyzer = KeyFactorsAnalyzer()

    def analyze_from_url(
        self,
        url: str,
        season: str = "2025-26",
        depth: str = "full",
        verbose: bool = True,
    ) -> Optional[PregameReport]:
        """从 Polymarket URL 生成赛前分析报告（MVP）。"""
        if verbose:
            logger.info("开始赛前分析...")
            logger.info("URL: {}", url)

        event_info = parse_polymarket_url(url)
        if not event_info:
            if verbose:
                logger.error("URL 解析失败")
            return None

        team1 = get_team_info(event_info.team1_abbr)
        team2 = get_team_info(event_info.team2_abbr)

        if not team1 or not team2:
            if verbose:
                logger.error("球队信息获取失败")
            return None

        if verbose:
            logger.info("解析成功: {} vs {}", team1.full_name, team2.full_name)
            logger.info("收集数据...")

        team1_data = self._collect_team_data(team1, season, verbose)
        team2_data = self._collect_team_data(team2, season, verbose)

        if not team1_data or not team2_data:
            if verbose:
                logger.error("球队数据收集失败")
            return None

        home_data = team2_data
        away_data = team1_data

        if verbose:
            logger.info("分析对阵历史...")

        h2h = self.matchup_collector.collect(team1.id, team2.id, season, verbose)

        if verbose:
            logger.info("执行分析...")

        matchup_analysis = self.matchup_analyzer.analyze(home_data, away_data, h2h)
        strength_comparison = self.strength_comparator.compare(home_data, away_data)
        key_factors = self.factors_analyzer.analyze(home_data, away_data, matchup_analysis, strength_comparison)

        report = PregameReport(
            game_info=GameBasicInfo(
                home_team=home_data.team_name,
                away_team=away_data.team_name,
                game_date=event_info.game_date,
                season=season,
            ),
            home_team=home_data.to_dict(),
            away_team=away_data.to_dict(),
            matchup_analysis=matchup_analysis.to_dict() if matchup_analysis else None,
            strength_comparison=strength_comparison.to_dict(),
            key_factors=key_factors.to_dict(),
        )

        if verbose:
            logger.info("分析完成")

        return report

    def _collect_team_data(
        self,
        team_info: TeamInfo,
        season: str,
        verbose: bool,
    ) -> Optional[TeamPregameData]:
        """收集单支球队的赛前数据。"""
        if verbose:
            logger.info("{}", team_info.full_name)

        standings_map = self.standings_collector.collect(season, verbose)
        standings = None
        if standings_map:
            standings = standings_map.get(team_info.id)
        if standings is None:
            standings = self._default_standings()

        recent_games = self.gamelog_collector.collect(team_info.id, season, last_n=10, verbose=verbose) or []
        recent_form = self.form_analyzer.analyze_recent_form(recent_games)

        season_stats = self.team_stats_collector.collect_basic_and_advanced(team_info.id, season, verbose)
        if season_stats is None:
            season_stats = self._default_stats()

        splits = self.team_stats_collector.collect_splits(team_info.id, season, verbose)
        if splits is None:
            splits = self._default_splits()

        return TeamPregameData(
            team_id=team_info.id,
            team_name=team_info.full_name,
            team_abbr=team_info.abbreviation,
            standings=standings,
            recent_games=recent_games,
            recent_form=recent_form,
            season_stats=season_stats,
            home_away_splits=splits,
        )

    def _default_standings(self) -> TeamStandings:
        return TeamStandings(
            wins=0,
            losses=0,
            win_pct=0.0,
            conference_rank=0,
            division_rank=0,
            last_10="0-0",
            streak="",
        )

    def _default_stats(self) -> TeamStatistics:
        return TeamStatistics(
            ppg=0.0,
            opp_ppg=0.0,
            fg_pct=0.0,
            fg3_pct=0.0,
            ft_pct=0.0,
            rpg=0.0,
            apg=0.0,
            spg=0.0,
            bpg=0.0,
            tov=0.0,
            off_rating=0.0,
            def_rating=0.0,
            net_rating=0.0,
            pace=0.0,
            ts_pct=0.0,
            efg_pct=0.0,
        )

    def _default_splits(self) -> HomeAwaySplits:
        return HomeAwaySplits(
            home_wins=0,
            home_losses=0,
            home_win_pct=0.0,
            home_ppg=0.0,
            home_opp_ppg=0.0,
            away_wins=0,
            away_losses=0,
            away_win_pct=0.0,
            away_ppg=0.0,
            away_opp_ppg=0.0,
        )
