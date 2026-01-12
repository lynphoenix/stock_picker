# -*- coding: utf-8 -*-
"""
板块热度计算模块
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class SectorHeat:
    """板块热度分析类"""

    def __init__(self):
        self.sectors = {}
        for category, sector_list in config.TARGET_SECTORS.items():
            for sector in sector_list:
                self.sectors[sector] = category

    def get_sector_heat_ranking(self) -> pd.DataFrame:
        """
        获取板块热度排名

        热度计算指标：
        - 近3日涨跌幅
        - 成交额
        - 涨跌家数比
        - 换手率

        Returns:
            板块热度DataFrame
        """
        try:
            # 获取概念板块行情
            df = ak.stock_board_concept_name_em()

            # 筛选目标板块
            target_sectors = list(self.sectors.keys())
            df_filtered = df[df["板块名称"].isin(target_sectors)].copy()

            if df_filtered.empty:
                print("未获取到板块数据")
                return pd.DataFrame()

            # 重命名列
            df_filtered = df_filtered.rename(columns={
                "板块名称": "name",
                "最新价": "index_value",
                "涨跌幅": "change_pct",
                "成交量": "volume",
                "成交额": "amount",
            })

            # 添加分类
            df_filtered["category"] = df_filtered["name"].map(self.sectors)

            # 计算热度评分
            df_filtered["heat_score"] = self._calculate_heat_score(df_filtered)

            # 排序
            df_filtered = df_filtered.sort_values(
                "heat_score", ascending=False
            ).reset_index(drop=True)

            return df_filtered

        except Exception as e:
            print(f"获取板块热度失败: {e}")
            return pd.DataFrame()

    def _calculate_heat_score(self, df: pd.DataFrame) -> pd.Series:
        """
        计算热度评分

        评分维度：
        - 涨跌幅（40%）：涨幅越大得分越高
        - 成交额（30%）：成交额越大越活跃
        - 涨跌家数比（30%）：上涨家数/总家数
        """
        score = pd.Series(0.0, index=df.index)

        # 涨跌幅得分（归一化）
        if "change_pct" in df.columns:
            change = df["change_pct"].astype(float)
            # 负值惩罚，正值奖励
            change_score = change.apply(lambda x: max(0, x + 3) / 10)
            score += change_score * 40

        # 成交额得分（归一化）
        if "amount" in df.columns:
            amount = df["amount"].astype(float)
            min_val = amount.min()
            max_val = amount.max()
            if max_val > min_val:
                amount_score = (amount - min_val) / (max_val - min_val)
            else:
                amount_score = amount * 0 + 0.5
            score += amount_score * 30

        # 涨跌家数比得分（如果有数据）
        if "上涨家数" in df.columns and "下跌家数" in df.columns:
            up = df["上涨家数"].astype(float)
            down = df["下跌家数"].astype(float)
            total = up + down
            ratio = (up / total).fillna(0.5)
            score += ratio * 30
        else:
            # 如果没有涨跌家数数据，用涨跌幅估算
            if "change_pct" in df.columns:
                trend_score = (df["change_pct"].astype(float) + 5) / 10
                trend_score = trend_score.clip(0, 1)
                score += trend_score * 30

        return score.round(2)

    def get_stock_sector_heat(self, sector_name: str) -> float:
        """
        获取指定板块的热度百分位

        Args:
            sector_name: 板块名称

        Returns:
            热度百分位 (0-1)
        """
        ranking = self.get_sector_heat_ranking()

        if ranking.empty:
            return 0.5

        # 获取该板块的热度值
        sector_row = ranking[ranking["name"] == sector_name]

        if sector_row.empty:
            return 0.5

        heat_value = sector_row["heat_score"].values[0]
        max_heat = ranking["heat_score"].max()

        if max_heat > 0:
            return heat_value / max_heat
        return 0.5

    def get_hot_stocks_by_sector(self, sector_name: str, top_n: int = 10) -> pd.DataFrame:
        """
        获取指定板块内的热门股票

        Args:
            sector_name: 板块名称
            top_n: 返回前N只

        Returns:
            热门股票DataFrame
        """
        try:
            # 获取板块成分股行情
            df = ak.stock_board_concept_cons_em(symbol=sector_name)

            if df is None or df.empty:
                return pd.DataFrame()

            # 重命名列
            df = df.rename(columns={
                "代码": "code",
                "名称": "name",
                "最新价": "price",
                "涨跌幅": "change_pct",
                "成交量": "volume",
                "成交额": "amount",
                "换手率": "turnover_rate",
                "量比": "volume_ratio",
            })

            # 计算热度
            df["stock_heat"] = self._calculate_stock_heat(df)

            # 排序并返回前N只
            df = df.sort_values("stock_heat", ascending=False).head(top_n)
            df = df.reset_index(drop=True)

            return df

        except Exception as e:
            print(f"获取板块 {sector_name} 热门股票失败: {e}")
            return pd.DataFrame()

    def _calculate_stock_heat(self, df: pd.DataFrame) -> pd.Series:
        """
        计算个股热度
        """
        score = pd.Series(0.0, index=df.index)

        # 涨跌幅贡献
        if "change_pct" in df.columns:
            change = df["change_pct"].astype(float)
            change_score = (change + 5) / 10
            change_score = change_score.clip(0, 1)
            score += change_score * 40

        # 成交额贡献
        if "amount" in df.columns:
            amount = df["amount"].astype(float)
            min_val = amount.min()
            max_val = amount.max()
            if max_val > min_val:
                amount_score = (amount - min_val) / (max_val - min_val)
            else:
                amount_score = amount * 0 + 0.5
            score += amount_score * 30

        # 换手率贡献
        if "turnover_rate" in df.columns:
            turnover = df["turnover_rate"].astype(float)
            # 换手率2%-8%最佳
            turnover_score = 1 - abs(turnover - 5) / 10
            turnover_score = turnover_score.clip(0, 1)
            score += turnover_score * 30

        return score.round(2)


if __name__ == "__main__":
    # 测试代码
    heat = SectorHeat()

    print("=== 板块热度排名 ===")
    ranking = heat.get_sector_heat_ranking()
    print(ranking[["name", "category", "change_pct", "amount", "heat_score"]].head(10))

    print("\n=== AI板块热门股票 ===")
    hot_stocks = heat.get_hot_stocks_by_sector("人工智能", top_n=10)
    print(hot_stocks[["code", "name", "price", "change_pct", "turnover_rate", "stock_heat"]])
