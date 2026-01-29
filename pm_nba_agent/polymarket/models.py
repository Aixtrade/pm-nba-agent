"""Polymarket 数据模型"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TokenInfo:
    """Token 信息"""

    token_id: str
    outcome: str
    condition_id: str
    market_slug: str

    def to_dict(self) -> dict:
        return {
            "token_id": self.token_id,
            "outcome": self.outcome,
            "condition_id": self.condition_id,
            "market_slug": self.market_slug,
        }


@dataclass
class MarketInfo:
    """市场信息"""

    slug: str
    question: Optional[str]
    description: Optional[str]
    condition_id: Optional[str]
    outcomes: list[str]
    clob_token_ids: list[str]
    market_id: Optional[str]
    raw_data: Optional[dict]

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "question": self.question,
            "description": self.description,
            "condition_id": self.condition_id,
            "outcomes": self.outcomes,
            "clob_token_ids": self.clob_token_ids,
            "market_id": self.market_id,
            "raw_data": self.raw_data,
        }


@dataclass
class EventInfo:
    """事件信息"""

    event_id: str
    title: str
    interval: str
    asset: str
    tokens: list[TokenInfo]
    condition_id: Optional[str]
    market_info: Optional[MarketInfo]
    event_data: Optional[dict]

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "interval": self.interval,
            "asset": self.asset,
            "condition_id": self.condition_id,
            "tokens": [token.to_dict() for token in self.tokens],
            "market_info": self.market_info.to_dict() if self.market_info else None,
            "event_data": self.event_data,
        }
