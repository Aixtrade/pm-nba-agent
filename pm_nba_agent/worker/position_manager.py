"""持仓管理"""

import asyncio
import time
from typing import Any, Callable, Optional

from loguru import logger

from pm_nba_agent.polymarket.models import PositionContext
from pm_nba_agent.polymarket.positions import get_current_positions

from .event_bus import EventPublisher
from .market_state import MarketState
from .sse_utils import now_iso, seconds_since_iso


class PositionManager:
    """持仓数据管理：定时刷新 + 策略回调。"""

    def __init__(
        self,
        task_id: str,
        market_state: MarketState,
        publisher: EventPublisher,
        config_provider: Callable[[], Any],
    ) -> None:
        self.task_id = task_id
        self.market_state = market_state
        self.publisher = publisher
        self._config_provider = config_provider

        self.sides: list[dict[str, Any]] = []
        self.loading = False
        self.updated_at: Optional[str] = None

        self._refresh_lock = asyncio.Lock()
        self._last_refresh_at = 0.0
        self._initial_refresh_done = False

    @property
    def _config(self) -> Any:
        return self._config_provider()

    async def publish_state(self) -> None:
        payload = {
            "sides": self.sides,
            "loading": self.loading,
            "updated_at": self.updated_at,
            "condition_id": self.market_state.condition_id,
            "timestamp": now_iso(),
        }
        await self.publisher.publish("position_state", payload)

    async def start_refresh_loop(self, cancelled_fn: Callable[[], bool]) -> None:
        while not cancelled_fn():
            config = self._config
            auto_sell = config.auto_sell if isinstance(config.auto_sell, dict) else {}
            default_cfg = auto_sell.get("default", {}) if isinstance(auto_sell.get("default"), dict) else {}
            refresh_interval = float(default_cfg.get("refresh_interval", 3.0))
            refresh_interval = max(1.0, min(refresh_interval, 60.0))
            should_refresh = bool(
                auto_sell.get("enabled", False)
                and self.market_state.condition_id
                and config.proxy_address
            )

            if should_refresh:
                await self.refresh_once()

            await asyncio.sleep(refresh_interval)

    async def refresh_once(self, force: bool = False) -> None:
        if not force and not self._should_refresh_now():
            return

        if self._refresh_lock.locked():
            return

        async with self._refresh_lock:
            self._last_refresh_at = time.monotonic()
            await self._refresh()

    def mark_initial_done(self) -> None:
        self._initial_refresh_done = True

    @property
    def initial_refresh_done(self) -> bool:
        return self._initial_refresh_done

    def _should_refresh_now(self) -> bool:
        interval = self._get_refresh_interval()
        min_gap = max(0.8, min(interval * 0.6, 5.0))
        return (time.monotonic() - self._last_refresh_at) >= min_gap

    def _get_refresh_interval(self) -> float:
        config = self._config
        auto_sell = config.auto_sell if isinstance(config.auto_sell, dict) else {}
        default_cfg = auto_sell.get("default") if isinstance(auto_sell.get("default"), dict) else {}
        refresh_interval = float(default_cfg.get("refresh_interval", 3.0)) if default_cfg else 3.0
        return max(1.0, min(refresh_interval, 60.0))

    async def _refresh(self) -> None:
        if not self.market_state.condition_id:
            return
        config = self._config
        if not config.proxy_address:
            return

        self.loading = True
        await self.publish_state()

        try:
            positions = await get_current_positions(
                user_address=config.proxy_address,
                condition_ids=[self.market_state.condition_id],
                proxy_address=config.proxy_address,
            )
            if not isinstance(positions, list):
                return

            sides = build_position_sides(positions, self.market_state.outcomes)
            self.sides = sides
            self.updated_at = now_iso()
        except Exception as exc:
            logger.error("刷新持仓失败 task={}: {}", self.task_id, exc)
        finally:
            self.loading = False
            await self.publish_state()

    def is_stale(self, max_stale_seconds: float) -> bool:
        if not self.updated_at:
            return True
        return seconds_since_iso(self.updated_at) > max_stale_seconds

    def find_side(self, outcome: str) -> Optional[dict[str, Any]]:
        for side in self.sides:
            if str(side.get("outcome") or "") == outcome:
                return side
        return None

    async def get_position_context(
        self,
        yes_token_id: str,
        no_token_id: str,
        max_stale_seconds: float,
    ) -> Optional[PositionContext]:
        if not yes_token_id or not no_token_id:
            return None

        stale_limit = max(1.0, float(max_stale_seconds))
        if self.updated_at is None or self.is_stale(stale_limit):
            await self.refresh_once()

        yes_outcome = self.market_state.outcome_by_token.get(yes_token_id)
        no_outcome = self.market_state.outcome_by_token.get(no_token_id)
        if not yes_outcome or not no_outcome:
            return PositionContext()

        yes_side = self.find_side(yes_outcome)
        no_side = self.find_side(no_outcome)

        yes_size = float(yes_side.get("size", 0.0)) if yes_side else 0.0
        no_size = float(no_side.get("size", 0.0)) if no_side else 0.0
        yes_avg = float(yes_side.get("avg_price", 0.0) or 0.0) if yes_side else 0.0
        no_avg = float(no_side.get("avg_price", 0.0) or 0.0) if no_side else 0.0

        yes_initial = float(yes_side.get("initial_value", 0.0) or 0.0) if yes_side else 0.0
        no_initial = float(no_side.get("initial_value", 0.0) or 0.0) if no_side else 0.0

        yes_total_cost = yes_initial if yes_initial > 0 else yes_size * yes_avg
        no_total_cost = no_initial if no_initial > 0 else no_size * no_avg

        return PositionContext(
            yes_size=yes_size,
            no_size=no_size,
            yes_avg_cost=yes_avg,
            no_avg_cost=no_avg,
            yes_total_cost=yes_total_cost,
            no_total_cost=no_total_cost,
        )


def build_position_sides(positions: list[dict[str, Any]], outcomes: list[str] | None) -> list[dict[str, Any]]:
    sizes: dict[str, float] = {}
    initial_values: dict[str, float] = {}
    avg_prices: dict[str, float | None] = {}
    cur_prices: dict[str, float | None] = {}

    for position in positions:
        outcome = str(position.get("outcome") or "").strip()
        if outcome:
            size_value = position.get("size", 0)
            try:
                size = float(size_value)
            except (TypeError, ValueError):
                size = 0.0
            sizes[outcome] = sizes.get(outcome, 0.0) + size

            initial_value = position.get("initialValue", 0)
            try:
                cost = float(initial_value)
            except (TypeError, ValueError):
                cost = 0.0
            initial_values[outcome] = initial_values.get(outcome, 0.0) + cost

            if outcome not in avg_prices:
                avg_value = position.get("avgPrice")
                if avg_value is not None:
                    try:
                        avg_prices[outcome] = float(avg_value)
                    except (TypeError, ValueError):
                        avg_prices[outcome] = None

            if outcome not in cur_prices:
                cur_value = position.get("curPrice")
                if cur_value is not None:
                    try:
                        cur_prices[outcome] = float(cur_value)
                    except (TypeError, ValueError):
                        cur_prices[outcome] = None

        opposite_outcome = str(position.get("oppositeOutcome") or "").strip()
        if opposite_outcome and opposite_outcome not in sizes:
            sizes[opposite_outcome] = 0.0
            initial_values[opposite_outcome] = 0.0

    if outcomes:
        for outcome in outcomes:
            if outcome not in sizes:
                sizes[outcome] = 0.0
            if outcome not in initial_values:
                initial_values[outcome] = 0.0

    ordered_outcomes = outcomes or list(sizes.keys())
    return [
        {
            "outcome": outcome,
            "size": sizes.get(outcome, 0.0),
            "initial_value": initial_values.get(outcome, 0.0),
            "avg_price": avg_prices.get(outcome),
            "cur_price": cur_prices.get(outcome),
        }
        for outcome in ordered_outcomes
    ]
