# 赛前分析系统设计方案

## 一、系统架构

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     用户请求                                  │
│              (Polymarket URL + 分析深度)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  主控制器 (PregameController)                 │
│  - 解析 URL                                                   │
│  - 协调数据收集                                               │
│  - 生成分析报告                                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ 数据收集层    │  │  缓存层       │  │  分析层       │
│ (Collectors) │  │  (Cache)     │  │ (Analyzers)  │
└──────────────┘  └──────────────┘  └──────────────┘
        │                                    │
        └────────────────┬───────────────────┘
                         ▼
                ┌──────────────────┐
                │   数据模型层      │
                │   (Models)       │
                └──────────────────┘
                         │
                         ▼
                ┌──────────────────┐
                │   输出报告        │
                │ (PregameReport)  │
                └──────────────────┘
```

### 1.2 模块职责

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **主控制器** | 协调整个分析流程 | URL, 分析配置 | 完整报告 |
| **数据收集器** | 从 NBA API 获取原始数据 | 球队ID, 赛季 | 原始统计数据 |
| **缓存管理器** | 管理数据缓存，减少 API 调用 | 数据键 | 缓存数据 |
| **分析器** | 处理数据，生成洞察 | 原始数据 | 分析结果 |
| **数据模型** | 数据结构定义 | - | 结构化数据 |

---

## 二、数据模型设计

### 2.1 赛前分析报告模型

```python
@dataclass
class PregameReport:
    """完整的赛前分析报告"""

    # 基本信息
    game_info: GameBasicInfo

    # 球队基础数据
    home_team: TeamPregameData
    away_team: TeamPregameData

    # 对阵分析
    matchup_analysis: MatchupAnalysis

    # 实力对比
    strength_comparison: StrengthComparison

    # 关键因素
    key_factors: KeyFactors

    # 预测结果（可选）
    prediction: Optional[PredictionResult] = None

    # 生成时间
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
```

### 2.2 球队赛前数据模型

```python
@dataclass
class TeamPregameData:
    """单支球队的赛前数据"""

    # 基本信息
    team_id: int
    team_name: str
    abbreviation: str

    # 战绩排名
    standings: TeamStandings

    # 最近表现
    recent_form: RecentForm

    # 主客场表现
    home_away_splits: HomeAwaySplits

    # 球队统计
    team_stats: TeamStatistics

    # 核心球员
    key_players: List[PlayerBasicStats]

    # 伤病情况（可选）
    injuries: Optional[List[InjuryInfo]] = None

@dataclass
class TeamStandings:
    """球队排名数据"""
    wins: int
    losses: int
    win_pct: float
    conference_rank: int
    division_rank: int
    last_10: str  # "7-3"
    streak: str   # "W3" or "L2"

@dataclass
class RecentForm:
    """最近表现"""
    last_5_games: List[GameSummary]
    avg_points: float
    avg_points_allowed: float
    avg_margin: float  # 场均净胜分

@dataclass
class HomeAwaySplits:
    """主客场数据"""
    is_home: bool
    home_record: str      # "15-5"
    away_record: str      # "12-8"
    home_avg_pts: float
    away_avg_pts: float
    home_win_pct: float
    away_win_pct: float

@dataclass
class TeamStatistics:
    """球队统计数据"""
    # 基础数据
    ppg: float           # 场均得分
    opp_ppg: float       # 场均失分
    fg_pct: float        # 命中率
    fg3_pct: float       # 三分命中率
    ft_pct: float        # 罚球命中率
    rpg: float           # 场均篮板
    apg: float           # 场均助攻
    spg: float           # 场均抢断
    bpg: float           # 场均盖帽
    tpg: float           # 场均失误

    # 高级数据
    off_rating: float    # 进攻效率
    def_rating: float    # 防守效率
    net_rating: float    # 净效率
    pace: float          # 节奏
    ts_pct: float        # 真实命中率

    # 联盟排名
    ppg_rank: Optional[int] = None
    def_rating_rank: Optional[int] = None
```

### 2.3 对阵分析模型

```python
@dataclass
class MatchupAnalysis:
    """对阵分析"""

    # 历史对阵
    head_to_head: HeadToHeadRecord

    # 风格匹配
    style_matchup: StyleMatchup

    # 关键对位
    key_matchups: List[PlayerMatchup]

@dataclass
class HeadToHeadRecord:
    """对阵历史记录"""
    season_record: str        # 本赛季 "2-0"
    last_5_record: str        # 最近5次 "3-2"
    last_meeting: Optional[GameSummary] = None
    avg_margin: float = 0.0   # 平均净胜分

@dataclass
class StyleMatchup:
    """风格匹配分析"""
    pace_advantage: str       # "Home", "Away", "Even"
    offensive_style: str      # "Fast Break", "Half Court"
    defensive_matchup: str    # "Advantage Home", "Even"
    three_point_battle: str   # "Advantage Away"
```

### 2.4 实力对比模型

```python
@dataclass
class StrengthComparison:
    """实力对比"""

    # 整体实力评分（0-100）
    home_overall: float
    away_overall: float

    # 分项对比
    offense_comparison: ComparisonItem
    defense_comparison: ComparisonItem
    rebounding_comparison: ComparisonItem
    shooting_comparison: ComparisonItem

    # 优势方
    overall_advantage: str  # "Home", "Away", "Even"

@dataclass
class ComparisonItem:
    """对比项"""
    category: str
    home_value: float
    away_value: float
    advantage: str  # "Home", "Away", "Even"
    difference: float
```

### 2.5 关键因素模型

```python
@dataclass
class KeyFactors:
    """影响比赛的关键因素"""

    # 主要因素（影响力排序）
    top_factors: List[Factor]

    # 主队优势
    home_advantages: List[str]

    # 客队优势
    away_advantages: List[str]

    # 风险因素
    risk_factors: List[str]

@dataclass
class Factor:
    """单个因素"""
    name: str
    description: str
    impact_level: str  # "High", "Medium", "Low"
    favors: str        # "Home", "Away", "Neutral"
```

---

## 三、数据收集器设计

### 3.1 基础收集器接口

```python
class BaseCollector(ABC):
    """数据收集器基类"""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager
        self.rate_limiter = RateLimiter(delay=0.6)

    @abstractmethod
    def collect(self, **kwargs) -> Any:
        """收集数据的抽象方法"""
        pass

    def _fetch_with_cache(self, key: str, fetch_func: Callable) -> Any:
        """带缓存的数据获取"""
        if self.cache:
            cached = self.cache.get(key)
            if cached:
                return cached

        self.rate_limiter.wait()
        data = fetch_func()

        if self.cache:
            self.cache.set(key, data)

        return data
```

### 3.2 具体收集器

#### 3.2.1 排名收集器

```python
class StandingsCollector(BaseCollector):
    """球队排名收集器"""

    def collect(self, season: str) -> Dict[int, TeamStandings]:
        """
        收集所有球队的排名数据

        Returns:
            {team_id: TeamStandings}
        """
        key = f"standings_{season}"

        def fetch():
            from nba_api.stats.endpoints import leaguestandings
            standings = leaguestandings.LeagueStandings(
                season=season,
                season_type='Regular Season'
            )
            return self._parse_standings(standings)

        return self._fetch_with_cache(key, fetch)

    def _parse_standings(self, standings) -> Dict[int, TeamStandings]:
        """解析排名数据"""
        df = standings.standings.get_data_frame()
        result = {}

        for _, row in df.iterrows():
            team_id = row['TeamID']
            result[team_id] = TeamStandings(
                wins=row['W'],
                losses=row['L'],
                win_pct=row['W_PCT'],
                conference_rank=row['ConferenceRank'],
                division_rank=row['DivisionRank'],
                last_10=row['L10'],
                streak=row['STREAK']
            )

        return result
```

#### 3.2.2 比赛日志收集器

```python
class GameLogCollector(BaseCollector):
    """比赛日志收集器"""

    def collect(self, team_id: int, season: str, last_n: int = 10) -> List[GameSummary]:
        """
        收集球队最近 N 场比赛

        Args:
            team_id: 球队ID
            season: 赛季
            last_n: 最近几场
        """
        key = f"gamelog_{team_id}_{season}"

        def fetch():
            from nba_api.stats.endpoints import teamgamelog
            gamelog = teamgamelog.TeamGameLog(
                team_id=str(team_id),
                season=season,
                season_type_all_star='Regular Season'
            )
            return self._parse_gamelog(gamelog, last_n)

        return self._fetch_with_cache(key, fetch)

    def _parse_gamelog(self, gamelog, last_n: int) -> List[GameSummary]:
        """解析比赛日志"""
        df = gamelog.team_game_log.get_data_frame()
        games = []

        for _, row in df.head(last_n).iterrows():
            games.append(GameSummary(
                game_id=row['Game_ID'],
                game_date=row['GAME_DATE'],
                matchup=row['MATCHUP'],
                result=row['WL'],
                points=row['PTS'],
                opp_points=self._extract_opp_pts(row),
                fg_pct=row['FG_PCT'],
                rebounds=row['REB'],
                assists=row['AST']
            ))

        return games
```

#### 3.2.3 球队统计收集器

```python
class TeamStatsCollector(BaseCollector):
    """球队统计收集器"""

    def collect_basic(self, team_id: int, season: str) -> TeamStatistics:
        """收集基础统计"""
        key = f"team_stats_basic_{team_id}_{season}"

        def fetch():
            from nba_api.stats.endpoints import leaguedashteamstats

            # 基础统计
            basic = leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                measure_type='Base',
                per_mode='PerGame'
            )

            # 高级统计
            advanced = leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                measure_type='Advanced'
            )

            return self._parse_team_stats(team_id, basic, advanced)

        return self._fetch_with_cache(key, fetch)

    def collect_splits(self, team_id: int, season: str) -> HomeAwaySplits:
        """收集主客场统计"""
        key = f"team_splits_{team_id}_{season}"

        def fetch():
            from nba_api.stats.endpoints import teamdashboardbygamesplits
            splits = teamdashboardbygamesplits.TeamDashboardByGameSplits(
                team_id=str(team_id),
                season=season
            )
            return self._parse_splits(splits)

        return self._fetch_with_cache(key, fetch)
```

#### 3.2.4 对阵历史收集器

```python
class MatchupHistoryCollector(BaseCollector):
    """对阵历史收集器"""

    def collect(self, team1_id: int, team2_id: int, season: str) -> HeadToHeadRecord:
        """收集两队对阵历史"""
        key = f"matchup_{team1_id}_{team2_id}_{season}"

        def fetch():
            from nba_api.stats.endpoints import leaguegamefinder

            # 查找 team1 的所有比赛
            games = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=str(team1_id),
                season_nullable=season
            )

            return self._parse_matchup(games, team1_id, team2_id)

        return self._fetch_with_cache(key, fetch)
```

---

## 四、分析器设计

### 4.1 球队状态分析器

```python
class TeamFormAnalyzer:
    """球队状态分析器"""

    def analyze_recent_form(self, games: List[GameSummary]) -> RecentForm:
        """分析最近表现"""
        if not games:
            return None

        total_pts = sum(g.points for g in games)
        total_opp_pts = sum(g.opp_points for g in games)

        return RecentForm(
            last_5_games=games[:5],
            avg_points=total_pts / len(games),
            avg_points_allowed=total_opp_pts / len(games),
            avg_margin=(total_pts - total_opp_pts) / len(games)
        )

    def calculate_momentum(self, games: List[GameSummary]) -> float:
        """
        计算球队势头（0-100）
        考虑因素：
        - 最近战绩
        - 得分趋势
        - 连胜/连败
        """
        if not games:
            return 50.0

        # 最近5场胜率权重 40%
        recent_wins = sum(1 for g in games[:5] if g.result == 'W')
        win_score = (recent_wins / 5) * 40

        # 得分趋势权重 30%
        trend_score = self._calculate_scoring_trend(games) * 30

        # 连胜连败权重 30%
        streak_score = self._calculate_streak_score(games) * 30

        return win_score + trend_score + streak_score
```

### 4.2 对阵分析器

```python
class MatchupAnalyzer:
    """对阵分析器"""

    def analyze(
        self,
        home_team: TeamPregameData,
        away_team: TeamPregameData,
        h2h: HeadToHeadRecord
    ) -> MatchupAnalysis:
        """综合对阵分析"""

        style_matchup = self._analyze_style_matchup(home_team, away_team)

        return MatchupAnalysis(
            head_to_head=h2h,
            style_matchup=style_matchup,
            key_matchups=[]  # 可扩展
        )

    def _analyze_style_matchup(
        self,
        home: TeamPregameData,
        away: TeamPregameData
    ) -> StyleMatchup:
        """分析风格匹配"""

        # 节奏对比
        pace_diff = home.team_stats.pace - away.team_stats.pace
        if abs(pace_diff) < 2:
            pace_adv = "Even"
        else:
            pace_adv = "Home" if pace_diff > 0 else "Away"

        # 进攻风格
        home_pace_rank = "Fast" if home.team_stats.pace > 100 else "Slow"
        away_pace_rank = "Fast" if away.team_stats.pace > 100 else "Slow"

        # 三分球对决
        home_3p = home.team_stats.fg3_pct
        away_3p = away.team_stats.fg3_pct
        three_pt_adv = "Even"
        if abs(home_3p - away_3p) > 0.03:
            three_pt_adv = f"Advantage {'Home' if home_3p > away_3p else 'Away'}"

        return StyleMatchup(
            pace_advantage=pace_adv,
            offensive_style=f"Home: {home_pace_rank}, Away: {away_pace_rank}",
            defensive_matchup=self._compare_defense(home, away),
            three_point_battle=three_pt_adv
        )
```

### 4.3 实力对比分析器

```python
class StrengthComparator:
    """实力对比分析器"""

    def compare(
        self,
        home: TeamPregameData,
        away: TeamPregameData
    ) -> StrengthComparison:
        """综合实力对比"""

        # 各项对比
        offense_cmp = self._compare_offense(home, away)
        defense_cmp = self._compare_defense(home, away)
        rebounding_cmp = self._compare_rebounding(home, away)
        shooting_cmp = self._compare_shooting(home, away)

        # 计算整体评分
        home_overall = self._calculate_overall_score(home)
        away_overall = self._calculate_overall_score(away)

        # 确定优势方
        diff = home_overall - away_overall
        if abs(diff) < 5:
            advantage = "Even"
        else:
            advantage = "Home" if diff > 0 else "Away"

        return StrengthComparison(
            home_overall=home_overall,
            away_overall=away_overall,
            offense_comparison=offense_cmp,
            defense_comparison=defense_cmp,
            rebounding_comparison=rebounding_cmp,
            shooting_comparison=shooting_cmp,
            overall_advantage=advantage
        )

    def _compare_offense(self, home: TeamPregameData, away: TeamPregameData) -> ComparisonItem:
        """对比进攻"""
        home_val = home.team_stats.off_rating
        away_val = away.team_stats.off_rating

        diff = home_val - away_val
        advantage = "Even"
        if abs(diff) > 3:
            advantage = "Home" if diff > 0 else "Away"

        return ComparisonItem(
            category="Offense (OFF_RATING)",
            home_value=home_val,
            away_value=away_val,
            advantage=advantage,
            difference=diff
        )
```

### 4.4 关键因素分析器

```python
class KeyFactorsAnalyzer:
    """关键因素分析器"""

    def analyze(
        self,
        home: TeamPregameData,
        away: TeamPregameData,
        matchup: MatchupAnalysis,
        comparison: StrengthComparison
    ) -> KeyFactors:
        """识别关键因素"""

        factors = []
        home_advantages = []
        away_advantages = []
        risk_factors = []

        # 1. 主场优势
        if home.home_away_splits.home_win_pct - home.home_away_splits.away_win_pct > 0.15:
            factors.append(Factor(
                name="Strong Home Court Advantage",
                description=f"{home.team_name} has {home.home_away_splits.home_win_pct:.1%} win rate at home",
                impact_level="High",
                favors="Home"
            ))
            home_advantages.append("Strong home court record")

        # 2. 最近势头
        home_momentum = self._calculate_momentum(home.recent_form)
        away_momentum = self._calculate_momentum(away.recent_form)

        if abs(home_momentum - away_momentum) > 20:
            favors = "Home" if home_momentum > away_momentum else "Away"
            factors.append(Factor(
                name="Momentum Difference",
                description=f"Significant momentum gap: {abs(home_momentum - away_momentum):.0f} points",
                impact_level="Medium",
                favors=favors
            ))

        # 3. 对阵历史
        if matchup.head_to_head.season_record:
            h2h_wins, h2h_total = self._parse_record(matchup.head_to_head.season_record)
            if h2h_total >= 2 and (h2h_wins == h2h_total or h2h_wins == 0):
                factors.append(Factor(
                    name="Head-to-Head Dominance",
                    description=f"One team is {matchup.head_to_head.season_record} this season",
                    impact_level="Medium",
                    favors="Home" if h2h_wins == h2h_total else "Away"
                ))

        # 4. 实力差距
        overall_diff = abs(comparison.home_overall - comparison.away_overall)
        if overall_diff > 10:
            factors.append(Factor(
                name="Significant Talent Gap",
                description=f"Overall rating difference: {overall_diff:.1f} points",
                impact_level="High",
                favors="Home" if comparison.home_overall > comparison.away_overall else "Away"
            ))

        # 5. 风格匹配
        if matchup.style_matchup.pace_advantage != "Even":
            factors.append(Factor(
                name="Pace Advantage",
                description=f"Pace favors {matchup.style_matchup.pace_advantage} team",
                impact_level="Low",
                favors=matchup.style_matchup.pace_advantage
            ))

        # 按影响力排序
        impact_order = {"High": 3, "Medium": 2, "Low": 1}
        factors.sort(key=lambda f: impact_order[f.impact_level], reverse=True)

        return KeyFactors(
            top_factors=factors[:5],
            home_advantages=home_advantages,
            away_advantages=away_advantages,
            risk_factors=risk_factors
        )
```

---

## 五、主控制器设计

```python
class PregameController:
    """赛前分析主控制器"""

    def __init__(self, cache_ttl: int = 3600):
        """
        Args:
            cache_ttl: 缓存有效期（秒），默认1小时
        """
        # 初始化缓存
        self.cache = CacheManager(ttl=cache_ttl)

        # 初始化收集器
        self.standings_collector = StandingsCollector(self.cache)
        self.gamelog_collector = GameLogCollector(self.cache)
        self.team_stats_collector = TeamStatsCollector(self.cache)
        self.matchup_collector = MatchupHistoryCollector(self.cache)

        # 初始化分析器
        self.form_analyzer = TeamFormAnalyzer()
        self.matchup_analyzer = MatchupAnalyzer()
        self.strength_comparator = StrengthComparator()
        self.factors_analyzer = KeyFactorsAnalyzer()

    def analyze_from_url(
        self,
        url: str,
        season: str = "2025-26",
        depth: str = "full",
        verbose: bool = True
    ) -> PregameReport:
        """
        从 Polymarket URL 生成赛前分析报告

        Args:
            url: Polymarket 事件 URL
            season: 赛季
            depth: 分析深度 ("basic", "standard", "full")
            verbose: 是否打印详细日志

        Returns:
            完整的赛前分析报告
        """
        if verbose:
            print(f"开始赛前分析...")
            print(f"URL: {url}")

        # 1. 解析 URL
        from ..parsers import parse_polymarket_url
        event_info = parse_polymarket_url(url)
        if not event_info:
            raise ValueError("URL 解析失败")

        if verbose:
            print(f"✓ 解析成功: {event_info.team1_abbr} vs {event_info.team2_abbr}")

        # 2. 获取球队信息
        from ..nba import get_team_info
        team1 = get_team_info(event_info.team1_abbr)
        team2 = get_team_info(event_info.team2_abbr)

        if not team1 or not team2:
            raise ValueError("球队信息获取失败")

        # 3. 收集数据
        if verbose:
            print(f"\n收集数据...")

        team1_data = self._collect_team_data(team1.id, team1, season, verbose)
        team2_data = self._collect_team_data(team2.id, team2, season, verbose)

        # 4. 确定主客场
        # 简化处理：根据 URL 中的顺序，第二个为主队
        home_data = team2_data
        away_data = team1_data

        # 5. 收集对阵历史
        if verbose:
            print(f"\n分析对阵历史...")

        h2h = self.matchup_collector.collect(team1.id, team2.id, season)

        # 6. 执行分析
        if verbose:
            print(f"\n执行分析...")

        matchup_analysis = self.matchup_analyzer.analyze(home_data, away_data, h2h)
        strength_comparison = self.strength_comparator.compare(home_data, away_data)
        key_factors = self.factors_analyzer.analyze(
            home_data, away_data, matchup_analysis, strength_comparison
        )

        # 7. 生成报告
        report = PregameReport(
            game_info=GameBasicInfo(
                game_date=event_info.game_date,
                home_team=home_data.team_name,
                away_team=away_data.team_name,
                url=url
            ),
            home_team=home_data,
            away_team=away_data,
            matchup_analysis=matchup_analysis,
            strength_comparison=strength_comparison,
            key_factors=key_factors
        )

        if verbose:
            print(f"\n✓ 分析完成")

        return report

    def _collect_team_data(
        self,
        team_id: int,
        team_info: 'TeamInfo',
        season: str,
        verbose: bool
    ) -> TeamPregameData:
        """收集单支球队的所有数据"""

        if verbose:
            print(f"  - {team_info.full_name}")

        # 排名
        all_standings = self.standings_collector.collect(season)
        standings = all_standings.get(team_id)

        # 比赛日志
        games = self.gamelog_collector.collect(team_id, season, last_n=10)
        recent_form = self.form_analyzer.analyze_recent_form(games)

        # 球队统计
        team_stats = self.team_stats_collector.collect_basic(team_id, season)
        splits = self.team_stats_collector.collect_splits(team_id, season)

        return TeamPregameData(
            team_id=team_id,
            team_name=team_info.full_name,
            abbreviation=team_info.abbreviation,
            standings=standings,
            recent_form=recent_form,
            home_away_splits=splits,
            team_stats=team_stats,
            key_players=[]  # 可扩展
        )
```

---

## 六、缓存管理设计

```python
class CacheManager:
    """缓存管理器"""

    def __init__(self, ttl: int = 3600, cache_dir: str = ".cache"):
        """
        Args:
            ttl: 缓存有效期（秒）
            cache_dir: 缓存目录
        """
        self.ttl = ttl
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # 内存缓存
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        # 1. 检查内存缓存
        if key in self._memory_cache:
            data, timestamp = self._memory_cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self._memory_cache[key]

        # 2. 检查文件缓存
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            file_age = time.time() - cache_file.stat().st_mtime
            if file_age < self.ttl:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    # 加载到内存
                    self._memory_cache[key] = (data, cache_file.stat().st_mtime)
                    return data

        return None

    def set(self, key: str, data: Any):
        """设置缓存"""
        timestamp = time.time()

        # 1. 写入内存
        self._memory_cache[key] = (data, timestamp)

        # 2. 写入文件
        cache_file = self.cache_dir / f"{key}.pkl"
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)

    def clear(self):
        """清空缓存"""
        self._memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
```

---

## 七、使用示例

### 7.1 基本使用

```python
from pm_nba_agent.pregame import PregameController

# 创建控制器
controller = PregameController(cache_ttl=3600)

# 从 URL 生成报告
url = "https://polymarket.com/event/nba-por-was-2026-01-27"
report = controller.analyze_from_url(url, season="2025-26", verbose=True)

# 打印报告
print("\n" + "="*60)
print("赛前分析报告")
print("="*60)
print(f"\n{report.away_team.team_name} @ {report.home_team.team_name}")
print(f"日期: {report.game_info.game_date}")

print("\n【球队战绩】")
print(f"{report.home_team.abbreviation}: {report.home_team.standings.wins}-{report.home_team.standings.losses} (排名: {report.home_team.standings.conference_rank})")
print(f"{report.away_team.abbreviation}: {report.away_team.standings.wins}-{report.away_team.standings.losses} (排名: {report.away_team.standings.conference_rank})")

print("\n【实力对比】")
print(f"整体优势: {report.strength_comparison.overall_advantage}")
print(f"主队评分: {report.strength_comparison.home_overall:.1f}")
print(f"客队评分: {report.strength_comparison.away_overall:.1f}")

print("\n【关键因素】")
for i, factor in enumerate(report.key_factors.top_factors, 1):
    print(f"{i}. {factor.name} ({factor.impact_level})")
    print(f"   {factor.description}")
    print(f"   有利于: {factor.favors}")
```

### 7.2 导出为 JSON

```python
# 转换为字典
report_dict = report.to_dict()

# 保存为 JSON
import json
with open('pregame_report.json', 'w', encoding='utf-8') as f:
    json.dump(report_dict, f, indent=2, ensure_ascii=False)
```

### 7.3 与赛中数据结合

```python
from pm_nba_agent.main import get_game_data_from_url
from pm_nba_agent.pregame import PregameController

url = "https://polymarket.com/event/nba-por-was-2026-01-27"

# 赛前分析
pregame_controller = PregameController()
pregame_report = pregame_controller.analyze_from_url(url)

# 赛中数据
live_data = get_game_data_from_url(url, verbose=False)

# 对比分析
if live_data:
    print("\n预测 vs 实际:")
    print(f"主队预测评分: {pregame_report.strength_comparison.home_overall:.1f}")
    print(f"主队实际得分: {live_data.home_team.score}")
```

---

## 八、实施计划

### 阶段 1: 基础架构（1-2天）
- [ ] 创建目录结构
- [ ] 实现基础数据模型
- [ ] 实现缓存管理器
- [ ] 实现限流器

### 阶段 2: 数据收集（2-3天）
- [ ] 实现 StandingsCollector
- [ ] 实现 GameLogCollector
- [ ] 实现 TeamStatsCollector
- [ ] 实现 MatchupHistoryCollector
- [ ] 添加错误处理和重试机制

### 阶段 3: 数据分析（2-3天）
- [ ] 实现 TeamFormAnalyzer
- [ ] 实现 MatchupAnalyzer
- [ ] 实现 StrengthComparator
- [ ] 实现 KeyFactorsAnalyzer

### 阶段 4: 主控制器（1天）
- [ ] 实现 PregameController
- [ ] 整合所有模块
- [ ] 添加完整的错误处理

### 阶段 5: 测试与优化（2天）
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 性能优化
- [ ] 文档完善

### 阶段 6: 示例与文档（1天）
- [ ] 创建使用示例
- [ ] 编写 API 文档
- [ ] 更新 README

---

## 九、技术要点

### 9.1 API 限流

```python
class RateLimiter:
    """API 限流器"""

    def __init__(self, delay: float = 0.6):
        self.delay = delay
        self.last_call = 0

    def wait(self):
        """等待以满足限流要求"""
        elapsed = time.time() - self.last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call = time.time()
```

### 9.2 错误处理

```python
def safe_api_call(func: Callable, max_retries: int = 3) -> Any:
    """安全的 API 调用，带重试机制"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"API 调用失败，重试 {attempt + 1}/{max_retries}: {e}")
            time.sleep(2 ** attempt)  # 指数退避
```

### 9.3 数据验证

```python
def validate_season(season: str) -> bool:
    """验证赛季格式"""
    pattern = r'^\d{4}-\d{2}$'
    return bool(re.match(pattern, season))

def validate_team_id(team_id: int) -> bool:
    """验证球队ID"""
    return 1610612737 <= team_id <= 1610612766
```

---

## 十、扩展方向

### 10.1 短期扩展
- 添加球员伤病数据（从外部API）
- 添加裁判历史数据
- 添加投注赔率分析
- 支持季后赛分析

### 10.2 长期扩展
- 机器学习预测模型
- 实时数据更新（WebSocket）
- 可视化仪表板
- 移动端 API

---

## 十一、性能指标

### 11.1 目标性能
- 单次分析完成时间: < 10秒（无缓存）
- 单次分析完成时间: < 2秒（有缓存）
- 内存占用: < 200MB
- 缓存命中率: > 80%

### 11.2 监控指标
- API 调用次数
- 缓存命中率
- 平均响应时间
- 错误率

---

## 十二、总结

这个设计方案提供了：

1. **清晰的架构**：分层设计，职责明确
2. **可扩展性**：模块化设计，易于添加新功能
3. **性能优化**：缓存机制，减少 API 调用
4. **容错能力**：完善的错误处理和重试机制
5. **易用性**：简单的 API 接口

实施后，可以为 Polymarket NBA 事件提供全面的赛前分析，帮助用户做出更好的预测决策。
