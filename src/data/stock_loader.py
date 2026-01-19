# -*- coding: utf-8 -*-
"""
股票数据加载器
支持缓存的历史数据加载
"""

import akshare as ak
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.cache import CacheManager, get_cache_manager
from settings import CACHE_EXPIRE_DAYS, DEFAULT_ADJUST


class StockLoader:
    """股票数据加载器"""

    def __init__(self, cache_manager: CacheManager = None):
        self.cache = cache_manager or get_cache_manager()

    def get_stock_list(self, market: str = "A股") -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型

        Returns:
            股票列表DataFrame
        """
        # 尝试从缓存获取
        cache_key = f"stock_list_{market}"
        cached = self.cache.get(cache_key, "data")
        if cached is not None:
            return cached

        try:
            df = ak.stock_zh_a_spot_em()

            df = df.rename(columns={
                "代码": "code",
                "名称": "name",
                "最新价": "price",
                "涨跌幅": "change_pct",
                "成交量": "volume",
                "成交额": "amount",
                "总市值": "market_cap",
                "流通市值": "float_cap",
            })

            df["symbol"] = df["code"]
            df["exchange"] = df["code"].apply(
                lambda x: "SH" if x.startswith("6") else "SZ"
            )

            result = df[["code", "symbol", "name", "exchange", "price",
                         "change_pct", "volume", "amount", "market_cap", "float_cap"]]

            # 缓存结果（缓存1天）
            self.cache.set(cache_key, result, "data")
            return result

        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_stock_history(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = DEFAULT_ADJUST,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史行情（支持缓存）

        Args:
            symbol: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            adjust: 复权类型
            use_cache: 是否使用缓存

        Returns:
            历史行情DataFrame
        """
        # 尝试从缓存获取
        cache_key = f"stock_hist_{symbol}_{start_date}_{end_date}_{adjust}"
        if use_cache:
            cached = self.cache.get(cache_key, "data")
            if cached is not None:
                return cached

        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )

            if df is not None and not df.empty:
                df = df.rename(columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                })
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)

                # 缓存结果
                if use_cache:
                    self.cache.set(cache_key, df, "data")

                return df

        except Exception as e:
            pass  # 静默失败

        return None

    def load_multiple_stocks(
        self,
        stock_list: pd.DataFrame,
        start_date: str,
        end_date: str,
        adjust: str = DEFAULT_ADJUST,
        max_stocks: int = None,
        progress_callback = None
    ) -> Dict[str, pd.DataFrame]:
        """
        批量加载多只股票的历史数据

        Args:
            stock_list: 股票列表DataFrame
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型
            max_stocks: 最大加载数量（None表示全部）
            progress_callback: 进度回调函数

        Returns:
            {code: DataFrame} 字典
        """
        result = {}

        total = len(stock_list) if max_stocks is None else min(len(stock_list), max_stocks)
        stocks_to_load = stock_list.head(total) if max_stocks else stock_list

        for i, (_, stock) in enumerate(stocks_to_load.iterrows()):
            code = stock['code']
            name = stock['name']

            hist = self.get_stock_history(code, start_date, end_date, adjust)

            if hist is not None and not hist.empty:
                hist['code'] = code
                hist['name'] = name
                hist['涨跌幅'] = hist['close'].pct_change() * 100
                result[code] = hist

            if progress_callback and (i + 1) % 100 == 0:
                progress_callback(i + 1, total, code)

        return result

    def filter_st_stocks(self, stock_list: pd.DataFrame) -> pd.DataFrame:
        """
        剔除ST股票

        Args:
            stock_list: 股票列表DataFrame

        Returns:
            过滤后的DataFrame
        """
        # 获取ST股票列表
        try:
            st_stocks = ak.st_stock_info_em()
            st_codes = set()
            if st_stocks is not None and not st_stocks.empty:
                st_codes = set(st_stocks['代码'].tolist())
        except:
            st_codes = set()

        # 通过名称过滤
        filtered = stock_list[
            ~stock_list['name'].str.contains('ST|退|暂停', na=False)
        ].copy()

        # 移除在ST列表中的股票
        if st_codes:
            filtered = filtered[~filtered['code'].isin(st_codes)]

        return filtered

    def get_sector_stocks(self, sector_name: str) -> List[str]:
        """
        获取指定板块的股票代码列表

        Args:
            sector_name: 板块名称

        Returns:
            股票代码列表
        """
        try:
            df = ak.stock_board_concept_cons_em(symbol=sector_name)
            if "代码" in df.columns:
                return df["代码"].tolist()
        except Exception:
            pass

        return []
