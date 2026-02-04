"""二元合并买入策略 (Binary Merge Long Strategy)

策略原理：
    二元市场（Binary Market）中，YES 和 NO 两个结果互斥且完备，
    结算时必有一方价值 1.0，另一方价值 0。
    因此：YES + NO 结算价值 = 1.0

    如果能以总成本 < 1.0 同时买入 YES 和 NO，结算时必然盈利。
    利润 = 1.0 - 买入成本

核心公式：
    有效买入价 YES = min(yes_ask, 1.0 - no_bid)
    有效买入价 NO  = min(no_ask, 1.0 - yes_bid)
    做多成本 = 有效买入价 YES + 有效买入价 NO

    为什么用 min(ask, 1.0 - opposite_bid)？
    - 直接买入：以 ask 价格买入
    - 间接买入：卖出对手方获得 1.0 - opposite_bid 成本的等效头寸
    - 取两者较小值为有效成本

触发条件：
    做多成本 <= 1.0 - min_arbitrage_gap

参数：
    min_arbitrage_gap: float = 0.0
        最小套利空间要求。例如 0.01 表示要求至少 1% 利润空间。
    total_budget: float = 10.0
        单次交易总预算（USDC）。

示例：
    YES ask=0.52, bid=0.50
    NO  ask=0.47, bid=0.45

    有效买入价 YES = min(0.52, 1.0 - 0.45) = min(0.52, 0.55) = 0.52
    有效买入价 NO  = min(0.47, 1.0 - 0.50) = min(0.47, 0.50) = 0.47
    做多成本 = 0.52 + 0.47 = 0.99

    如果 min_arbitrage_gap = 0.005：
        阈值 = 1.0 - 0.005 = 0.995
        0.99 < 0.995 ✓ 触发买入
        预期利润 = 1.0 - 0.99 = 0.01 (1%)

    买入数量 = total_budget / 做多成本 = 10.0 / 0.99 ≈ 10.10
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from .base import BaseStrategy, TradingSignal, SignalType
from .registry import StrategyRegistry
from ..models import MarketSnapshot, OrderBookContext, PositionContext


@StrategyRegistry.register("merge_long")
class MergeLongStrategy(BaseStrategy):
    """合并做多策略：双边买入成本 < 1.0 时套利"""

    DEFAULT_PARAMS = {
        "min_arbitrage_gap": 0.01,
        "total_budget": 10.0,
    }

    @property
    def strategy_id(self) -> str:
        return "merge_long"

    def _get_param(self, params: dict[str, Any], key: str) -> Any:
        """获取参数，优先使用传入值，否则使用默认值"""
        return params.get(key, self.DEFAULT_PARAMS.get(key))

    def generate_signal(
        self,
        snapshot: MarketSnapshot,
        order_book: OrderBookContext,
        position: PositionContext,
        params: dict[str, Any],
    ) -> Optional[TradingSignal]:
        """生成交易信号"""

        # 获取订单簿最优价格
        yes_ask = order_book.yes_best_ask
        no_ask = order_book.no_best_ask
        yes_bid = order_book.yes_best_bid
        no_bid = order_book.no_best_bid

        # 检查订单簿完整性
        if yes_ask is None or no_ask is None or yes_bid is None or no_bid is None:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason="订单簿不完整，缺少 bid/ask",
            )

        # 计算有效买入价格
        effective_buy_yes = min(yes_ask, 1.0 - no_bid)
        effective_buy_no = min(no_ask, 1.0 - yes_bid)
        long_cost = effective_buy_yes + effective_buy_no

        logger.debug(
            "YES ask=%.4f bid=%.4f, NO ask=%.4f bid=%.4f, cost=%.4f",
            yes_ask,
            yes_bid,
            no_ask,
            no_bid,
            long_cost,
        )

        # 获取参数
        min_arbitrage_gap = self._get_param(params, "min_arbitrage_gap")
        total_budget = self._get_param(params, "total_budget")

        # 参数验证
        try:
            min_arbitrage_gap = float(min_arbitrage_gap)
        except (TypeError, ValueError):
            min_arbitrage_gap = 0.0

        if not isinstance(total_budget, (int, float)) or total_budget <= 0:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason=f"无效的 total_budget: {total_budget}",
            )

        # 计算阈值
        threshold = 1.0 - min_arbitrage_gap
        epsilon = 1e-6

        # 构建通用元数据
        base_metadata = {
            "effective_buy_yes": effective_buy_yes,
            "effective_buy_no": effective_buy_no,
            "long_cost": long_cost,
            "threshold": threshold,
            "min_arbitrage_gap": min_arbitrage_gap,
            "yes_ask": yes_ask,
            "yes_bid": yes_bid,
            "no_ask": no_ask,
            "no_bid": no_bid,
        }

        # 检查是否满足套利条件
        if long_cost > threshold + epsilon:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason=f"成本 {long_cost:.2f} > 阈值 {threshold:.2f}",
                metadata=base_metadata,
            )

        # 验证成本有效性
        if long_cost <= 0:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason=f"无效成本: {long_cost:.2f}",
                metadata=base_metadata,
            )

        # 计算买入数量
        size = total_budget / long_cost
        if size <= 0:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason=f"计算数量无效: {size:.2f}",
                metadata=base_metadata,
            )

        # 计算预期利润
        expected_profit = (1.0 - long_cost) * size
        expected_profit_pct = (1.0 - long_cost) * 100

        logger.info(
            f"套利触发: cost={long_cost:.4f}, threshold={threshold:.4f}, size={size:.2f}, "
            f"profit={expected_profit:.2f} ({expected_profit_pct:.2f}%)"
        )

        return TradingSignal(
            signal_type=SignalType.BUY,
            yes_size=size,
            no_size=size,
            yes_price=effective_buy_yes,
            no_price=effective_buy_no,
            reason=f"套利: 成本 {long_cost:.2f} <= 阈值 {threshold:.2f}，预期利润 {expected_profit_pct:.2f}%",
            metadata={
                **base_metadata,
                "total_budget": total_budget,
                "size": size,
                "expected_profit": expected_profit,
                "expected_profit_pct": expected_profit_pct,
            },
        )
