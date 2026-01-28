# -*- coding: utf-8 -*-
"""
基本面策略

基于财务指标的选股策略
"""
import pandas as pd
from typing import List
from .strategy_base import Strategy, StrategyResult


class FundamentalStrategy(Strategy):
    """
    基本面策略

    基于ROE、PE、营收增速、利润增速等指标
    """

    def __init__(self, params: dict = None):
        """
        Args:
            params: 策略参数
                - roe_min: ROE最小值 (默认8)
                - pe_max: PE最大值 (默认50)
                - revenue_growth_min: 营收增速最小值 (默认5)
                - profit_growth_min: 利润增速最小值 (默认5)
        """
        default_params = {
            "roe_min": 8.0,
            "pe_max": 50,
            "revenue_growth_min": 5.0,
            "profit_growth_min": 5.0,
        }

        if params:
            default_params.update(params)

        super().__init__("Fundamental", default_params)

    def get_required_indicators(self) -> List[str]:
        """需要的指标"""
        return ["FUNDAMENTAL"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号

        注: 基本面策略需要额外的财务数据
        这里主要是占位实现，实际使用时需要集成财务数据
        """
        return StrategyResult(
            action="hold",
            score=0,
            reasons=["基本面策略待完善"],
            confidence=0.0,
            metadata={}
        )
