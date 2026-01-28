# -*- coding: utf-8 -*-
"""
基本面指标计算
"""
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class FundamentalIndicators:
    """基本面指标计算类"""

    @staticmethod
    def add_fundamental_score(df: pd.DataFrame) -> pd.DataFrame:
        """
        添加基本面评分

        注: 基本面数据需要单独获取，这里主要是占位
        未来可以集成到数据流中
        """
        # 预留接口
        return df
