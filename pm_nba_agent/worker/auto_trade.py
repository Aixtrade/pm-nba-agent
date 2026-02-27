"""规则引擎 + AutoTrade 处理器"""

import asyncio
import copy
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from loguru import logger

from .event_bus import EventPublisher
from .market_state import BOTH_SIDE, MarketState
from .order_executor import OrderExecutor, OrderRequest
from .sse_utils import calculate_size, now_iso


@dataclass
class OrderIntent:
    rule_id: str
    rule_type: str
    token_id: str
    side: str
    price: float
    size: float
    outcome: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleRuntimeState:
    last_trigger_at: float = 0.0
    last_order_at: float = 0.0
    order_count: int = 0
    total_spent: float = 0.0
    next_run_at: float = 0.0


class RiskGate:
    """统一风控与去重入口（MVP 使用内存去重）"""

    def __init__(self) -> None:
        self._recent_keys: dict[str, float] = {}

    def allow(self, *, dedupe_key: str, dedupe_ttl_sec: float = 3.0) -> bool:
        now = time.time()
        last = self._recent_keys.get(dedupe_key, 0.0)
        if now - last < dedupe_ttl_sec:
            return False
        self._recent_keys[dedupe_key] = now
        return True

    @staticmethod
    def check_basic(intent: OrderIntent, min_order_amount: float) -> tuple[bool, Optional[str]]:
        if intent.price <= 0 or intent.price >= 1:
            return False, "价格非法"
        if intent.size <= 0:
            return False, "份数非法"
        amount = intent.price * intent.size
        if amount < min_order_amount:
            return False, f"下单金额过小: {amount:.4f} < {min_order_amount}"
        return True, None


class RuleEngine:
    """规则调度器：产出下单意图，由 AutoTradeHandler 统一执行。"""

    def __init__(
        self,
        config_provider: Callable[[], Any],
        market_state: MarketState,
    ) -> None:
        self._config_provider = config_provider
        self.market_state = market_state
        self.runtime: dict[str, RuleRuntimeState] = {}
        self.risk_gate = RiskGate()

    def get_runtime_snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            rule_id: {
                "last_trigger_at": state.last_trigger_at,
                "last_order_at": state.last_order_at,
                "order_count": state.order_count,
                "total_spent": state.total_spent,
                "next_run_at": state.next_run_at,
            }
            for rule_id, state in self.runtime.items()
        }

    def _get_rules(self) -> list[dict[str, Any]]:
        config = self._config_provider()
        auto_trade = config.auto_trade if isinstance(config.auto_trade, dict) else {}
        if not auto_trade.get("enabled", False):
            return []
        rules = auto_trade.get("rules")
        if not isinstance(rules, list):
            return []
        valid = [r for r in rules if isinstance(r, dict) and r.get("enabled", True)]
        return sorted(valid, key=lambda r: int(r.get("priority", 1000)))

    def _state(self, rule_id: str) -> RuleRuntimeState:
        if rule_id not in self.runtime:
            self.runtime[rule_id] = RuleRuntimeState()
        return self.runtime[rule_id]

    def on_book_update(self) -> list[OrderIntent]:
        intents: list[OrderIntent] = []
        for rule in self._get_rules():
            rule_type = str(rule.get("type", "")).strip()
            if rule_type == "condition_buy":
                intent = self._eval_condition_buy(rule)
                if intent:
                    intents.append(intent)
        return intents

    def on_strategy_signal(self, payload: dict[str, Any]) -> list[OrderIntent]:
        intents: list[OrderIntent] = []
        for rule in self._get_rules():
            rule_type = str(rule.get("type", "")).strip()
            if rule_type == "signal_buy":
                intents.extend(self._eval_signal_buy(rule, payload))
        return intents

    def on_tick(self) -> list[OrderIntent]:
        intents: list[OrderIntent] = []
        for rule in self._get_rules():
            rule_type = str(rule.get("type", "")).strip()
            if rule_type == "periodic_buy":
                intent = self._eval_periodic_buy(rule)
                if intent:
                    intents.append(intent)
        return intents

    def on_config_updated(self, old_auto_trade: dict[str, Any], new_auto_trade: dict[str, Any]) -> None:
        old_enabled_map = self._build_enabled_rule_map(old_auto_trade)
        new_enabled_map = self._build_enabled_rule_map(new_auto_trade)

        for rule_id in list(self.runtime.keys()):
            if rule_id not in new_enabled_map or not new_enabled_map[rule_id]:
                self.runtime.pop(rule_id, None)

        for rule_id, is_enabled in new_enabled_map.items():
            if is_enabled and not old_enabled_map.get(rule_id, False):
                self.runtime[rule_id] = RuleRuntimeState()

    @staticmethod
    def _build_enabled_rule_map(auto_trade: dict[str, Any]) -> dict[str, bool]:
        if not isinstance(auto_trade, dict):
            return {}
        rules = auto_trade.get("rules")
        if not isinstance(rules, list):
            return {}

        enabled_map: dict[str, bool] = {}
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            rule_id = str(rule.get("id", "")).strip() or f"rule_{index + 1}"
            enabled_map[rule_id] = bool(rule.get("enabled", True))
        return enabled_map

    def _eval_signal_buy(self, rule: dict[str, Any], payload: dict[str, Any]) -> list[OrderIntent]:
        signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
        strategy = payload.get("strategy") if isinstance(payload.get("strategy"), dict) else {}
        signal_type = str(signal.get("type", "")).upper()
        strategy_id = str(strategy.get("id", "")).strip()

        scope = rule.get("scope") if isinstance(rule.get("scope"), dict) else {}
        target_strategy = str(scope.get("strategy_id", "")).strip()
        target_outcome = str(scope.get("outcome", BOTH_SIDE)).strip() or BOTH_SIDE

        cfg = rule.get("config") if isinstance(rule.get("config"), dict) else {}
        signal_types = cfg.get("signal_types") if isinstance(cfg.get("signal_types"), list) else ["BUY"]
        allowed = {str(item).upper() for item in signal_types}
        if allowed and signal_type not in allowed:
            return []
        if target_strategy and strategy_id != target_strategy:
            return []

        amount = float(cfg.get("amount", 10.0))
        round_size = bool(cfg.get("round_size", False))
        rule_id = str(rule.get("id", "signal_buy"))

        outcomes = self.market_state.resolve_outcomes(target_outcome)
        intents: list[OrderIntent] = []
        for outcome in outcomes:
            token_id = self.market_state.token_by_outcome.get(outcome)
            best_ask = self.market_state.best_ask_by_token.get(token_id or "")
            if not token_id or best_ask is None:
                continue
            size = calculate_size(amount, best_ask, round_size)
            if size <= 0:
                continue
            intents.append(OrderIntent(
                rule_id=rule_id,
                rule_type="signal_buy",
                token_id=token_id,
                side="BUY",
                price=best_ask,
                size=size,
                outcome=outcome,
                metadata={
                    "strategy_id": strategy_id,
                    "order_type": str(cfg.get("order_type", "GTC")),
                },
            ))
        return intents

    def _eval_condition_buy(self, rule: dict[str, Any]) -> Optional[OrderIntent]:
        rule_id = str(rule.get("id", "condition_buy"))
        state = self._state(rule_id)
        now = time.time()

        cooldown = float(rule.get("cooldown_seconds", 0.0))
        if cooldown > 0 and now - state.last_order_at < cooldown:
            return None

        scope = rule.get("scope") if isinstance(rule.get("scope"), dict) else {}
        target_outcome = str(scope.get("outcome", BOTH_SIDE)).strip() or BOTH_SIDE
        outcomes = self.market_state.resolve_outcomes(target_outcome)
        if not outcomes:
            return None

        cfg = rule.get("config") if isinstance(rule.get("config"), dict) else {}
        trigger = float(cfg.get("trigger_price_lte", 0.45))
        budget = float(cfg.get("budget_usdc", 10.0))

        for outcome in outcomes:
            token_id = self.market_state.token_by_outcome.get(outcome)
            ask = self.market_state.best_ask_by_token.get(token_id or "")
            if not token_id or ask is None:
                continue
            if ask > trigger:
                continue
            size = float(int((budget / ask) * 100) / 100)
            if size <= 0:
                continue
            return OrderIntent(
                rule_id=rule_id,
                rule_type="condition_buy",
                token_id=token_id,
                side="BUY",
                price=ask,
                size=size,
                outcome=outcome,
                metadata={
                    "trigger_price_lte": trigger,
                    "budget_usdc": budget,
                    "order_type": str(cfg.get("order_type", "GTC")),
                },
            )

        return None

    def _eval_periodic_buy(self, rule: dict[str, Any]) -> Optional[OrderIntent]:
        rule_id = str(rule.get("id", "periodic_buy"))
        state = self._state(rule_id)
        now = time.time()

        scope = rule.get("scope") if isinstance(rule.get("scope"), dict) else {}
        target_outcome = str(scope.get("outcome", BOTH_SIDE)).strip() or BOTH_SIDE
        outcomes = self.market_state.resolve_outcomes(target_outcome)
        if not outcomes:
            return None

        cfg = rule.get("config") if isinstance(rule.get("config"), dict) else {}
        interval = max(5, int(cfg.get("interval_seconds", 120)))
        budget = float(cfg.get("budget_usdc", 10.0))
        max_total = max(0.0, float(cfg.get("max_total_budget", 0.0)))

        last_run_at = max(state.last_trigger_at, state.last_order_at)
        if last_run_at > 0 and now - last_run_at < interval:
            state.next_run_at = last_run_at + interval
            return None

        if max_total > 0 and state.total_spent >= max_total:
            return None

        for outcome in outcomes:
            token_id = self.market_state.token_by_outcome.get(outcome)
            ask = self.market_state.best_ask_by_token.get(token_id or "")
            if not token_id or ask is None:
                continue

            effective_budget = budget
            if max_total > 0:
                effective_budget = min(effective_budget, max_total - state.total_spent)
            if effective_budget <= 0:
                continue

            size = float(int((effective_budget / ask) * 100) / 100)
            if size <= 0:
                continue

            state.last_trigger_at = now
            state.next_run_at = now + interval
            return OrderIntent(
                rule_id=rule_id,
                rule_type="periodic_buy",
                token_id=token_id,
                side="BUY",
                price=ask,
                size=size,
                outcome=outcome,
                metadata={
                    "interval_seconds": interval,
                    "budget_usdc": effective_budget,
                    "order_type": str(cfg.get("order_type", "GTC")),
                },
            )

        return None

    def mark_executed(self, intent: OrderIntent) -> None:
        state = self._state(intent.rule_id)
        now = time.time()
        state.last_trigger_at = now
        state.last_order_at = now
        state.order_count += 1
        if intent.side == "BUY":
            state.total_spent += intent.price * intent.size


class AutoTradeHandler:
    """AutoTrade 处理器：封装 intent 执行、tick 循环、状态发布。"""

    def __init__(
        self,
        task_id: str,
        config_provider: Callable[[], Any],
        market_state: MarketState,
        publisher: EventPublisher,
    ) -> None:
        self.task_id = task_id
        self._config_provider = config_provider
        self.market_state = market_state
        self.publisher = publisher
        self.rule_engine = RuleEngine(config_provider, market_state)

    @property
    def _config(self) -> Any:
        return self._config_provider()

    def has_enabled_signal_buy(self) -> bool:
        config = self._config
        auto_trade = config.auto_trade if isinstance(config.auto_trade, dict) else {}
        if not auto_trade.get("enabled", False):
            return False
        rules = auto_trade.get("rules")
        if not isinstance(rules, list):
            return False

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            if str(rule.get("type", "")).strip() != "signal_buy":
                continue
            if bool(rule.get("enabled", True)):
                return True
        return False

    async def publish_state(self) -> None:
        config = self._config
        auto_trade = config.auto_trade if isinstance(config.auto_trade, dict) else {}
        cfg = copy.deepcopy(auto_trade) if isinstance(auto_trade, dict) else {}
        payload = {
            "enabled": bool(cfg.get("enabled", False)),
            "version": int(cfg.get("version", 1)),
            "config_version": int(cfg.get("config_version", 0)),
            "defaults": cfg.get("defaults", {}),
            "rules": cfg.get("rules", []),
            "runtime": self.rule_engine.get_runtime_snapshot(),
            "timestamp": now_iso(),
        }
        await self.publisher.publish("auto_trade_state", payload)

    async def on_config_updated(self, old_auto_trade: dict[str, Any], new_auto_trade: dict[str, Any]) -> None:
        self.rule_engine.on_config_updated(old_auto_trade, new_auto_trade)

    async def tick_loop(self, cancelled_fn: Callable[[], bool]) -> None:
        while not cancelled_fn():
            await self.execute_intents(self.rule_engine.on_tick())
            await asyncio.sleep(1.0)

    async def execute_intents(self, intents: list[OrderIntent]) -> None:
        if not intents:
            return

        config = self._config
        if not config.private_key:
            await self._publish_execution(
                success=False,
                orders=[],
                error="private_key 不能为空",
            )
            return

        auto_trade = config.auto_trade if isinstance(config.auto_trade, dict) else {}
        cfg = copy.deepcopy(auto_trade) if isinstance(auto_trade, dict) else {}
        defaults = cfg.get("defaults") if isinstance(cfg.get("defaults"), dict) else {}
        min_order_amount = float(defaults.get("min_order_amount", 1.0))
        default_order_type = str(defaults.get("order_type", "GTC"))

        success_count = 0
        orders: list[dict[str, Any]] = []
        errors: list[str] = []

        for intent in intents:
            ok, reason = self.rule_engine.risk_gate.check_basic(
                intent,
                min_order_amount=min_order_amount,
            )
            if not ok:
                message = reason or "风控拒绝"
                errors.append(f"{intent.rule_id}: {message}")
                orders.append({
                    "rule_id": intent.rule_id,
                    "rule_type": intent.rule_type,
                    "outcome": intent.outcome,
                    "token_id": intent.token_id,
                    "side": intent.side,
                    "price": intent.price,
                    "size": intent.size,
                    "status": "REJECTED",
                    "error": message,
                })
                continue

            time_bucket = int(time.time() // 3)
            dedupe_key = (
                f"{self.task_id}:{intent.rule_id}:{intent.token_id}:{intent.side}:"
                f"{round(intent.price, 3)}:{time_bucket}"
            )
            if not self.rule_engine.risk_gate.allow(dedupe_key=dedupe_key, dedupe_ttl_sec=3.0):
                orders.append({
                    "rule_id": intent.rule_id,
                    "rule_type": intent.rule_type,
                    "outcome": intent.outcome,
                    "token_id": intent.token_id,
                    "side": intent.side,
                    "price": intent.price,
                    "size": intent.size,
                    "status": "SKIPPED",
                    "error": "重复触发已忽略",
                })
                continue

            order_type = str(intent.metadata.get("order_type", default_order_type))
            request = OrderRequest(
                token_id=intent.token_id,
                side=intent.side,
                price=float(intent.price),
                size=float(intent.size),
                order_type=order_type,
                private_key=config.private_key,
                proxy_address=config.proxy_address,
            )
            result = await OrderExecutor.execute(request)
            if result.success:
                success_count += 1
                self.rule_engine.mark_executed(intent)
                orders.append({
                    "rule_id": intent.rule_id,
                    "rule_type": intent.rule_type,
                    "outcome": intent.outcome,
                    "token_id": intent.token_id,
                    "side": intent.side,
                    "price": intent.price,
                    "size": intent.size,
                    "status": "SUBMITTED",
                    "result": result.result,
                    "metadata": intent.metadata,
                })
            else:
                message = result.error or "下单失败"
                errors.append(f"{intent.rule_id}: {message}")
                orders.append({
                    "rule_id": intent.rule_id,
                    "rule_type": intent.rule_type,
                    "outcome": intent.outcome,
                    "token_id": intent.token_id,
                    "side": intent.side,
                    "price": intent.price,
                    "size": intent.size,
                    "status": "FAILED",
                    "error": message,
                    "metadata": intent.metadata,
                })

        success = success_count > 0 and all(item.get("status") != "FAILED" for item in orders)
        await self._publish_execution(
            success=success,
            orders=orders,
            error="; ".join(errors) if errors else None,
        )
        await self.publish_state()

    async def _publish_execution(
        self,
        success: bool,
        orders: list[dict[str, Any]],
        error: Optional[str] = None,
    ) -> None:
        payload = {
            "success": success,
            "orders": orders,
            "error": error,
            "source": "auto_trade_engine",
            "timestamp": now_iso(),
        }
        await self.publisher.publish("auto_trade_execution", payload)
