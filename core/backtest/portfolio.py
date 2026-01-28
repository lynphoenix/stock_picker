# -*- coding: utf-8 -*-
"""
组合管理模块
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


@dataclass
class Position:
    """持仓信息"""
    code: str                    # 股票代码
    name: str                    # 股票名称
    shares: int                  # 持仓数量
    entry_price: float          # 买入价格
    entry_date: datetime        # 买入日期
    current_price: float = 0.0  # 当前价格
    peak_price: float = 0.0     # 历史最高价（用于移动止损）

    # 止盈止损标记
    tp1_taken: bool = False     # 第一次止盈是否已执行
    tp2_taken: bool = False     # 第二次止盈是否已执行

    # 附加信息
    buy_score: float = 0.0      # 买入时的信号评分
    sector: str = ""            # 所属板块

    @property
    def cost(self) -> float:
        """持仓成本"""
        return self.shares * self.entry_price

    @property
    def market_value(self) -> float:
        """当前市值"""
        return self.shares * self.current_price

    @property
    def profit(self) -> float:
        """盈亏金额"""
        return self.market_value - self.cost

    @property
    def profit_pct(self) -> float:
        """盈亏比例"""
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price * 100

    @property
    def holding_days(self) -> int:
        """持仓天数"""
        return (datetime.now() - self.entry_date).days

    def update_price(self, price: float):
        """更新当前价格"""
        self.current_price = price
        if price > self.peak_price:
            self.peak_price = price


@dataclass
class Trade:
    """交易记录"""
    date: datetime
    code: str
    name: str
    action: str              # buy | sell
    price: float
    shares: int
    amount: float
    reason: str
    profit_pct: float = 0.0  # 卖出时的盈亏比例
    holding_days: int = 0    # 卖出时的持仓天数


class Portfolio:
    """
    组合管理器

    负责管理资金、持仓、交易记录
    """

    def __init__(self, initial_capital: float = 100000):
        """
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.daily_values: List[Dict] = []

    def get_total_value(self, current_prices: Dict[str, float] = None) -> float:
        """
        获取总资产价值

        Args:
            current_prices: {code: price} 当前价格字典

        Returns:
            总资产
        """
        total = self.cash

        for code, position in self.positions.items():
            if current_prices and code in current_prices:
                position.update_price(current_prices[code])
            total += position.market_value

        return total

    def get_position_value(self) -> float:
        """获取持仓总市值"""
        return sum(pos.market_value for pos in self.positions.values())

    def get_available_cash(self, reserved_ratio: float = 0.0) -> float:
        """
        获取可用资金

        Args:
            reserved_ratio: 预留比例（0-1）

        Returns:
            可用资金
        """
        return self.cash * (1 - reserved_ratio)

    def can_buy(self, code: str, amount: float) -> bool:
        """
        检查是否可以买入

        Args:
            code: 股票代码
            amount: 买入金额

        Returns:
            是否可以买入
        """
        # 检查资金
        if amount > self.cash:
            return False

        # 检查是否已持仓
        if code in self.positions:
            return False

        return True

    def buy(
        self,
        code: str,
        name: str,
        price: float,
        shares: int,
        date: datetime,
        reason: str = "",
        buy_score: float = 0.0,
        sector: str = ""
    ) -> bool:
        """
        买入股票

        Args:
            code: 股票代码
            name: 股票名称
            price: 买入价格
            shares: 买入数量
            date: 买入日期
            reason: 买入原因
            buy_score: 买入信号评分
            sector: 所属板块

        Returns:
            是否成功
        """
        amount = price * shares

        if not self.can_buy(code, amount):
            return False

        # 扣除资金
        self.cash -= amount

        # 创建持仓
        position = Position(
            code=code,
            name=name,
            shares=shares,
            entry_price=price,
            entry_date=date,
            current_price=price,
            peak_price=price,
            buy_score=buy_score,
            sector=sector
        )

        self.positions[code] = position

        # 记录交易
        trade = Trade(
            date=date,
            code=code,
            name=name,
            action="buy",
            price=price,
            shares=shares,
            amount=amount,
            reason=reason
        )

        self.trades.append(trade)

        return True

    def sell(
        self,
        code: str,
        price: float,
        shares: int = None,
        date: datetime = None,
        reason: str = ""
    ) -> bool:
        """
        卖出股票

        Args:
            code: 股票代码
            price: 卖出价格
            shares: 卖出数量（None表示全部卖出）
            date: 卖出日期
            reason: 卖出原因

        Returns:
            是否成功
        """
        if code not in self.positions:
            return False

        position = self.positions[code]

        # 确定卖出数量
        if shares is None or shares >= position.shares:
            shares = position.shares
            # 清空持仓
            del self.positions[code]
        else:
            # 部分卖出
            position.shares -= shares

        # 回收资金
        amount = price * shares
        self.cash += amount

        # 计算盈亏
        profit_pct = (price - position.entry_price) / position.entry_price * 100
        holding_days = (date - position.entry_date).days if date else 0

        # 记录交易
        trade = Trade(
            date=date or datetime.now(),
            code=code,
            name=position.name,
            action="sell",
            price=price,
            shares=shares,
            amount=amount,
            reason=reason,
            profit_pct=profit_pct,
            holding_days=holding_days
        )

        self.trades.append(trade)

        return True

    def update_daily_value(self, date: datetime, prices: Dict[str, float]):
        """
        更新每日资产价值

        Args:
            date: 日期
            prices: {code: price} 当前价格
        """
        # 更新持仓价格
        for code, position in self.positions.items():
            if code in prices:
                position.update_price(prices[code])

        total_value = self.get_total_value()

        self.daily_values.append({
            "date": date,
            "cash": self.cash,
            "position_value": self.get_position_value(),
            "total_value": total_value,
            "positions_count": len(self.positions)
        })

    def get_trades_df(self) -> pd.DataFrame:
        """获取交易记录DataFrame"""
        if not self.trades:
            return pd.DataFrame()

        data = []
        for trade in self.trades:
            data.append({
                "date": trade.date,
                "code": trade.code,
                "name": trade.name,
                "action": trade.action,
                "price": trade.price,
                "shares": trade.shares,
                "amount": trade.amount,
                "reason": trade.reason,
                "profit_pct": trade.profit_pct,
                "holding_days": trade.holding_days
            })

        return pd.DataFrame(data)

    def get_daily_values_df(self) -> pd.DataFrame:
        """获取每日资产DataFrame"""
        if not self.daily_values:
            return pd.DataFrame()

        return pd.DataFrame(self.daily_values)

    def get_summary(self) -> Dict:
        """获取组合摘要"""
        total_value = self.get_total_value()
        total_return = (total_value - self.initial_capital) / self.initial_capital * 100

        sell_trades = [t for t in self.trades if t.action == "sell"]
        win_trades = [t for t in sell_trades if t.profit_pct > 0]

        return {
            "initial_capital": self.initial_capital,
            "current_cash": self.cash,
            "position_value": self.get_position_value(),
            "total_value": total_value,
            "total_return": total_return,
            "total_trades": len(sell_trades),
            "win_trades": len(win_trades),
            "win_rate": len(win_trades) / len(sell_trades) * 100 if sell_trades else 0,
            "positions_count": len(self.positions)
        }

    def __repr__(self):
        summary = self.get_summary()
        return (
            f"<Portfolio("
            f"capital={summary['total_value']:.2f}, "
            f"return={summary['total_return']:.2f}%, "
            f"positions={summary['positions_count']}"
            f")>"
        )
