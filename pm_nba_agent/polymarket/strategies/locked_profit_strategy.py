"""锁定利润策略 (Locked Profit Strategy)

策略原理：
    通过同时持有 YES 和 NO 两边的份额来对冲风险，确保无论哪边赢都能达到目标利润。

    在二元市场中：
    - YES 赢时利润 = yes_size * settle - net_cost
    - NO 赢时利润 = no_size * settle - net_cost
    - 锁定利润 = min(yes_size, no_size) * settle - net_cost

    如果已有单边仓位，通过买入另一边可以"锁定"保底利润。

核心公式：
    设已有持仓 (q_yes, q_no, net_cost)，要买入 side 的 x 份，价格 p。

    如果买 YES:
    - YES 赢利润 = profit_yes + x * (settle - p)
    - NO 赢利润 = profit_no - x * p

    如果买 NO:
    - NO 赢利润 = profit_no + x * (settle - p)
    - YES 赢利润 = profit_yes - x * p

    求最小 x 使得两边利润都 >= target_profit。

参数：
    target_profit: float = 0.0
        目标保底利润。默认 0 表示保本不亏。

触发条件：
    1. 有持仓（yes_size > 0 或 no_size > 0）
    2. 某一边利润 < target_profit
    3. 计算出的对冲买入量 > 0

示例：
    已持有 YES 11份，成本 $1
    - YES 赢利润 = 11 - 1 = 10
    - NO 赢利润 = 0 - 1 = -1  ← 亏损风险！

    当前 NO ask = 0.48，计算对冲买入量：
    需买入 NO 约 2.08 份，使 NO 赢时利润 >= 0

    买入后：
    - YES 赢利润 = 11 - 1 - 2.08*0.48 = 9.00
    - NO 赢利润 = 2.08 - 1 - 2.08*0.48 ≈ 0.08 ≈ 0 ✓
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from loguru import logger

from .base import BaseStrategy, SignalType, TradingSignal
from .registry import StrategyRegistry
from ..models import MarketSnapshot, OrderBookContext, PositionContext


# ---------- 内部数据结构 ----------

Side = Literal["YES", "NO"]


@dataclass
class Portfolio:
    """持仓组合（内部计算用）"""

    q_yes: float = 0.0  # YES 份额
    q_no: float = 0.0  # NO 份额
    net_cost: float = 0.0  # 净成本

    def profit(self, winner: Side, settle: float = 1.0) -> float:
        """计算指定结果获胜时的利润"""
        payout = (self.q_yes if winner == "YES" else self.q_no) * settle
        return payout - self.net_cost

    def locked_profit(self, settle: float = 1.0) -> float:
        """锁定利润（无论谁赢的最小利润）"""
        return min(self.q_yes, self.q_no) * settle - self.net_cost

    @classmethod
    def from_position_context(cls, position: PositionContext) -> "Portfolio":
        """从 PositionContext 创建"""
        return cls(
            q_yes=position.yes_size,
            q_no=position.no_size,
            net_cost=position.yes_total_cost + position.no_total_cost,
        )


# ---------- 核心计算函数 ----------


def min_buy_qty_for_target_profit(
    port: Portfolio,
    side_to_buy: Side,
    raw_ask: float,
    target_profit: float = 0.0,
    settle: float = 1.0,
) -> Optional[float]:
    """计算达到目标利润的最小买入量

    只允许在 side_to_buy 上以 raw_ask 买入 x，返回最小 x，使：
        profit(YES胜) >= target_profit 且 profit(NO胜) >= target_profit

    Args:
        port: 当前持仓组合
        side_to_buy: 要买入的边 ("YES" 或 "NO")
        raw_ask: 买入价格 (0-1)
        target_profit: 目标保底利润
        settle: 结算价值（通常为 1.0）

    Returns:
        最小买入量；不可行时返回 None
    """
    p = raw_ask  # 有效买入价（无手续费）

    profit_yes = port.profit("YES", settle)
    profit_no = port.profit("NO", settle)

    if p >= settle:
        return None  # 买入价 >= 结算价，不划算

    if side_to_buy == "YES":
        # 买 YES x 后：
        # profit_YES = profit_yes + x * (settle - p)
        # profit_NO = profit_no - x * p
        lower = (target_profit - profit_yes) / (settle - p)
        upper = (profit_no - target_profit) / p
    else:
        # 买 NO x 后：
        # profit_NO = profit_no + x * (settle - p)
        # profit_YES = profit_yes - x * p
        lower = (target_profit - profit_no) / (settle - p)
        upper = (profit_yes - target_profit) / p

    x_min = max(0.0, lower)
    if upper < x_min - 1e-12:
        return None  # 不可行

    return x_min


# ---------- 策略实现 ----------


@StrategyRegistry.register("locked_profit")
class LockedProfitStrategy(BaseStrategy):
    """锁定利润策略：根据当前持仓动态计算对冲买入量"""

    DEFAULT_PARAMS = {
        "target_profit": 0.0,  # 目标保底利润，默认 0（保本）
    }

    @property
    def strategy_id(self) -> str:
        return "locked_profit"

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

        # 1. 检查是否有持仓
        if not position.has_position():
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason="无持仓，策略不适用",
            )

        # 2. 将 PositionContext 转换为 Portfolio
        port = Portfolio.from_position_context(position)

        # 3. 计算当前两边利润
        profit_yes_wins = port.profit("YES")
        profit_no_wins = port.profit("NO")
        locked = port.locked_profit()

        # 4. 获取目标利润参数
        target = self._get_param(params, "target_profit")
        try:
            target = float(target)
        except (TypeError, ValueError):
            target = 0.0

        # 构建基础元数据
        base_metadata = {
            "yes_size": position.yes_size,
            "no_size": position.no_size,
            "net_cost": port.net_cost,
            "profit_if_yes_wins": profit_yes_wins,
            "profit_if_no_wins": profit_no_wins,
            "locked_profit": locked,
            "target_profit": target,
        }

        # 5. 如果已经达到目标，HOLD
        if profit_yes_wins >= target and profit_no_wins >= target:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason=f"已锁定利润 ${locked:.2f}，两边均 >= 目标 ${target:.2f}",
                metadata=base_metadata,
            )

        # 6. 判断需要买哪边来对冲
        #    - YES 利润低 → 买 YES
        #    - NO 利润低 → 买 NO
        if profit_yes_wins < profit_no_wins:
            side_to_buy: Side = "YES"
            raw_ask = order_book.yes_best_ask
        else:
            side_to_buy = "NO"
            raw_ask = order_book.no_best_ask

        if raw_ask is None:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason=f"无 {side_to_buy} ask 价格",
                metadata=base_metadata,
            )

        # 7. 计算达到目标利润的最小买入量
        min_qty = min_buy_qty_for_target_profit(
            port, side_to_buy, raw_ask, target
        )

        if min_qty is None:
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason=f"无法达到目标利润（{side_to_buy} ask={raw_ask:.4f} 过高或仓位不平衡）",
                metadata={
                    **base_metadata,
                    "side_to_buy": side_to_buy,
                    "raw_ask": raw_ask,
                },
            )

        if min_qty < 0.01:  # 忽略过小的买入量
            return TradingSignal(
                signal_type=SignalType.HOLD,
                reason=f"对冲量过小 ({min_qty:.4f})，已接近目标",
                metadata={
                    **base_metadata,
                    "side_to_buy": side_to_buy,
                    "min_qty": min_qty,
                },
            )

        # 8. 计算买入后的预期利润
        cost = min_qty * raw_ask
        if side_to_buy == "YES":
            new_profit_yes = profit_yes_wins + min_qty * (1.0 - raw_ask)
            new_profit_no = profit_no_wins - cost
        else:
            new_profit_no = profit_no_wins + min_qty * (1.0 - raw_ask)
            new_profit_yes = profit_yes_wins - cost

        new_locked = min(new_profit_yes, new_profit_no)

        logger.info(
            f"锁定利润信号: 买入 {side_to_buy} {min_qty:.2f} @ {raw_ask:.4f}, "
            f"成本 ${cost:.2f}, 新锁定利润 ${new_locked:.2f}"
        )

        # 9. 生成买入信号
        return TradingSignal(
            signal_type=SignalType.BUY,
            yes_size=min_qty if side_to_buy == "YES" else None,
            no_size=min_qty if side_to_buy == "NO" else None,
            yes_price=raw_ask if side_to_buy == "YES" else None,
            no_price=raw_ask if side_to_buy == "NO" else None,
            reason=f"对冲买入 {side_to_buy} {min_qty:.2f} @ {raw_ask:.4f}，锁定利润 ${locked:.2f} → ${new_locked:.2f}",
            metadata={
                **base_metadata,
                "side_to_buy": side_to_buy,
                "raw_ask": raw_ask,
                "min_qty": min_qty,
                "cost": cost,
                "new_profit_if_yes_wins": new_profit_yes,
                "new_profit_if_no_wins": new_profit_no,
                "new_locked_profit": new_locked,
            },
        )
