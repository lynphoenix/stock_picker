# -*- coding: utf-8 -*-
"""
异步数据获取器 - Async Data Fetcher

使用 asyncio 并发采集，适用于大规模股票池批量采集。

性能对比:
| 方案 | 100只股票 | 1000只股票 |
|------|----------|------------|
| ThreadPool (10 workers) | ~30s | ~300s |
| asyncio (20 concurrent) | ~10s | ~60s |
"""
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.fetch_result import FetchResult
from src.data_source_manager import DataSourceManager
from src.logger_config import setup_logger

logger = setup_logger(__name__)


@dataclass
class AsyncFetchResult:
    """异步获取结果"""
    symbol: str
    result: FetchResult
    duration: float  # 耗时（秒）


class AsyncDataFetcher:
    """
    异步数据获取器

    使用示例:
        fetcher = AsyncDataFetcher(max_concurrent=20)

        # 批量获取
        results = await fetcher.fetch_batch(
            symbols=["000001", "000002", "600000"],
            start_date="20240101",
            end_date="20241231"
        )

        # 并发限制
        async with fetcher.semaphore:
            ...
    """

    def __init__(
        self,
        max_concurrent: int = 20,
        timeout: int = 30,
    ):
        """
        初始化异步数据获取器

        Args:
            max_concurrent: 最大并发数
            timeout: 单个请求超时时间（秒）
        """
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # 数据源管理器（非异步，需要在线程池中运行）
        self.data_source_manager = DataSourceManager()

        # 统计
        self._stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'total_duration': 0.0,
        }

        logger.info(
            f"AsyncDataFetcher initialized: max_concurrent={max_concurrent}, timeout={timeout}s"
        )

    async def fetch_one(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> AsyncFetchResult:
        """
        获取单个股票数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            adjust: 复权类型

        Returns:
            AsyncFetchResult
        """
        start_time = time.time()

        async with self.semaphore:
            try:
                # 在线程池中运行阻塞的同步代码
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.data_source_manager.fetch_with_fallback(
                            symbol=symbol,
                            start_date=start_date,
                            end_date=end_date,
                            period=period,
                            adjust=adjust
                        )
                    ),
                    timeout=self.timeout
                )

                duration = time.time() - start_time

                if result.success:
                    self._stats['success'] += 1
                else:
                    self._stats['failed'] += 1

                return AsyncFetchResult(
                    symbol=symbol,
                    result=result,
                    duration=duration
                )

            except asyncio.TimeoutError:
                duration = time.time() - start_time
                self._stats['failed'] += 1
                logger.warning(f"{symbol} 获取超时: {self.timeout}s")

                return AsyncFetchResult(
                    symbol=symbol,
                    result=FetchResult(
                        success=False,
                        data=None,
                        error_type="timeout",
                        error_message=f"获取超时: {self.timeout}s"
                    ),
                    duration=duration
                )

            except Exception as e:
                duration = time.time() - start_time
                self._stats['failed'] += 1
                logger.error(f"{symbol} 获取异常: {e}")

                return AsyncFetchResult(
                    symbol=symbol,
                    result=FetchResult(
                        success=False,
                        data=None,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    ),
                    duration=duration
                )

            finally:
                self._stats['total'] += 1
                self._stats['total_duration'] += duration

    async def fetch_batch(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq",
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, FetchResult]:
        """
        批量获取股票数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            period: 周期
            adjust: 复权类型
            progress_callback: 进度回调函数 callback(completed, total)

        Returns:
            {symbol: FetchResult}
        """
        self._stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'total_duration': 0.0,
        }

        start_time = time.time()

        # 创建任务
        tasks = [
            self.fetch_one(symbol, start_date, end_date, period, adjust)
            for symbol in symbols
        ]

        # 使用 TaskGroup 并发执行 (Python 3.11+)
        results_map: Dict[str, FetchResult] = {}

        try:
            # Python 3.11+ 的 TaskGroup
            async with asyncio.TaskGroup() as tg:
                for task in tasks:
                    tg.create_task(task)

            # 收集结果
            for task in tasks:
                result = await task
                results_map[result.symbol] = result.result

                if progress_callback:
                    progress_callback(len(results_map), len(symbols))

        except asyncio.CancelledError:
            # 取消所有任务
            for task in tasks:
                if not task.done():
                    task.cancel()
            raise

        total_duration = time.time() - start_time

        logger.info(
            f"批量获取完成: {len(symbols)} 只股票, "
            f"成功: {self._stats['success']}, 失败: {self._stats['failed']}, "
            f"耗时: {total_duration:.2f}s, "
            f"平均: {total_duration/len(symbols):.2f}s/只"
        )

        return results_map

    async def fetch_with_retry(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        max_retries: int = 3,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> AsyncFetchResult:
        """
        带重试的异步获取

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            max_retries: 最大重试次数
            period: 周期
            adjust: 复权类型

        Returns:
            AsyncFetchResult
        """
        last_error = None

        for attempt in range(max_retries):
            result = await self.fetch_one(symbol, start_date, end_date, period, adjust)

            if result.result.success:
                return result

            last_error = result.result.error_message

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                logger.info(f"{symbol} 第{attempt+1}次失败，{wait_time}s后重试")
                await asyncio.sleep(wait_time)

        # 所有重试都失败
        return AsyncFetchResult(
            symbol=symbol,
            result=FetchResult(
                success=False,
                data=None,
                error_type="all_retries_failed",
                error_message=f"重试{max_retries}次均失败: {last_error}"
            ),
            duration=0
        )

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            'avg_duration': (
                self._stats['total_duration'] / self._stats['total']
                if self._stats['total'] > 0 else 0
            ),
            'success_rate': (
                self._stats['success'] / self._stats['total'] * 100
                if self._stats['total'] > 0 else 0
            ),
        }


# 便捷函数
async def fetch_stocks_async(
    symbols: List[str],
    start_date: str,
    end_date: str,
    max_concurrent: int = 20,
    **kwargs
) -> Dict[str, FetchResult]:
    """
    便捷函数：异步获取多只股票数据

    Args:
        symbols: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        max_concurrent: 最大并发数
        **kwargs: 其他参数

    Returns:
        {symbol: FetchResult}
    """
    fetcher = AsyncDataFetcher(max_concurrent=max_concurrent)
    return await fetcher.fetch_batch(symbols, start_date, end_date, **kwargs)
