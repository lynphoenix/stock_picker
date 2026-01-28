# -*- coding: utf-8 -*-
"""
数据提供者
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.data_fetcher import DataFetcher
from .cache_manager import CacheManager
import config


class BaseDataProvider:
    """数据提供者基类"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.cache = CacheManager()

    def fetch(self, code: str, **kwargs) -> pd.DataFrame:
        """获取数据 - 子类实现"""
        raise NotImplementedError


class HistoricalDataProvider(BaseDataProvider):
    """
    历史数据提供者
    用于回测，提供指定时间范围的历史K线数据
    """

    def fetch(
        self,
        code: str,
        start_date: str = None,
        end_date: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取历史K线数据

        Args:
            code: 股票代码
            start_date: 开始日期 (格式: YYYYMMDD)
            end_date: 结束日期 (格式: YYYYMMDD)
            use_cache: 是否使用缓存

        Returns:
            包含 OHLCV 的 DataFrame
        """
        # 生成缓存键
        cache_key = f"hist_{code}_{start_date}_{end_date}"

        # 尝试从缓存读取
        if use_cache and config.CACHE_ENABLED:
            cached_data = self.cache.get(
                cache_key,
                ttl=config.CACHE_EXPIRE_HOURS * 3600
            )
            if cached_data is not None:
                return cached_data

        # 从API获取
        try:
            df = self.fetcher.get_stock_history(
                symbol=code,
                start_date=start_date,
                end_date=end_date
            )

            if not df.empty and use_cache and config.CACHE_ENABLED:
                self.cache.set(cache_key, df, metadata={
                    "code": code,
                    "start_date": start_date,
                    "end_date": end_date
                })

            return df

        except Exception as e:
            print(f"获取历史数据失败 {code}: {e}")
            return pd.DataFrame()


class RealtimeDataProvider(BaseDataProvider):
    """
    实时数据提供者
    用于实盘，提供最新行情 + 最近N天历史数据（用于计算指标）
    """

    def __init__(self, lookback_days: int = 120):
        """
        Args:
            lookback_days: 回溯天数，用于计算技术指标
        """
        super().__init__()
        self.lookback_days = lookback_days

    def fetch(
        self,
        code: str,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取实时数据（最新行情 + 历史数据）

        Args:
            code: 股票代码
            use_cache: 是否使用缓存（缓存时间很短，仅用于批量查询）

        Returns:
            包含最近lookback_days天的数据
        """
        # 生成缓存键
        today = datetime.now().strftime("%Y%m%d")
        cache_key = f"realtime_{code}_{today}"

        # 短期缓存（5分钟）
        if use_cache:
            cached_data = self.cache.get(cache_key, ttl=300)
            if cached_data is not None:
                return cached_data

        # 从API获取
        try:
            # 计算开始日期
            start_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")

            df = self.fetcher.get_stock_history(
                symbol=code,
                start_date=start_date,
                end_date=end_date
            )

            if not df.empty and use_cache:
                self.cache.set(cache_key, df, metadata={
                    "code": code,
                    "fetch_time": datetime.now().isoformat()
                })

            return df

        except Exception as e:
            print(f"获取实时数据失败 {code}: {e}")
            return pd.DataFrame()
