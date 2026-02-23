"""任务模型定义"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskState(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 等待启动
    CANCELLING = "cancelling"  # 取消中
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 正常完成
    CANCELLED = "cancelled"  # 用户取消
    FAILED = "failed"  # 异常失败


@dataclass
class TaskConfig:
    """任务配置（从 LiveStreamRequest 提取）"""

    url: str
    poll_interval: float = 10.0
    user_id: str = ""
    include_scoreboard: bool = True
    include_boxscore: bool = True
    analysis_interval: float = 30.0
    strategy_ids: list[str] | None = None
    strategy_params_map: dict[str, dict[str, Any]] | None = None
    strategy_id: str = "merge_long"
    strategy_params: dict[str, Any] = field(default_factory=dict)
    enable_trading: bool = False
    execution_mode: str = "SIMULATION"
    order_type: str = "GTC"
    order_expiration: Optional[str] = None
    min_order_amount: float = 1.0
    trade_cooldown_seconds: float = 0.0
    private_key: Optional[str] = None
    proxy_address: Optional[str] = None
    auto_buy: dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "default": {
            "amount": 10.0,
            "round_size": False,
            "order_type": "GTC",
            "execution_mode": "SIMULATION",
            "private_key": None,
            "proxy_address": None,
        },
        "strategy_rules": {},
    })
    auto_sell: dict[str, Any] = field(default_factory=lambda: {
        "enabled": False,
        "default": {
            "min_profit_rate": 5.0,
            "sell_ratio": 100.0,
            "cooldown_time": 30.0,
            "refresh_interval": 3.0,
            "order_type": "GTC",
            "max_stale_seconds": 7.0,
        },
        "outcome_rules": {},
    })
    auto_trade: dict[str, Any] = field(default_factory=lambda: {
        "version": 1,
        "enabled": False,
        "defaults": {
            "order_type": "GTC",
            "min_order_amount": 1.0,
            "round_size": False,
            "execution_mode": "SIMULATION",
        },
        "rules": [],
    })
    enable_analysis: bool = True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskConfig":
        """从字典创建"""
        return cls(
            url=data.get("url", ""),
            poll_interval=float(data.get("poll_interval", 10.0)),
            user_id=str(data.get("user_id", "")),
            include_scoreboard=bool(data.get("include_scoreboard", True)),
            include_boxscore=bool(data.get("include_boxscore", True)),
            analysis_interval=float(data.get("analysis_interval", 30.0)),
            strategy_ids=data.get("strategy_ids"),
            strategy_params_map=data.get("strategy_params_map"),
            strategy_id=str(data.get("strategy_id", "merge_long")),
            strategy_params=data.get("strategy_params") or {},
            enable_trading=bool(data.get("enable_trading", False)),
            execution_mode=str(data.get("execution_mode", "SIMULATION")),
            order_type=str(data.get("order_type", "GTC")),
            order_expiration=data.get("order_expiration"),
            min_order_amount=float(data.get("min_order_amount", 1.0)),
            trade_cooldown_seconds=float(data.get("trade_cooldown_seconds", 0.0)),
            private_key=data.get("private_key"),
            proxy_address=data.get("proxy_address"),
            auto_buy=_normalize_auto_buy(data.get("auto_buy")),
            auto_sell=_normalize_auto_sell(data.get("auto_sell")),
            auto_trade=_normalize_auto_trade(
                data.get("auto_trade"),
                legacy_auto_buy=data.get("auto_buy"),
                legacy_auto_sell=data.get("auto_sell"),
            ),
            enable_analysis=bool(data.get("enable_analysis", True)),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TaskConfig":
        """从 JSON 反序列化"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class TaskStatus:
    """任务状态"""

    task_id: str
    state: TaskState
    created_at: str  # ISO 格式时间戳
    updated_at: str  # ISO 格式时间戳
    game_id: Optional[str] = None
    error: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    user_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "game_id": self.game_id,
            "error": self.error,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "user_id": self.user_id,
        }

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskStatus":
        """从字典创建"""
        return cls(
            task_id=data["task_id"],
            state=TaskState(data["state"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            game_id=data.get("game_id"),
            error=data.get("error"),
            home_team=data.get("home_team"),
            away_team=data.get("away_team"),
            user_id=str(data.get("user_id", "")),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TaskStatus":
        """从 JSON 反序列化"""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def create(cls, task_id: str, user_id: str = "") -> "TaskStatus":
        """创建新任务状态"""
        now = datetime.utcnow().isoformat() + "Z"
        return cls(
            task_id=task_id,
            state=TaskState.PENDING,
            created_at=now,
            updated_at=now,
            user_id=user_id,
        )

    def update_state(self, state: TaskState, error: Optional[str] = None) -> None:
        """更新状态"""
        self.state = state
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        if error:
            self.error = error

    def set_game_info(
        self, game_id: str, home_team: str, away_team: str
    ) -> None:
        """设置比赛信息"""
        self.game_id = game_id
        self.home_team = home_team
        self.away_team = away_team
        self.updated_at = datetime.utcnow().isoformat() + "Z"


def _normalize_auto_buy(value: Any) -> dict[str, Any]:
    """规范化 auto_buy 配置"""
    base = {
        "enabled": False,
        "default": {
            "amount": 10.0,
            "round_size": False,
            "order_type": "GTC",
            "execution_mode": "SIMULATION",
            "private_key": None,
            "proxy_address": None,
        },
        "strategy_rules": {},
    }

    if not isinstance(value, dict):
        return base

    default_input = value.get("default")
    if isinstance(default_input, dict):
        default_cfg = {
            **base["default"],
            "amount": _to_float(default_input.get("amount"), base["default"]["amount"]),
            "round_size": bool(default_input.get("round_size", base["default"]["round_size"])),
            "order_type": str(default_input.get("order_type", base["default"]["order_type"])),
            "execution_mode": str(default_input.get("execution_mode", base["default"]["execution_mode"])),
            "private_key": default_input.get("private_key"),
            "proxy_address": default_input.get("proxy_address"),
        }
    else:
        default_cfg = dict(base["default"])

    strategy_rules: dict[str, Any] = {}
    raw_rules = value.get("strategy_rules")
    if isinstance(raw_rules, dict):
        for strategy_id, raw_rule in raw_rules.items():
            if not isinstance(strategy_id, str) or not strategy_id:
                continue
            if not isinstance(raw_rule, dict):
                continue

            rule: dict[str, Any] = {
                "enabled": bool(raw_rule.get("enabled", True)),
                "side": str(raw_rule.get("side", "__BOTH__")),
                "signal_types": raw_rule.get("signal_types") or ["BUY"],
            }

            if raw_rule.get("amount") is not None:
                rule["amount"] = _to_float(raw_rule.get("amount"), 0.0)
            if raw_rule.get("round_size") is not None:
                rule["round_size"] = bool(raw_rule.get("round_size"))
            if raw_rule.get("order_type") is not None:
                rule["order_type"] = str(raw_rule.get("order_type"))
            if raw_rule.get("execution_mode") is not None:
                rule["execution_mode"] = str(raw_rule.get("execution_mode"))

            strategy_rules[strategy_id] = rule

    return {
        "enabled": bool(value.get("enabled", False)),
        "default": default_cfg,
        "strategy_rules": strategy_rules,
    }


def _normalize_auto_sell(value: Any) -> dict[str, Any]:
    """规范化 auto_sell 配置"""
    base = {
        "enabled": False,
        "default": {
            "min_profit_rate": 5.0,
            "sell_ratio": 100.0,
            "cooldown_time": 30.0,
            "refresh_interval": 3.0,
            "order_type": "GTC",
            "max_stale_seconds": 7.0,
        },
        "outcome_rules": {},
    }

    if not isinstance(value, dict):
        return base

    default_input = value.get("default")
    if isinstance(default_input, dict):
        default_cfg = {
            **base["default"],
            "min_profit_rate": _to_float(default_input.get("min_profit_rate"), base["default"]["min_profit_rate"]),
            "sell_ratio": _to_float(default_input.get("sell_ratio"), base["default"]["sell_ratio"]),
            "cooldown_time": _to_float(default_input.get("cooldown_time"), base["default"]["cooldown_time"]),
            "refresh_interval": _to_float(default_input.get("refresh_interval"), base["default"]["refresh_interval"]),
            "order_type": str(default_input.get("order_type", base["default"]["order_type"])),
            "max_stale_seconds": _to_float(default_input.get("max_stale_seconds"), base["default"]["max_stale_seconds"]),
        }
    else:
        default_cfg = dict(base["default"])

    outcome_rules: dict[str, Any] = {}
    raw_rules = value.get("outcome_rules")
    if isinstance(raw_rules, dict):
        for outcome, raw_rule in raw_rules.items():
            if not isinstance(outcome, str) or not outcome:
                continue
            if not isinstance(raw_rule, dict):
                continue

            rule: dict[str, Any] = {
                "enabled": bool(raw_rule.get("enabled", False)),
            }
            if raw_rule.get("min_profit_rate") is not None:
                rule["min_profit_rate"] = _to_float(raw_rule.get("min_profit_rate"), 0.0)
            if raw_rule.get("sell_ratio") is not None:
                rule["sell_ratio"] = _to_float(raw_rule.get("sell_ratio"), 0.0)
            if raw_rule.get("cooldown_time") is not None:
                rule["cooldown_time"] = _to_float(raw_rule.get("cooldown_time"), 0.0)
            if raw_rule.get("order_type") is not None:
                rule["order_type"] = str(raw_rule.get("order_type"))

            outcome_rules[outcome] = rule

    return {
        "enabled": bool(value.get("enabled", False)),
        "default": default_cfg,
        "outcome_rules": outcome_rules,
    }


def _default_auto_trade() -> dict[str, Any]:
    return {
        "version": 1,
        "enabled": False,
        "defaults": {
            "order_type": "GTC",
            "min_order_amount": 1.0,
            "round_size": False,
            "execution_mode": "SIMULATION",
        },
        "rules": [],
    }


def _normalize_auto_trade(
    value: Any,
    legacy_auto_buy: dict[str, Any] | None = None,
    legacy_auto_sell: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = _default_auto_trade()

    if isinstance(value, dict):
        defaults_in: dict[str, Any] = {}
        raw_defaults = value.get("defaults")
        if isinstance(raw_defaults, dict):
            defaults_in = raw_defaults
        defaults = {
            "order_type": str(defaults_in.get("order_type", base["defaults"]["order_type"])),
            "min_order_amount": _to_float(defaults_in.get("min_order_amount"), base["defaults"]["min_order_amount"]),
            "round_size": bool(defaults_in.get("round_size", base["defaults"]["round_size"])),
            "execution_mode": str(defaults_in.get("execution_mode", base["defaults"]["execution_mode"])),
        }

        rules: list[dict[str, Any]] = []
        raw_rules = value.get("rules")
        if isinstance(raw_rules, list):
            for index, raw_rule in enumerate(raw_rules):
                normalized_rule = _normalize_auto_trade_rule(raw_rule, index)
                if normalized_rule:
                    rules.append(normalized_rule)

        return {
            "version": max(1, _to_int(value.get("version"), 1)),
            "enabled": bool(value.get("enabled", False)),
            "defaults": defaults,
            "rules": rules,
        }

    migrated_rules = _migrate_legacy_auto_buy_rules(legacy_auto_buy)
    migrated_rules.extend(_migrate_legacy_auto_sell_rules(legacy_auto_sell))
    return {
        "version": 1,
        "enabled": bool(migrated_rules),
        "defaults": base["defaults"],
        "rules": migrated_rules,
    }


def _normalize_auto_trade_rule(value: Any, index: int) -> Optional[dict[str, Any]]:
    if not isinstance(value, dict):
        return None

    rule_type = str(value.get("type", "")).strip()
    if not rule_type:
        return None

    rule_id = str(value.get("id", "")).strip() or f"{rule_type}_{index + 1}"
    scope_input: dict[str, Any] = {}
    raw_scope = value.get("scope")
    if isinstance(raw_scope, dict):
        scope_input = raw_scope
    scope = {
        "strategy_id": str(scope_input.get("strategy_id", "")).strip() or None,
        "outcome": str(scope_input.get("outcome", "__BOTH__")).strip() or "__BOTH__",
    }

    config_input: dict[str, Any] = {}
    raw_config = value.get("config")
    if isinstance(raw_config, dict):
        config_input = raw_config
    risk_input: dict[str, Any] = {}
    raw_risk = value.get("risk")
    if isinstance(raw_risk, dict):
        risk_input = raw_risk

    return {
        "id": rule_id,
        "type": rule_type,
        "enabled": bool(value.get("enabled", True)),
        "priority": _to_int(value.get("priority"), 1000),
        "scope": scope,
        "cooldown_seconds": max(0.0, _to_float(value.get("cooldown_seconds"), 0.0)),
        "config": _normalize_auto_trade_rule_config(rule_type, config_input),
        "risk": {
            "max_total_budget": max(0.0, _to_float(risk_input.get("max_total_budget"), 0.0)),
            "max_order_count": max(0, _to_int(risk_input.get("max_order_count"), 0)),
            "max_slippage": max(0.0, _to_float(risk_input.get("max_slippage"), 0.0)),
        },
    }


def _normalize_auto_trade_rule_config(rule_type: str, config: dict[str, Any]) -> dict[str, Any]:
    if rule_type == "signal_buy":
        signal_types = config.get("signal_types")
        if not isinstance(signal_types, list) or not signal_types:
            signal_types = ["BUY"]
        return {
            "signal_types": [str(item).upper() for item in signal_types],
            "amount": _to_float(config.get("amount"), 10.0),
            "round_size": bool(config.get("round_size", False)),
            "order_type": str(config.get("order_type", "GTC")),
        }

    if rule_type == "condition_buy":
        return {
            "trigger_price_lte": _to_float(config.get("trigger_price_lte"), 0.45),
            "budget_usdc": _to_float(config.get("budget_usdc"), 10.0),
            "order_type": str(config.get("order_type", "GTC")),
        }

    if rule_type == "periodic_buy":
        return {
            "interval_seconds": max(5, _to_int(config.get("interval_seconds"), 120)),
            "budget_usdc": _to_float(config.get("budget_usdc"), 10.0),
            "max_total_budget": max(0.0, _to_float(config.get("max_total_budget"), 0.0)),
            "order_type": str(config.get("order_type", "GTC")),
        }

    return dict(config)


def _migrate_legacy_auto_buy_rules(legacy_auto_buy: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(legacy_auto_buy, dict):
        return []

    rules: list[dict[str, Any]] = []
    strategy_rules = legacy_auto_buy.get("strategy_rules")
    if not isinstance(strategy_rules, dict):
        return rules

    default_input: dict[str, Any] = {}
    raw_default = legacy_auto_buy.get("default")
    if isinstance(raw_default, dict):
        default_input = raw_default

    for strategy_id, raw_rule in strategy_rules.items():
        if not isinstance(strategy_id, str) or not strategy_id:
            continue
        if not isinstance(raw_rule, dict):
            continue

        signal_types = raw_rule.get("signal_types")
        if not isinstance(signal_types, list) or not signal_types:
            signal_types = ["BUY"]

        rules.append({
            "id": f"legacy_signal_buy_{strategy_id}",
            "type": "signal_buy",
            "enabled": bool(raw_rule.get("enabled", True)),
            "priority": 100,
            "scope": {
                "strategy_id": strategy_id,
                "outcome": str(raw_rule.get("side", "__BOTH__")),
            },
            "cooldown_seconds": 0.0,
            "config": {
                "signal_types": [str(item).upper() for item in signal_types],
                "amount": _to_float(raw_rule.get("amount"), _to_float(default_input.get("amount"), 10.0)),
                "round_size": bool(raw_rule.get("round_size", default_input.get("round_size", False))),
                "order_type": str(raw_rule.get("order_type", default_input.get("order_type", "GTC"))),
            },
            "risk": {
                "max_total_budget": 0.0,
                "max_order_count": 0,
                "max_slippage": 0.0,
            },
        })

    return rules


def _migrate_legacy_auto_sell_rules(legacy_auto_sell: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(legacy_auto_sell, dict):
        return []
    return []


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
