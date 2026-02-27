"""统一下单接口 — 被 AutoBuy / AutoSell / AutoTrade 共享"""

from dataclasses import dataclass, field
from typing import Any, Optional

from pm_nba_agent.polymarket.orders import create_polymarket_order


@dataclass
class OrderRequest:
    token_id: str
    side: str
    price: float
    size: float
    order_type: str = "GTC"
    private_key: str = ""
    proxy_address: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderResult:
    success: bool
    result: Any = None
    error: Optional[str] = None


class OrderExecutor:
    """统一下单执行器。"""

    @staticmethod
    async def execute(request: OrderRequest) -> OrderResult:
        try:
            result = await create_polymarket_order(
                token_id=request.token_id,
                side=request.side,
                price=request.price,
                size=request.size,
                order_type=request.order_type,
                private_key=request.private_key,
                proxy_address=request.proxy_address,
            )
            return OrderResult(success=True, result=result)
        except Exception as exc:
            return OrderResult(success=False, error=str(exc))
