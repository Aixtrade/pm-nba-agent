"""市场状态容器 — 唯一的市场数据源"""

from typing import Any, Optional


BOTH_SIDE = "__BOTH__"


class MarketState:
    """封装所有市场数据字典，供各业务模块注入引用消费。"""

    def __init__(self) -> None:
        self.token_by_outcome: dict[str, str] = {}
        self.outcome_by_token: dict[str, str] = {}
        self.best_ask_by_token: dict[str, float] = {}
        self.best_bid_by_token: dict[str, float] = {}
        self.condition_id: Optional[str] = None
        self.outcomes: list[str] = []

    def update_from_polymarket_info(self, payload: dict[str, Any]) -> None:
        tokens = payload.get("tokens")
        if not isinstance(tokens, list):
            return

        mapping: dict[str, str] = {}
        reverse: dict[str, str] = {}

        for token in tokens:
            if not isinstance(token, dict):
                continue
            outcome = str(token.get("outcome") or "").strip()
            token_id = str(token.get("token_id") or "").strip()
            if not outcome or not token_id:
                continue
            mapping[outcome] = token_id
            reverse[token_id] = outcome

        if mapping:
            self.token_by_outcome = mapping
            self.outcome_by_token = reverse
            self.outcomes = list(mapping.keys())
            condition_id = payload.get("condition_id")
            if isinstance(condition_id, str) and condition_id:
                self.condition_id = condition_id

            market_info = payload.get("market_info")
            if isinstance(market_info, dict):
                nested_condition_id = market_info.get("condition_id")
                if isinstance(nested_condition_id, str) and nested_condition_id:
                    self.condition_id = nested_condition_id
                raw_outcomes = market_info.get("outcomes")
                if isinstance(raw_outcomes, list):
                    normalized_outcomes = [
                        str(outcome).strip()
                        for outcome in raw_outcomes
                        if str(outcome).strip()
                    ]
                    if normalized_outcomes:
                        self.outcomes = normalized_outcomes

    def update_from_polymarket_book(self, payload: dict[str, Any]) -> None:
        price_changes = payload.get("price_changes")
        if isinstance(price_changes, list) and price_changes:
            for change in price_changes:
                if not isinstance(change, dict):
                    continue
                asset_id = change.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id:
                    continue
                best_bid = change.get("best_bid")
                best_ask = change.get("best_ask")
                try:
                    bid_value = float(best_bid) if best_bid is not None else None
                except (TypeError, ValueError):
                    bid_value = None
                try:
                    ask_value = float(best_ask) if best_ask is not None else None
                except (TypeError, ValueError):
                    ask_value = None

                if bid_value is not None and 0 < bid_value < 1:
                    self.best_bid_by_token[asset_id] = bid_value
                if ask_value is not None and 0 < ask_value < 1:
                    self.best_ask_by_token[asset_id] = ask_value
            return

        asset_id = (
            payload.get("asset_id")
            or payload.get("assetId")
            or payload.get("token_id")
            or payload.get("tokenId")
        )
        if not isinstance(asset_id, str) or not asset_id:
            return

        bids = payload.get("bids") or payload.get("buys") or []
        asks = payload.get("asks") or payload.get("sells") or []

        if isinstance(bids, list) and bids:
            best_bid = _extract_best_bid(bids)
            if best_bid is not None:
                self.best_bid_by_token[asset_id] = best_bid

        if isinstance(asks, list) and asks:
            best_ask = _extract_best_ask(asks)
            if best_ask is not None:
                self.best_ask_by_token[asset_id] = best_ask

    def resolve_outcomes(self, side: str) -> list[str]:
        if side == BOTH_SIDE:
            return list(self.token_by_outcome.keys())
        if side in self.token_by_outcome:
            return [side]
        return []

    def get_best_ask(self, outcome: str) -> Optional[float]:
        token_id = self.token_by_outcome.get(outcome)
        if not token_id:
            return None
        return self.best_ask_by_token.get(token_id)

    def get_best_bid(self, outcome: str) -> Optional[float]:
        token_id = self.token_by_outcome.get(outcome)
        if not token_id:
            return None
        return self.best_bid_by_token.get(token_id)

    def get_token_id(self, outcome: str) -> Optional[str]:
        return self.token_by_outcome.get(outcome)


def _extract_best_bid(bids: list) -> Optional[float]:
    values: list[float] = []
    for bid in bids:
        price: Optional[float] = None
        if isinstance(bid, dict):
            raw = bid.get("price")
            if raw is not None:
                try:
                    price = float(raw)
                except (TypeError, ValueError):
                    price = None
        elif isinstance(bid, (list, tuple)) and len(bid) >= 1:
            try:
                price = float(bid[0])
            except (TypeError, ValueError):
                price = None

        if price is None:
            continue
        if 0 < price < 1:
            values.append(price)

    if not values:
        return None
    return max(values)


def _extract_best_ask(asks: list) -> Optional[float]:
    values: list[float] = []
    for ask in asks:
        price: Optional[float] = None
        if isinstance(ask, dict):
            raw = ask.get("price")
            if raw is not None:
                try:
                    price = float(raw)
                except (TypeError, ValueError):
                    price = None
        elif isinstance(ask, (list, tuple)) and len(ask) >= 1:
            try:
                price = float(ask[0])
            except (TypeError, ValueError):
                price = None

        if price is None:
            continue
        if 0 < price < 1:
            values.append(price)

    if not values:
        return None
    return min(values)
