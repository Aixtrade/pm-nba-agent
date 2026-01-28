"""比赛上下文管理器"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
import time

from .models import SignificantEvent


@dataclass
class GameContext:
    """比赛上下文，保存三种事件的最新数据"""
    game_id: str
    scoreboard: Optional[dict] = None
    boxscore: Optional[dict] = None
    playbyplay: list[dict] = field(default_factory=list)

    # 更新时间戳
    scoreboard_updated_at: Optional[float] = None
    boxscore_updated_at: Optional[float] = None
    playbyplay_updated_at: Optional[float] = None

    # 分析状态
    last_analysis_at: Optional[float] = None
    analysis_round: int = 0

    # 重要事件
    significant_events: list[SignificantEvent] = field(default_factory=list)

    # 上次比分记录（用于检测比分变化）
    _last_home_score: int = 0
    _last_away_score: int = 0
    _last_period: int = 0

    def update_scoreboard(self, data: dict) -> None:
        """更新比分板数据"""
        now = time.time()

        # 检测重要事件
        if self.scoreboard is not None:
            self._detect_scoreboard_events(data, now)

        self.scoreboard = data
        self.scoreboard_updated_at = now

        # 更新比分记录
        home_team = data.get('home_team', {})
        away_team = data.get('away_team', {})
        self._last_home_score = home_team.get('score', 0)
        self._last_away_score = away_team.get('score', 0)
        self._last_period = data.get('period', 0)

    def update_boxscore(self, data: dict) -> None:
        """更新详细统计数据"""
        self.boxscore = data
        self.boxscore_updated_at = time.time()

    def update_playbyplay(self, actions: list[dict]) -> None:
        """更新逐回合数据（追加新事件）"""
        now = time.time()

        # 检测重要得分事件
        for action in actions:
            self._detect_play_events(action, now)

        self.playbyplay.extend(actions)
        self.playbyplay_updated_at = now

        # 保持最近 100 条记录
        if len(self.playbyplay) > 100:
            self.playbyplay = self.playbyplay[-100:]

    def _detect_scoreboard_events(self, new_data: dict, timestamp: float) -> None:
        """检测比分板相关的重要事件"""
        home_team = new_data.get('home_team', {})
        away_team = new_data.get('away_team', {})
        new_home_score = home_team.get('score', 0)
        new_away_score = away_team.get('score', 0)
        new_period = new_data.get('period', 0)

        # 检测大比分变化（单次 5 分以上）
        home_diff = new_home_score - self._last_home_score
        away_diff = new_away_score - self._last_away_score

        if home_diff >= 5 or away_diff >= 5:
            team_name = home_team.get('name') if home_diff > away_diff else away_team.get('name')
            self.significant_events.append(SignificantEvent(
                event_type="big_score_run",
                description=f"{team_name} 打出一波得分潮",
                timestamp=timestamp,
                data={"home_diff": home_diff, "away_diff": away_diff}
            ))

        # 检测领先交换
        old_lead = self._last_home_score - self._last_away_score
        new_lead = new_home_score - new_away_score
        if (old_lead > 0 and new_lead < 0) or (old_lead < 0 and new_lead > 0):
            leader = home_team.get('name') if new_lead > 0 else away_team.get('name')
            self.significant_events.append(SignificantEvent(
                event_type="lead_change",
                description=f"{leader} 反超取得领先",
                timestamp=timestamp,
                data={"new_lead": abs(new_lead)}
            ))

        # 检测节次变化
        if new_period > self._last_period and self._last_period > 0:
            self.significant_events.append(SignificantEvent(
                event_type="period_change",
                description=f"进入第 {new_period} 节",
                timestamp=timestamp,
                data={"period": new_period}
            ))

    def _detect_play_events(self, action: dict, timestamp: float) -> None:
        """检测逐回合中的重要事件"""
        action_type = action.get('action_type', '').lower()
        description = action.get('description', '')

        # 检测三分球
        if 'three' in action_type.lower() or '3pt' in description.lower():
            if 'made' in action_type.lower() or 'makes' in description.lower():
                self.significant_events.append(SignificantEvent(
                    event_type="three_pointer",
                    description=description,
                    timestamp=timestamp,
                    data=action
                ))

        # 检测扣篮
        if 'dunk' in action_type.lower() or 'dunk' in description.lower():
            self.significant_events.append(SignificantEvent(
                event_type="dunk",
                description=description,
                timestamp=timestamp,
                data=action
            ))

    def has_significant_event_since(self, seconds: float) -> bool:
        """检查指定时间内是否有重要事件"""
        if not self.significant_events:
            return False

        cutoff = time.time() - seconds
        return any(e.timestamp > cutoff for e in self.significant_events)

    def should_analyze(
        self,
        normal_interval: float = 30.0,
        event_interval: float = 15.0
    ) -> bool:
        """判断是否应该触发分析"""
        now = time.time()

        # 如果从未分析过，且有数据，则分析
        if self.last_analysis_at is None:
            return self.scoreboard is not None or self.boxscore is not None

        time_since_analysis = now - self.last_analysis_at

        # 有重要事件时使用较短间隔
        if self.has_significant_event_since(event_interval):
            return time_since_analysis >= event_interval

        # 正常间隔
        return time_since_analysis >= normal_interval

    def mark_analyzed(self) -> None:
        """标记已分析"""
        self.mark_analysis_attempted(success=True)

    def mark_analysis_attempted(self, success: bool) -> None:
        """标记分析尝试"""
        self.last_analysis_at = time.time()
        if success:
            self.analysis_round += 1
            # 清空重要事件（已被分析过）
            self.significant_events = []

    def get_recent_plays(self, limit: int = 10) -> list[dict]:
        """获取最近的比赛事件"""
        return self.playbyplay[-limit:] if self.playbyplay else []

    def to_prompt_context(self) -> dict:
        """转换为 Prompt 友好格式"""
        result = {
            "game_id": self.game_id,
            "analysis_round": self.analysis_round + 1,
        }

        # 比分板信息
        if self.scoreboard:
            result["scoreboard"] = {
                "status": self.scoreboard.get("status", "Unknown"),
                "period": self.scoreboard.get("period", 0),
                "game_clock": self.scoreboard.get("game_clock", ""),
                "home_team": self.scoreboard.get("home_team", {}),
                "away_team": self.scoreboard.get("away_team", {}),
            }

        # 详细统计
        if self.boxscore:
            teams = self.boxscore.get("teams", {})
            result["team_stats"] = {
                "home": teams.get("home", {}),
                "away": teams.get("away", {}),
            }

            # 提取关键球员
            players = self.boxscore.get("players", [])
            top_scorers = sorted(
                players,
                key=lambda p: p.get("stats", {}).get("points", 0),
                reverse=True
            )[:5]
            result["top_performers"] = [
                {
                    "name": p.get("name"),
                    "team": p.get("team"),
                    "points": p.get("stats", {}).get("points", 0),
                    "rebounds": p.get("stats", {}).get("rebounds", 0),
                    "assists": p.get("stats", {}).get("assists", 0),
                }
                for p in top_scorers
            ]

        # 最近比赛事件
        result["recent_plays"] = self.get_recent_plays(10)

        # 重要事件
        result["significant_events"] = [
            {"type": e.event_type, "description": e.description}
            for e in self.significant_events[-5:]
        ]

        return result
