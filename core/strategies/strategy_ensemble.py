# -*- coding: utf-8 -*-
"""
策略集成器

组合多个策略，通过投票或加权平均做出最终决策
"""
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

from .strategy_base import Strategy, StrategyResult


class StrategyEnsemble(Strategy):
    """
    策略集成器

    功能：
    1. 运行多个策略
    2. 投票或加权平均
    3. 提高决策稳健性
    """

    def __init__(
        self,
        strategies: List[Tuple[Strategy, float]],
        voting_method: str = "weighted",  # "weighted" | "majority" | "unanimous"
        min_agreement: float = 0.6
    ):
        """
        Args:
            strategies: [(策略对象, 权重), ...]
            voting_method: 投票方式
                - weighted: 加权平均（推荐）
                - majority: 多数投票
                - unanimous: 一致同意
            min_agreement: 最小一致性要求（0-1）
        """
        self.strategies = strategies
        self.voting_method = voting_method
        self.min_agreement = min_agreement

        strategy_names = [s.name for s, _ in strategies]
        self.name = f"Ensemble({len(strategies)} strategies)"
        self.description = f"集成策略: {', '.join(strategy_names)}"

    def get_required_indicators(self) -> List[str]:
        """获取所有策略需要的指标（去重）"""
        all_indicators = set()
        for strategy, _ in self.strategies:
            all_indicators.update(strategy.get_required_indicators())
        return list(all_indicators)

    def _weighted_voting(
        self,
        results: List[Tuple[StrategyResult, float]]
    ) -> StrategyResult:
        """
        加权投票

        根据每个策略的权重和评分，计算加权总分
        """
        # 计算每个action的加权得分
        action_scores = {"buy": 0, "sell": 0, "hold": 0}
        total_confidence = 0
        all_reasons = []
        all_metadata = {}

        total_weight = sum(weight for _, weight in results)

        for result, weight in results:
            # 归一化权重
            norm_weight = weight / total_weight

            # 加权评分
            action_scores[result.action] += result.score * norm_weight
            total_confidence += result.confidence * norm_weight

            # 收集原因
            strategy_name = None
            for s, w in self.strategies:
                if w == weight:
                    strategy_name = s.name
                    break

            if result.action in ["buy", "sell"]:
                all_reasons.append(
                    f"[{strategy_name[:15]}] {result.action.upper()}: {result.reasons[0] if result.reasons else 'N/A'}"
                )

        # 确定最终action
        final_action = max(action_scores.items(), key=lambda x: x[1])[0]
        final_score = action_scores[final_action]

        # 计算一致性
        max_score = max(action_scores.values())
        second_score = sorted(action_scores.values(), reverse=True)[1]
        agreement = (max_score - second_score) / 100 if max_score > 0 else 0

        # 如果一致性不足，降低置信度
        if agreement < self.min_agreement:
            total_confidence *= 0.5
            all_reasons.insert(0, f"⚠️ 策略分歧(一致性{agreement:.1%})")

        return StrategyResult(
            action=final_action,
            score=final_score,
            reasons=all_reasons[:5],  # 最多显示5条
            confidence=total_confidence,
            metadata={
                "action_scores": action_scores,
                "agreement": agreement,
                "num_strategies": len(results)
            }
        )

    def _majority_voting(
        self,
        results: List[Tuple[StrategyResult, float]]
    ) -> StrategyResult:
        """
        多数投票

        每个策略一票，取票数最多的action
        """
        action_votes = {"buy": 0, "sell": 0, "hold": 0}
        action_reasons = {"buy": [], "sell": [], "hold": []}
        total_confidence = 0

        for result, weight in results:
            action_votes[result.action] += 1
            action_reasons[result.action].extend(result.reasons)
            total_confidence += result.confidence

        # 平均置信度
        total_confidence /= len(results)

        # 找出票数最多的action
        final_action = max(action_votes.items(), key=lambda x: x[1])[0]
        vote_count = action_votes[final_action]

        # 计算一致性
        agreement = vote_count / len(results)

        if agreement < self.min_agreement:
            total_confidence *= 0.5

        return StrategyResult(
            action=final_action,
            score=vote_count / len(results) * 100,
            reasons=action_reasons[final_action][:5],
            confidence=total_confidence,
            metadata={
                "votes": action_votes,
                "agreement": agreement
            }
        )

    def _unanimous_voting(
        self,
        results: List[Tuple[StrategyResult, float]]
    ) -> StrategyResult:
        """
        一致投票

        所有策略必须一致，否则返回hold
        """
        actions = [result.action for result, _ in results]

        # 检查是否一致
        if len(set(actions)) == 1:
            final_action = actions[0]
            avg_score = np.mean([result.score for result, _ in results])
            avg_confidence = np.mean([result.confidence for result, _ in results])
            all_reasons = []
            for result, _ in results:
                all_reasons.extend(result.reasons)

            return StrategyResult(
                action=final_action,
                score=avg_score,
                reasons=all_reasons[:5],
                confidence=avg_confidence,
                metadata={"unanimous": True}
            )
        else:
            # 不一致，返回hold
            return StrategyResult(
                action="hold",
                score=50,
                reasons=["策略分歧，保持观望"],
                confidence=0.3,
                metadata={
                    "unanimous": False,
                    "actions": actions
                }
            )

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号

        运行所有策略并综合决策
        """
        if df.empty:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据不足"],
                confidence=0.0,
                metadata={}
            )

        # 运行所有策略
        results = []
        for strategy, weight in self.strategies:
            try:
                result = strategy.generate_signals(df)
                results.append((result, weight))
            except Exception as e:
                print(f"⚠️  策略 {strategy.name} 执行失败: {e}")
                continue

        if not results:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["所有策略执行失败"],
                confidence=0.0,
                metadata={}
            )

        # 根据投票方式决策
        if self.voting_method == "weighted":
            return self._weighted_voting(results)
        elif self.voting_method == "majority":
            return self._majority_voting(results)
        elif self.voting_method == "unanimous":
            return self._unanimous_voting(results)
        else:
            raise ValueError(f"未知的投票方式: {self.voting_method}")


class StrategyRotation:
    """
    策略轮换器

    根据市场环境自动切换策略：
    - 牛市：动量策略
    - 熊市：价值策略
    - 震荡：均值回归策略
    """

    def __init__(self, strategies: Dict[str, Strategy]):
        """
        Args:
            strategies: {市场环境: 策略对象}
                例如: {
                    "bull": MomentumStrategy(),
                    "bear": ValueStrategy(),
                    "sideways": BollingerStrategy()
                }
        """
        self.strategies = strategies
        self.current_regime = "sideways"  # 默认震荡市

    def detect_market_regime(self, df: pd.DataFrame) -> str:
        """
        检测市场环境

        Returns:
            "bull" | "bear" | "sideways"
        """
        if len(df) < 60:
            return "sideways"

        # 计算趋势强度
        close = df["close"].values
        ma20 = df["close"].rolling(20).mean().values
        ma60 = df["close"].rolling(60).mean().values

        latest_close = close[-1]
        latest_ma20 = ma20[-1]
        latest_ma60 = ma60[-1]

        # 计算20日涨幅
        gain_20d = (latest_close / close[-20] - 1) * 100 if len(close) >= 20 else 0

        # 判断
        if latest_close > latest_ma20 > latest_ma60 and gain_20d > 8:
            return "bull"
        elif latest_close < latest_ma20 < latest_ma60 and gain_20d < -8:
            return "bear"
        else:
            return "sideways"

    def get_strategy(self, df: pd.DataFrame) -> Strategy:
        """
        根据市场环境选择策略
        """
        regime = self.detect_market_regime(df)
        self.current_regime = regime

        return self.strategies.get(regime, list(self.strategies.values())[0])

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成信号（自动选择策略）
        """
        strategy = self.get_strategy(df)
        result = strategy.generate_signals(df)

        # 添加市场环境信息
        result.metadata["market_regime"] = self.current_regime
        result.metadata["strategy_used"] = strategy.name

        result.reasons.insert(0, f"[{self.current_regime.upper()}市场] 使用{strategy.name}")

        return result
