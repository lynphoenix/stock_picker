# -*- coding: utf-8 -*-
"""
策略模块
"""

from .strategy_base import Strategy, StrategyResult
from .strategy_manager import StrategyManager

# 技术策略
from .macd_rsi_strategy import MACDRSIStrategy
from .ma_crossover_strategy import MACrossoverStrategy
from .bollinger_strategy import BollingerStrategy
from .momentum_strategy import MomentumStrategy
from .multi_factor_strategy import MultiFactorStrategy
from .original_signal_strategy import OriginalSignalStrategy

# 基本面策略
from .fundamental_strategy import FundamentalStrategy

# 策略组合
from .strategy_ensemble import StrategyEnsemble, StrategyRotation

__all__ = [
    # Base
    "Strategy",
    "StrategyResult",
    "StrategyManager",

    # Technical Strategies
    "MACDRSIStrategy",
    "MACrossoverStrategy",
    "BollingerStrategy",
    "MomentumStrategy",
    "MultiFactorStrategy",
    "OriginalSignalStrategy",

    # Fundamental
    "FundamentalStrategy",

    # Ensemble
    "StrategyEnsemble",
    "StrategyRotation",
]
