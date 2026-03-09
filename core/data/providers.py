# -*- coding: utf-8 -*-
"""
数据提供者
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import sys
import os
import sqlite3
import zlib
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.data_fetcher import DataFetcher
from .cache_manager import CacheManager
import config


class BaseDataProvider:
    def __init__(self):
        self.fetcher = DataFetcher()
        self.cache = CacheManager()

    def fetch(self, code: str, **kwargs) -> pd.DataFrame:
        raise NotImplementedError

    def _load_from_stock_cache(self, code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """从stock_cache.db加载数据"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "core/data/stock_cache.db")

        if not os.path.exists(db_path):
            return pd.DataFrame()

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            query = "SELECT data FROM stock_cache WHERE symbol = ? AND data_type = 'daily'"
            cursor.execute(query, (code,))
            row = cursor.fetchone()
            conn.close()

            if row:
                data_blob = row[0]
                try:
                    decompressed = zlib.decompress(data_blob).decode('utf-8')
                    data_list = json.loads(decompressed)
                    df = pd.DataFrame(data_list)
                except:
                    return pd.DataFrame()

                # 转换数值列
                numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                # 过滤日期范围
                col_date = 'date'
                if col_date in df.columns:
                    df[col_date] = pd.to_datetime(df[col_date])
                    if start_date:
                        df = df[df[col_date] >= pd.to_datetime(start_date)]
                    if end_date:
                        df = df[df[col_date] <= pd.to_datetime(end_date)]

                return df

        except Exception as e:
            print(f"从stock_cache加载{code}失败: {e}")

        return pd.DataFrame()


class HistoricalDataProvider(BaseDataProvider):
    def fetch(
        self,
        code: str,
        start_date: str = None,
        end_date: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        cache_key = f"hist_{code}_{start_date}_{end_date}"

        # 尝试从本地缓存读取
        if use_cache and config.CACHE_ENABLED:
            cached_data = self.cache.get(cache_key, ttl=None)
            if cached_data is not None and not cached_data.empty:
                return cached_data

        # 从API获取
        try:
            df = self.fetcher.get_stock_history(
                symbol=code,
                start_date=start_date,
                end_date=end_date
            )

            # 如果API返回空数据，使用后备
            if df.empty:
                print(f"API返回空，尝试从stock_cache加载 {code}")
                df = self._load_from_stock_cache(code, start_date, end_date)
                if not df.empty:
                    print(f"从stock_cache加载 {code}: {len(df)} 行")
                    if use_cache and config.CACHE_ENABLED:
                        self.cache.set(cache_key, df, metadata={
                            "code": code,
                            "start_date": start_date,
                            "end_date": end_date,
                            "source": "stock_cache"
                        })
                    return df

            if not df.empty and use_cache and config.CACHE_ENABLED:
                self.cache.set(cache_key, df, metadata={
                    "code": code,
                    "start_date": start_date,
                    "end_date": end_date
                })

            return df

        except Exception as e:
            print(f"获取 {code} 历史数据失败: {e}")

        # 从stock_cache.db加载后备数据
        df = self._load_from_stock_cache(code, start_date, end_date)
        if not df.empty:
            print(f"从stock_cache加载 {code}: {len(df)} 行")
            if use_cache and config.CACHE_ENABLED:
                self.cache.set(cache_key, df, metadata={
                    "code": code,
                    "start_date": start_date,
                    "end_date": end_date,
                    "source": "stock_cache"
                })
            return df

        return pd.DataFrame()


class RealtimeDataProvider(BaseDataProvider):
    def __init__(self, lookback_days: int = 120):
        super().__init__()
        self.lookback_days = lookback_days

    def fetch(
        self,
        code: str,
        use_cache: bool = True
    ) -> pd.DataFrame:
        today = datetime.now().strftime("%Y%m%d")
        cache_key = f"realtime_{code}_{today}"

        if use_cache:
            cached_data = self.cache.get(cache_key, ttl=300)
            if cached_data is not None and not cached_data.empty:
                return cached_data

        try:
            start_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")

            df = self.fetcher.get_stock_history(
                symbol=code,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                df = self._load_from_stock_cache(code)

            if not df.empty and use_cache:
                self.cache.set(cache_key, df, metadata={
                    "code": code,
                    "fetch_time": datetime.now().isoformat()
                })

            return df

        except Exception as e:
            print(f"获取实时数据失败 {code}: {e}")

        df = self._load_from_stock_cache(code)
        if not df.empty and use_cache:
            self.cache.set(cache_key, df, metadata={
                "code": code,
                "fetch_time": datetime.now().isoformat()
            })

        return df
