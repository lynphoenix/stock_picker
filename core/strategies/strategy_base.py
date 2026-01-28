# -*- coding: utf-8 -*-
"""
策略基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List
from dataclasses import dataclass
import pandas as pd


@dataclass
class StrategyResult:
    """策略结果"""
    action: str  # "buy" | "sell" | "hold"
    score: float  # 信号强度 0-100
    reasons: List[str]  # 信号原因
    confidence: float  # 置信度 0.0-1.0
    metadata: Dict = None  # 额外信息

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Strategy(ABC):
    """
    策略基类

    所有策略必须继承此类并实现抽象方法
    """

    def __init__(self, name: str, params: Dict = None):
        """
        Args:
            name: 策略名称
            params: 策略参数
        """
        self.name = name
        self.params = params or {}
        self.version = "1.0"

    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """
        返回策略所需的指标列表

        Returns:
            指标名称列表，如 ["MACD", "RSI", "MA"]
        """
        pass

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号

        Args:
            df: 包含OHLCV和指标的DataFrame

        Returns:
            StrategyResult对象
        """
        pass

    def get_params(self) -> Dict:
        """获取策略参数"""
        return self.params.copy()

    def set_params(self, params: Dict):
        """更新策略参数"""
        self.params.update(params)

    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        验证数据是否包含必需的指标

        Args:
            df: DataFrame

        Returns:
            是否有效
        """
        if df.empty:
            return False

        required = self.get_required_indicators()

        # 检查基础列
        basic_cols = ["open", "high", "low", "close", "volume"]
        for col in basic_cols:
            if col not in df.columns:
                print(f"缺少基础列: {col}")
                return False

        # 检查指标列
        for indicator in required:
            # 检查是否有对应的列（可能有前缀如 MACD_DIF）
            has_indicator = any(indicator in col for col in df.columns)
            if not has_indicator:
                print(f"缺少指标: {indicator}")
                return False

        return True

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}', version='{self.version}')>"
