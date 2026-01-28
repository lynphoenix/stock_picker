# -*- coding: utf-8 -*-
"""
风险管理模块
"""
from typing import Dict, Optional
from .portfolio import Portfolio, Position


class RiskManager:
    """
    风险管理器

    负责止损、止盈、仓位控制等风险管理功能
    """

    def __init__(self, config: Dict = None):
        """
        Args:
            config: 风险配置
                - max_positions: 最大持仓数
                - position_size: 单只持仓比例
                - stop_loss: 硬止损比例（如-0.10表示-10%）
                - trailing_stop: 移动止损比例（如0.04表示从高点回落4%）
                - take_profit_1: 第一次止盈比例
                - take_profit_2: 第二次止盈比例
        """
        default_config = {
            "max_positions": 5,
            "position_size": 0.10,  # 10%
            "stop_loss": -0.10,     # -10%
            "trailing_stop": 0.04,  # 从高点回落4%
            "take_profit_1": 0.08,  # +8%
            "take_profit_2": 0.18,  # +18%
            "tp1_sell_ratio": 0.33, # 第一次止盈卖出1/3
            "tp2_sell_ratio": 0.50, # 第二次止盈卖出1/2
        }

        self.config = {**default_config, **(config or {})}

    def can_buy(self, portfolio: Portfolio, code: str, amount: float) -> bool:
        """
        检查是否可以买入

        Args:
            portfolio: 组合对象
            code: 股票代码
            amount: 买入金额

        Returns:
            是否可以买入
        """
        # 1. 检查持仓数量
        if len(portfolio.positions) >= self.config["max_positions"]:
            return False

        # 2. 检查是否已持仓
        if code in portfolio.positions:
            return False

        # 3. 检查资金
        if amount > portfolio.cash:
            return False

        return True

    def calculate_position_size(
        self,
        portfolio: Portfolio,
        price: float
    ) -> int:
        """
        计算买入数量

        Args:
            portfolio: 组合对象
            price: 股票价格

        Returns:
            买入数量（手数）
        """
        total_value = portfolio.get_total_value()
        position_amount = total_value * self.config["position_size"]

        # 计算股数（向下取整到100股的倍数）
        shares = int(position_amount / price / 100) * 100

        return shares

    def check_stop_loss(self, position: Position) -> tuple[bool, str]:
        """
        检查是否触发止损

        Args:
            position: 持仓对象

        Returns:
            (是否止损, 原因)
        """
        profit_pct = position.profit_pct / 100

        # 1. 硬止损
        if profit_pct <= self.config["stop_loss"]:
            return True, f"硬止损({profit_pct*100:.1f}%)"

        # 2. 移动止损（只在有盈利时启用）
        if profit_pct > 0.03:  # 盈利超过3%才启用移动止损
            drawdown_from_peak = (position.current_price - position.peak_price) / position.peak_price

            if drawdown_from_peak <= -self.config["trailing_stop"]:
                return True, f"移动止损(从高点回落{abs(drawdown_from_peak)*100:.1f}%)"

        return False, ""

    def check_take_profit(
        self,
        position: Position
    ) -> tuple[bool, int, str]:
        """
        检查是否触发止盈

        Args:
            position: 持仓对象

        Returns:
            (是否止盈, 卖出数量, 原因)
        """
        profit_pct = position.profit_pct / 100

        # 第一次止盈
        if (
            profit_pct >= self.config["take_profit_1"]
            and not position.tp1_taken
        ):
            sell_shares = int(position.shares * self.config["tp1_sell_ratio"])
            position.tp1_taken = True
            return True, sell_shares, f"止盈T1({profit_pct*100:.1f}%)"

        # 第二次止盈
        if (
            profit_pct >= self.config["take_profit_2"]
            and not position.tp2_taken
        ):
            sell_shares = int(position.shares * self.config["tp2_sell_ratio"])
            position.tp2_taken = True
            return True, sell_shares, f"止盈T2({profit_pct*100:.1f}%)"

        return False, 0, ""

    def check_sell_signals(
        self,
        position: Position,
        technical_signal: str = ""
    ) -> tuple[bool, Optional[int], str]:
        """
        综合检查卖出信号

        Args:
            position: 持仓对象
            technical_signal: 技术面卖出信号（如"MACD死叉"）

        Returns:
            (是否卖出, 卖出数量, 原因)
        """
        # 1. 检查止损
        should_stop_loss, reason = self.check_stop_loss(position)
        if should_stop_loss:
            return True, None, reason  # None表示全部卖出

        # 2. 检查止盈
        should_take_profit, shares, reason = self.check_take_profit(position)
        if should_take_profit:
            return True, shares, reason

        # 3. 技术面卖出信号（只在没有盈利或盈利很少时考虑）
        if technical_signal and position.profit_pct < 2:
            return True, None, f"技术信号: {technical_signal}"

        return False, 0, ""

    def get_config(self) -> Dict:
        """获取风险配置"""
        return self.config.copy()

    def update_config(self, config: Dict):
        """更新风险配置"""
        self.config.update(config)

    def __repr__(self):
        return (
            f"<RiskManager("
            f"max_pos={self.config['max_positions']}, "
            f"stop_loss={self.config['stop_loss']*100:.0f}%, "
            f"tp1={self.config['take_profit_1']*100:.0f}%"
            f")>"
        )
