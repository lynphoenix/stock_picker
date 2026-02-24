# -*- coding: utf-8 -*-
"""
自动数据采集器 - 实现多数据源fallback、缓存、并发控制
"""
import pandas as pd
import asyncio
import random
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import baostock as bs
except ImportError:
    bs = None

try:
    import akshare as ak
except ImportError:
    ak = None

try:
    from chinese_calendar import is_holiday
except ImportError:
    is_holiday = None

import config


class FetchStatus(Enum):
    """采集状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class FetchStats:
    """采集统计"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.start_time = None
        self.end_time = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0,
            "errors": self.errors[-10:]  # 只保留最近10个错误
        }


class CircuitBreakerState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常：允许请求
    OPEN = "open"          # 熔断：拒绝请求
    HALF_OPEN = "half_open"  # 半开：允许探测


class CircuitBreaker:
    """熔断器实现"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def is_open(self) -> bool:
        """检查是否熔断中"""
        if self.state == CircuitBreakerState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed > self.timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    return False  # 半开状态，允许尝试
            return True  # 熔断中
        return False

    def record_success(self):
        """记录成功"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                print(f"✅ 熔断器 {self.name} 已关闭")
        else:
            self.failure_count = 0

    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN  # 重新熔断
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            print(f"⚠️ 熔断器 {self.name} 已打开")


class DataSourceManager:
    """多数据源管理器 - 支持Baostock(主)和AKShare(备)"""

    def __init__(self):
        self.baostock_breaker = CircuitBreaker("baostock")
        self.akshare_breaker = CircuitBreaker("akshare")
        self._bs_logged_in = False

    def _login_baostock(self):
        """登录Baostock（线程安全）"""
        if bs and not self._bs_logged_in:
            try:
                lg = bs.login()
                if lg.error_code == '0':
                    self._bs_logged_in = True
                    print(f"✅ Baostock 登录成功")
                else:
                    print(f"❌ Baostock 登录失败: {lg.error_msg}")
            except Exception as e:
                print(f"❌ Baostock 登录异常: {e}")

    def _convert_symbol_to_baostock(self, symbol: str) -> str:
        """股票代码转换为Baostock格式"""
        if symbol.startswith('6'):
            return f'sh.{symbol}'  # 沪市
        else:
            return f'sz.{symbol}'  # 深市

    def _convert_date_format(self, date: str) -> str:
        """YYYYMMDD → YYYY-MM-DD"""
        if len(date) == 8 and date.isdigit():
            return f'{date[:4]}-{date[4:6]}-{date[6:8]}'
        return date

    def fetch_from_baostock(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """从Baostock获取数据"""
        if not bs:
            return pd.DataFrame()

        if self.baostock_breaker.is_open():
            print(f"⚠️ Baostock 熔断中，跳过")
            return pd.DataFrame()

        try:
            self._login_baostock()

            bs_symbol = self._convert_symbol_to_baostock(symbol)
            bs_start = self._convert_date_format(start_date)
            bs_end = self._convert_date_format(end_date)

            # 复权类型转换
            adjust_map = {'qfq': '1', 'hfq': '2', '': '3'}
            adjustflag = adjust_map.get(adjust, '1')

            # 查询字段
            fields = "date,code,open,high,low,close,volume,amount"

            rs = bs.query_history_k_data_plus(
                bs_symbol,
                fields,
                start_date=bs_start,
                end_date=bs_end,
                frequency="d",
                adjustflag=adjustflag
            )

            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                self.baostock_breaker.record_success()
                return df
            else:
                self.baostock_breaker.record_failure()
                return pd.DataFrame()

        except Exception as e:
            print(f"❌ Baostock 查询失败 {symbol}: {e}")
            self.baostock_breaker.record_failure()
            return pd.DataFrame()

    def fetch_from_akshare(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """从AKShare获取数据"""
        if not ak:
            return pd.DataFrame()

        if self.akshare_breaker.is_open():
            print(f"⚠️ AKShare 熔断中，跳过")
            return pd.DataFrame()

        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )

            if df is not None and not df.empty:
                # 重命名列
                df = df.rename(columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                })
                df["date"] = pd.to_datetime(df["date"]).dt.strftime('%Y-%m-%d')
                df["code"] = symbol
                self.akshare_breaker.record_success()
                return df
            else:
                self.akshare_breaker.record_failure()
                return pd.DataFrame()

        except Exception as e:
            print(f"❌ AKShare 查询失败 {symbol}: {e}")
            self.akshare_breaker.record_failure()
            return pd.DataFrame()

    def fetch_with_fallback(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> Dict[str, Any]:
        """
        故障转移采集 - 依次尝试各个数据源

        Returns:
            {
                "success": bool,
                "data": pd.DataFrame,
                "error_message": str,
                "source": str
            }
        """
        # 1. 尝试 Baostock (主数据源)
        if not self.baostock_breaker.is_open():
            df = self.fetch_from_baostock(symbol, start_date, end_date, adjust)
            if not df.empty:
                return {
                    "success": True,
                    "data": df,
                    "error_message": "",
                    "source": "baostock"
                }

        # 2. 尝试 AKShare (备用数据源)
        if not self.akshare_breaker.is_open():
            df = self.fetch_from_akshare(symbol, start_date, end_date, adjust)
            if not df.empty:
                return {
                    "success": True,
                    "data": df,
                    "error_message": "",
                    "source": "akshare"
                }

        # 3. 全部失败
        return {
            "success": False,
            "data": pd.DataFrame(),
            "error_message": "所有数据源均失败",
            "source": None
        }


class SQLiteCacheManager:
    """SQLite缓存管理器"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "stock_cache.db"
        )
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        import sqlite3
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                data_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                data BLOB NOT NULL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, data_type, start_date, end_date)
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON stock_cache(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dates ON stock_cache(start_date, end_date)")

        conn.commit()
        conn.close()

    def get(self, symbol: str, data_type: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """读取缓存"""
        import sqlite3
        import zlib

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT data FROM stock_cache
                WHERE symbol = ? AND data_type = ? AND start_date = ? AND end_date = ?
            """, (symbol, data_type, start_date, end_date))

            row = cursor.fetchone()
            conn.close()

            if row:
                # 解压缩数据
                compressed_data = row[0]
                json_str = zlib.decompress(compressed_data).decode('utf-8')
                data = json.loads(json_str)
                return pd.DataFrame(data)

        except Exception as e:
            print(f"缓存读取失败: {e}")

        return None

    def set(
        self,
        symbol: str,
        data_type: str,
        start_date: str,
        end_date: str,
        data: pd.DataFrame,
        source: str = None
    ):
        """写入缓存"""
        import sqlite3
        import zlib

        try:
            # 压缩数据
            json_str = data.to_json(orient='records', force_ascii=False)
            compressed_data = zlib.compress(json_str.encode('utf-8'))

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO stock_cache
                (symbol, data_type, start_date, end_date, data, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (symbol, data_type, start_date, end_date, compressed_data, source))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"缓存写入失败: {e}")

    def is_valid(self, symbol: str, data_type: str, start_date: str, end_date: str) -> bool:
        """检查缓存是否有效"""
        df = self.get(symbol, data_type, start_date, end_date)
        return df is not None and not df.empty


class AutoDataFetcher:
    """
    自动数据采集器

    设计要点:
    1. 支持定时/手动两种触发方式
    2. 增量采集：检查缓存，只采集缺失数据
    3. 并发控制：避免对数据源压力过大
    4. 随机延迟：避免API限流
    5. 采集统计：记录成功/失败/跳过
    """

    def __init__(self):
        self.data_source_manager = DataSourceManager()
        self.cache = SQLiteCacheManager()
        self.stats = FetchStats()
        self.status = FetchStatus.IDLE
        self.current_task = None
        self._stop_requested = False

    def should_fetch_today(self, date: datetime = None) -> bool:
        """
        判断今日是否为交易日

        Args:
            date: 可选，指定日期，默认今天

        Returns:
            True: 是交易日
            False: 非交易日（周末或节假日）
        """
        if date is None:
            date = datetime.now()

        # 1. 检查周末
        # Monday = 0, Sunday = 6
        if date.weekday() >= 5:
            print(f"⏸️ {date.strftime('%Y-%m-%d')} 是周末，跳过")
            return False

        # 2. 检查节假日
        if is_holiday:
            if is_holiday(date):
                print(f"⏸️ {date.strftime('%Y-%m-%d')} 是节假日，跳过")
                return False

        return True

    def get_stock_list(self, stock_pool: str = "all") -> List[str]:
        """
        获取股票代码列表

        Args:
            stock_pool: 股票池名称 (all/AI软件/半导体/机器人)

        Returns:
            股票代码列表
        """
        # 1. 优先使用配置的股票池
        if stock_pool != "all" and stock_pool in config.CURATED_STOCK_POOLS:
            return config.CURATED_STOCK_POOLS[stock_pool]

        # 2. 合并所有配置的股票池
        all_stocks = []
        for pool_stocks in config.CURATED_STOCK_POOLS.values():
            all_stocks.extend(pool_stocks)

        # 3. 去重返回
        return list(set(all_stocks))

    def is_cache_valid(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        data_type: str = "daily"
    ) -> bool:
        """
        检查缓存是否有效

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            data_type: 数据类型

        Returns:
            True: 缓存有效
            False: 需要重新采集
        """
        return self.cache.is_valid(symbol, data_type, start_date, end_date)

    async def fetch_daily_data(
        self,
        stock_pool: str = "all",
        start_date: str = None,
        end_date: str = None,
        max_concurrent: int = 10,
        retry_times: int = 3,
        on_progress: Callable = None
    ) -> Dict[str, Any]:
        """
        执行每日数据采集

        Args:
            stock_pool: 股票池 (all/AI软件/半导体/机器人)
            start_date: 开始日期 (YYYYMMDD)，默认30天前
            end_date: 结束日期 (YYYYMMDD)，默认今天
            max_concurrent: 最大并发数
            retry_times: 失败重试次数
            on_progress: 进度回调函数

        Returns:
            {
                "status": "completed",
                "total": int,
                "success": int,
                "failed": int,
                "skipped": int,
                "duration": float,
                "errors": [...]
            }
        """
        # 初始化参数
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        # 获取股票列表
        stock_list = self.get_stock_list(stock_pool)
        if not stock_list:
            return {
                "status": "error",
                "message": "股票列表为空",
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0,
                "errors": []
            }

        # 重置统计
        self.stats.reset()
        self.stats.total = len(stock_list)
        self.stats.start_time = datetime.now()
        self.status = FetchStatus.RUNNING
        self._stop_requested = False

        print(f"🚀 开始采集 {len(stock_list)} 只股票 ({start_date} ~ {end_date})")
        print(f"📊 并发数: {max_concurrent}, 重试次数: {retry_times}")

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(symbol: str) -> Dict[str, Any]:
            """带并发控制的采集"""
            if self._stop_requested:
                return {"symbol": symbol, "status": "stopped"}

            async with semaphore:
                # 检查缓存
                if self.is_cache_valid(symbol, start_date, end_date):
                    self.stats.skipped += 1
                    return {"symbol": symbol, "status": "skipped", "reason": "cache_valid"}

                # 随机延迟 0-2秒，避免API限流
                await asyncio.sleep(random.uniform(0, 2))

                # 带重试的采集
                result = await self._fetch_with_retry(symbol, start_date, end_date, retry_times)

                if result["success"]:
                    self.stats.success += 1
                    # 保存到缓存
                    if not result["data"].empty:
                        self.cache.set(
                            symbol=symbol,
                            data_type="daily",
                            start_date=start_date,
                            end_date=end_date,
                            data=result["data"],
                            source=result["source"]
                        )
                else:
                    self.stats.failed += 1
                    self.stats.errors.append({
                        "symbol": symbol,
                        "error": result.get("error_message", "未知错误")
                    })

                # 进度回调
                if on_progress:
                    on_progress(self.stats.to_dict())

                return result

        # 执行所有采集任务
        tasks = [fetch_with_semaphore(symbol) for symbol in stock_list]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 完成
        self.stats.end_time = datetime.now()
        self.status = FetchStatus.COMPLETED if not self._stop_requested else FetchStatus.STOPPED

        result = self.stats.to_dict()
        result["status"] = "completed" if self.status == FetchStatus.COMPLETED else "stopped"

        print(f"✅ 采集完成: 成功 {self.stats.success}, 失败 {self.stats.failed}, 跳过 {self.stats.skipped}")

        return result

    def fetch_daily_data_sync(
        self,
        stock_pool: str = "all",
        start_date: str = None,
        end_date: str = None,
        max_concurrent: int = 10,
        retry_times: int = 3,
        on_progress: Callable = None
    ) -> Dict[str, Any]:
        """
        同步版本的每日数据采集（供调度器使用）

        Args:
            stock_pool: 股票池 (all/AI软件/半导体/机器人)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            max_concurrent: 最大并发数
            retry_times: 失败重试次数
            on_progress: 进度回调函数

        Returns:
            {
                "status": "completed",
                "total": int,
                "success": int,
                "failed": int,
                "skipped": int,
                "duration": float,
                "errors": [...]
            }
        """
        return asyncio.run(self.fetch_daily_data(
            stock_pool=stock_pool,
            start_date=start_date,
            end_date=end_date,
            max_concurrent=max_concurrent,
            retry_times=retry_times,
            on_progress=on_progress
        ))

    async def _fetch_with_retry(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        retry_times: int
    ) -> Dict[str, Any]:
        """带重试的采集"""
        for attempt in range(retry_times):
            try:
                result = self.data_source_manager.fetch_with_fallback(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )

                if result["success"]:
                    return result

                if attempt < retry_times - 1:
                    print(f"⚠️ {symbol} 第{attempt + 1}次失败，{result.get('error_message')}，重试中...")
                    await asyncio.sleep(1)  # 重试前等待

            except Exception as e:
                print(f"❌ {symbol} 第{attempt + 1}次异常: {e}")
                if attempt < retry_times - 1:
                    await asyncio.sleep(1)

        return {
            "success": False,
            "data": pd.DataFrame(),
            "error_message": f"重试{retry_times}次后仍失败",
            "source": None
        }

    def stop(self):
        """停止采集"""
        self._stop_requested = True
        self.status = FetchStatus.STOPPED
        print("🛑 采集已停止")

    def get_status(self) -> Dict[str, Any]:
        """获取当前采集状态"""
        return {
            "status": self.status.value,
            "stats": self.stats.to_dict()
        }


# ============= 测试代码 =============
if __name__ == "__main__":
    fetcher = AutoDataFetcher()

    # 测试1: 判断今日是否为交易日
    print("=== 测试 should_fetch_today ===")
    print(f"今天({datetime.now().strftime('%Y-%m-%d')}): {fetcher.should_fetch_today()}")

    # 测试周六
    saturday = datetime(2026, 2, 28)
    print(f"周六({saturday.strftime('%Y-%m-%d')}): {fetcher.should_fetch_today(saturday)}")

    # 测试周日
    sunday = datetime(2026, 3, 1)
    print(f"周日({sunday.strftime('%Y-%m-%d')}): {fetcher.should_fetch_today(sunday)}")

    # 测试2: 获取股票列表
    print("\n=== 测试 get_stock_list ===")
    stocks = fetcher.get_stock_list("all")
    print(f"全部股票: {len(stocks)} 只")
    print(stocks[:5])

    ai_stocks = fetcher.get_stock_list("AI软件")
    print(f"AI软件: {len(ai_stocks)} 只")

    # 测试3: 缓存检查
    print("\n=== 测试缓存 ===")
    print(f"600000 缓存有效: {fetcher.is_cache_valid('600000', '20250101', '20250110')}")

    # 测试4: 单股票采集 (同步测试)
    print("\n=== 测试单股票采集 ===")
    result = fetcher.data_source_manager.fetch_with_fallback(
        symbol="600000",
        start_date="20250101",
        end_date="20250110"
    )
    print(f"采集成功: {result['success']}")
    print(f"数据源: {result['source']}")
    if not result['data'].empty:
        print(result['data'].head())
