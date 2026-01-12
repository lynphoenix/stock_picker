# -*- coding: utf-8 -*-
"""
基本面筛选模块
"""
import pandas as pd
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.data_fetcher import DataFetcher


class FundamentalFilter:
    """基本面筛选类"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.filters = config.FUNDAMENTAL_FILTERS

    def filter_by_fundamentals(
        self,
        stock_list: List[str],
        category: str = ""
    ) -> pd.DataFrame:
        """
        根据基本面指标筛选股票

        Args:
            stock_list: 股票代码列表
            category: 所属板块类别

        Returns:
            符合条件的股票DataFrame
        """
        results = []

        for code in stock_list:
            try:
                fundamental = self.fetcher.get_stock_fundamentals(code)

                if not fundamental:
                    continue

                # 检查是否符合筛选条件
                if self._check_filters(fundamental):
                    fundamental["category"] = category
                    results.append(fundamental)

            except Exception as e:
                print(f"分析 {code} 基本面失败: {e}")
                continue

        df = pd.DataFrame(results)

        if not df.empty:
            # 计算综合评分
            df["score"] = self._calculate_score(df)
            df = df.sort_values("score", ascending=False).reset_index(drop=True)

        return df

    def _check_filters(self, fundamental: Dict) -> bool:
        """检查是否符合筛选条件"""

        # PE不能为负且不超过最大值
        pe = fundamental.get("pe", 999)
        if pe < 0 or pe > self.filters["pe_max"]:
            return False

        # ROE符合最小值
        if fundamental.get("roe", 0) < self.filters["roe_min"]:
            return False

        # 营收增速符合最小值
        if fundamental.get("revenue_growth", -999) < self.filters["revenue_growth_min"]:
            return False

        # 利润增速符合最小值
        if fundamental.get("profit_growth", -999) < self.filters["profit_growth_min"]:
            return False

        return True

    def _calculate_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算综合评分

        评分维度：
        - ROE越高越好（权重30%）
        - 营收增速越高越好（权重25%）
        - 利润增速越高越好（权重25%）
        - PE合理适中（权重20%）
        """
        # 归一化处理
        def normalize(series):
            min_val = series.min()
            max_val = series.max()
            if max_val == min_val:
                return series * 0 + 0.5
            return (series - min_val) / (max_val - min_val)

        score = pd.Series(0.0, index=df.index)

        # ROE得分
        if "roe" in df.columns:
            score += normalize(df["roe"]) * 30

        # 营收增速得分
        if "revenue_growth" in df.columns:
            score += normalize(df["revenue_growth"].clip(lower=0)) * 25

        # 利润增速得分
        if "profit_growth" in df.columns:
            score += normalize(df["profit_growth"].clip(lower=0)) * 25

        # PE得分（适中为好，10-30最佳）
        if "pe" in df.columns:
            pe_score = (1 - ((df["pe"] - 20) / 50).abs()).clip(0, 1)
            score += pe_score * 20

        return score.round(2)


if __name__ == "__main__":
    # 测试代码
    filter = FundamentalFilter()

    # 测试筛选AI板块
    ai_stocks = filter.fetcher.get_sector_stocks("人工智能")
    result = filter.filter_by_fundamentals(ai_stocks[:20], "AI")

    print(f"符合条件的股票: {len(result)}")
    print(result[["code", "name", "pe", "roe", "revenue_growth", "profit_growth", "score"]].head(10))
