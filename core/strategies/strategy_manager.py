# -*- coding: utf-8 -*-
"""
策略管理器
"""
from typing import Dict, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from .strategy_base import Strategy, StrategyResult
from .macd_rsi_strategy import MACDRSIStrategy
from .fundamental_strategy import FundamentalStrategy
from core.data import DataManager


class StrategyManager:
    """
    策略管理器

    负责策略的注册、获取和执行
    """

    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.data_manager = DataManager()
        self._register_builtin_strategies()

    def _register_builtin_strategies(self):
        """注册内置策略"""
        # MACD + RSI 策略
        self.register(MACDRSIStrategy())

        # 基本面策略
        self.register(FundamentalStrategy())

    def register(self, strategy: Strategy):
        """
        注册策略

        Args:
            strategy: 策略对象
        """
        self.strategies[strategy.name] = strategy
        print(f"已注册策略: {strategy.name}")

    def get_strategy(self, name: str) -> Strategy:
        """
        获取策略

        Args:
            name: 策略名称

        Returns:
            策略对象

        Raises:
            ValueError: 如果策略不存在
        """
        if name not in self.strategies:
            raise ValueError(
                f"未找到策略: {name}\n"
                f"可用策略: {self.list_strategies()}"
            )

        return self.strategies[name]

    def list_strategies(self) -> List[str]:
        """列出所有策略"""
        return list(self.strategies.keys())

    def get_strategy_info(self, name: str) -> Dict:
        """
        获取策略信息

        Args:
            name: 策略名称

        Returns:
            策略信息字典
        """
        strategy = self.get_strategy(name)

        return {
            "name": strategy.name,
            "version": strategy.version,
            "required_indicators": strategy.get_required_indicators(),
            "params": strategy.get_params(),
        }

    def run_strategy(
        self,
        strategy_name: str,
        code: str,
        mode: str = "realtime",
        **kwargs
    ) -> StrategyResult:
        """
        运行指定策略

        Args:
            strategy_name: 策略名称
            code: 股票代码
            mode: 数据模式 ("realtime" | "historical" | "latest")
            **kwargs: 传递给DataManager.get_data的其他参数

        Returns:
            StrategyResult对象
        """
        # 1. 获取策略
        strategy = self.get_strategy(strategy_name)

        # 2. 获取数据
        df = self.data_manager.get_data(code, mode=mode, **kwargs)

        if df.empty:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据获取失败"],
                confidence=0.0
            )

        # 3. 添加策略需要的指标
        required_indicators = strategy.get_required_indicators()
        df = self.data_manager.add_indicators(df, required_indicators)

        # 4. 生成信号
        result = strategy.generate_signals(df)

        return result

    def batch_run(
        self,
        strategy_name: str,
        codes: List[str],
        mode: str = "realtime",
        **kwargs
    ) -> Dict[str, StrategyResult]:
        """
        批量运行策略

        Args:
            strategy_name: 策略名称
            codes: 股票代码列表
            mode: 数据模式
            **kwargs: 其他参数

        Returns:
            {code: StrategyResult} 字典
        """
        results = {}

        for code in codes:
            try:
                result = self.run_strategy(strategy_name, code, mode=mode, **kwargs)
                results[code] = result
            except Exception as e:
                print(f"运行策略失败 {code}: {e}")
                results[code] = StrategyResult(
                    action="hold",
                    score=0,
                    reasons=[f"执行失败: {str(e)}"],
                    confidence=0.0
                )

        return results
