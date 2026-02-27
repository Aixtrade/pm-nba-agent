"""SSE 纯工具函数"""

import json
from datetime import datetime
from typing import Any, Optional


def parse_sse_event(event: str) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    event_type: Optional[str] = None
    data_payload: Optional[str] = None

    for line in event.splitlines():
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:") and data_payload is None:
            data_payload = line[5:].strip()

    if not event_type or not data_payload:
        return None, None

    try:
        parsed = json.loads(data_payload)
    except Exception:
        return event_type, None

    if not isinstance(parsed, dict):
        return event_type, None

    return event_type, parsed


def format_sse_event(event_type: str, payload: dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = deep_merge_dict(current, value)
        else:
            merged[key] = value
    return merged


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def seconds_since_iso(value: str) -> float:
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        now = datetime.now(ts.tzinfo)
        return max(0.0, (now - ts).total_seconds())
    except Exception:
        return 10 ** 9


def calculate_size(amount: float, price: float, round_size: bool) -> float:
    if price <= 0 or price >= 1:
        return 0.0

    raw_size = amount / price
    if round_size:
        return float(int(raw_size))
    return float(int(raw_size * 100) / 100)


def calculate_profit_rate(avg_price: float, current_price: float) -> float:
    if avg_price <= 0:
        return -1.0
    return (current_price - avg_price) / avg_price
