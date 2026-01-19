# -*- coding: utf-8 -*-
"""
策略基类
所有交易策略都应该继承这个基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__

    @abstractmethod
    def check_buy_signal(
        self,
        hist: pd.DataFrame,
        date_idx: int,
        code: str = None
    ) -> bool:
        """
        检查买入信号

        Args:
            hist: 历史行情数据
            date_idx: 当前日期索引
            code: 股票代码（可选，用于获取额外信息）

        Returns:
            bool: 是否产生买入信号
        """
        pass

    @abstractmethod
    def check_sell_signal(
        self,
        hist: pd.DataFrame,
        date_idx: int,
        position: Dict[str, Any]
    ) -> tuple:
        """
        检查卖出信号

        Args:
            hist: 历史行情数据
            date_idx: 当前日期索引
            position: 持仓信息字典，包含:
                - shares: 持股数量
                - entry_price: 买入价格
                - entry_date: 买入日期

        Returns:
            tuple: (should_sell, sell_shares, reason)
                - should_sell: 是否卖出
                - sell_shares: 卖出数量（0表示全部卖出）
                - reason: 卖出原因说明
        """
        pass

    def get_position_size(
        self,
        cash: float,
        price: float,
        total_value: float
    ) -> int:
        """
        计算买入数量

        Args:
            cash: 可用资金
            price: 股票价格
            total_value: 总资产

        Returns:
            int: 买入股数（100的整数倍）
        """
        # 子类可以重写这个方法实现自定义仓位管理
        position_value = cash * 0.2  # 默认20%仓位
        shares = int(position_value / price / 100) * 100
        return shares

    def validate_data(self, hist: pd.DataFrame, date_idx: int) -> bool:
        """
        验证数据是否有效

        Args:
            hist: 历史数据
            date_idx: 日期索引

        Returns:
            bool: 数据是否有效
        """
        if hist is None or hist.empty:
            return False

        if date_idx < 0 or date_idx >= len(hist):
            return False

        return True

    def get_info(self) -> Dict[str, Any]:
        """
        获取策略信息

        Returns:
            策略信息字典
        """
        return {
            "name": self.name,
            "class": self.__class__.__name__,
        }
