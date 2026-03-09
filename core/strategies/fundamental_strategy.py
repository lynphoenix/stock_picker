# -*- coding: utf-8 -*-
"""
基本面策略

基于价格趋势和成交量的简化策略
"""
import pandas as pd
from typing import List
from .strategy_base import Strategy, StrategyResult


class FundamentalStrategy(Strategy):
    """
    基本面策略 (简化版)

    使用短期均线策略:
    - 买入: 价格站上MA5均线
    - 卖出: 价格跌破MA5均线，或持仓超过指定天数
    """

    def __init__(self, params: dict = None):
        """
        Args:
            params: 策略参数
                - holding_days: 持仓天数 (默认5)
                - ma_period: 均线周期 (默认5)
        """
        default_params = {
            "holding_days": 5,
            "ma_period": 5,
        }

        if params:
            default_params.update(params)

        super().__init__("Fundamental", default_params)

    def get_required_indicators(self) -> List[str]:
        """需要的指标"""
        return ["MA"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号
        
        注意: 此策略不跟踪持仓状态，返回的信号需要由回测引擎或组合管理器
        根据实际持仓情况来决定是否执行
        """
        if df is None or len(df) < 10:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据不足"],
                confidence=0.0,
                metadata={}
            )

        try:
            params = self.params
            ma_period = params.get("ma_period", 5)
            
            # 简化版：不跟踪持仓状态，总是基于当前价格和均线的关系来判断
            # 买入条件: 价格站上均线
            # 卖出条件: 价格跌破均线
            
            recent = df.copy()
            
            if 'close' not in recent.columns:
                return StrategyResult(
                    action="hold",
                    score=0,
                    reasons=["无收盘价数据"],
                    confidence=0.0,
                    metadata={}
                )

            # 获取对应的均线列名
            ma_col = f'MA{ma_period}'
            if ma_col not in recent.columns:
                return StrategyResult(
                    action="hold",
                    score=0,
                    reasons=[f"缺少{ma_col}指标"],
                    confidence=0.0,
                    metadata={}
                )

            # 获取最新数据
            current = recent.iloc[-1]

            # 检查是否有有效数据
            if pd.isna(current[ma_col]):
                return StrategyResult(
                    action="hold",
                    score=0,
                    reasons=["均线数据不足"],
                    confidence=0.0,
                    metadata={}
                )

            price = current['close']
            ma = current[ma_col]
            
            # 简化逻辑：比较当前价格和均线
            if price > ma:
                return StrategyResult(
                    action="buy",
                    score=0.7,
                    reasons=[f"价格{price:.2f} > {ma_col}{ma:.2f}"],
                    confidence=0.7,
                    metadata={
                        "price": float(price),
                        "ma": float(ma),
                    }
                )
            else:
                return StrategyResult(
                    action="sell",
                    score=0.7,
                    reasons=[f"价格{price:.2f} < {ma_col}{ma:.2f}"],
                    confidence=0.7,
                    metadata={
                        "price": float(price),
                    }
                )

        except Exception as e:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=[f"计算错误: {str(e)}"],
                confidence=0.0,
                metadata={}
            )
