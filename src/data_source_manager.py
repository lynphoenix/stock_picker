# -*- coding: utf-8 -*-
"""
多数据源管理器 - 支持主备切换 + 熔断机制
"""
from typing import Optional
from enum import Enum
import os
import akshare as ak
import pandas as pd
import threading
from src.fetch_result import FetchResult
from src.timeout_utils import timeout
from src.logger_config import setup_logger
from src.circuit_breaker import (
    DataSourceCircuitBreaker,
    CircuitBreakerManager,
    get_breaker_manager,
    CircuitBreakerError,
)

logger = setup_logger(__name__)

# 线程本地存储，用于baostock连接
_thread_local = threading.local()


class DataSource(Enum):
    """数据源枚举"""
    AKSHARE = "akshare"
    BAOSTOCK = "baostock"
    TUSHARE = "tushare"


class DataSourceManager:
    """多数据源管理器"""

    def __init__(self, tushare_token: Optional[str] = None):
        """
        初始化数据源管理器

        Args:
            tushare_token: Tushare Pro API token（可选）
                          - 未提供时从环境变量TUSHARE_TOKEN读取
                          - 如有token，tushare为主源（priority 1）
                          - 无token时，baostock为主源（priority 1）
        """
        # 读取tushare token（参数 > 环境变量 > config.py）
        if tushare_token is None:
            tushare_token = os.getenv('TUSHARE_TOKEN')
            if not tushare_token:
                try:
                    import config
                    tushare_token = config.TUSHARE_TOKEN
                except:
                    pass

        has_tushare = bool(tushare_token)

        # 根据是否有tushare token调整优先级
        if has_tushare:
            # 有tushare：tushare(主) → baostock(备1) → akshare(备2)
            self.sources = [
                {'name': DataSource.TUSHARE, 'priority': 1, 'enabled': True},
                {'name': DataSource.BAOSTOCK, 'priority': 2, 'enabled': True},
                {'name': DataSource.AKSHARE, 'priority': 3, 'enabled': True},
            ]
            logger.info("数据源优先级: tushare(1) → baostock(2) → akshare(3)")
        else:
            # 无tushare：baostock(主) → akshare(备)
            self.sources = [
                {'name': DataSource.BAOSTOCK, 'priority': 1, 'enabled': True},
                {'name': DataSource.TUSHARE, 'priority': 2, 'enabled': False},
                {'name': DataSource.AKSHARE, 'priority': 3, 'enabled': True},
            ]
            logger.info("数据源优先级: baostock(1) → akshare(3) [tushare未配置]")

        self.failure_counts = {src['name']: 0 for src in self.sources}

        # 初始化熔断器
        self.circuit_breakers: dict[DataSource, DataSourceCircuitBreaker] = {}
        self._init_circuit_breakers()

        # 初始化 Tushare (需要在熔断器初始化之后)
        self._init_tushare(tushare_token, has_tushare)

    def _init_circuit_breakers(self) -> None:
        """初始化各数据源的熔断器"""
        # 为每个数据源创建熔断器
        for src in self.sources:
            name = src['name'].value
            breaker = DataSourceCircuitBreaker(
                name=name,
                failure_threshold=5,      # 连续5次失败触发熔断
                success_threshold=2,      # 连续2次成功恢复
                timeout=60,             # 60秒后进入半开状态
                half_open_max_calls=3,   # 半开状态最多探测3次
            )
            self.circuit_breakers[src['name']] = breaker
            logger.info(f"CircuitBreaker initialized for {name}")

    def _init_tushare(self, tushare_token: str, has_tushare: bool) -> None:
        """初始化 Tushare"""
        self.tushare_token = tushare_token
        if has_tushare:
            try:
                import tushare as ts
                ts.set_token(tushare_token)
                self.tushare_pro = ts.pro_api()
                logger.info("Tushare Pro 初始化成功")
            except Exception as e:
                logger.warning(f"Tushare Pro 初始化失败: {e}")
                # 禁用tushare
                for src in self.sources:
                    if src['name'] == DataSource.TUSHARE:
                        src['enabled'] = False

    def fetch_with_fallback(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> FetchResult:
        """
        带降级的数据采集（带熔断机制）

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 周期
            adjust: 复权类型

        Returns:
            FetchResult
        """
        last_error = None

        # 按优先级尝试各数据源
        for source in sorted(self.sources, key=lambda x: x['priority']):
            if not source['enabled']:
                continue

            # 检查熔断器状态
            breaker = self.circuit_breakers.get(source['name'])
            if breaker and not breaker.can_execute():
                logger.info(
                    f"{source['name'].value} 熔断器状态: {breaker.state.value}, 跳过"
                )
                continue

            try:
                result = self._fetch_from_source(
                    source['name'],
                    symbol,
                    start_date,
                    end_date,
                    period,
                    adjust
                )

                if result.success:
                    # 成功，重置失败计数
                    self.failure_counts[source['name']] = 0
                    # 记录熔断器成功
                    if breaker:
                        breaker.record_success()
                    return result
                else:
                    # 该源返回了失败结果，尝试下一个源
                    last_error = result.error_message
                    self.failure_counts[source['name']] += 1
                    # 记录熔断器失败
                    if breaker:
                        breaker.record_failure()
                    logger.warning(
                        f"{source['name'].value} 采集失败: {symbol} - {result.error_message}"
                    )
                    continue

            except Exception as e:
                last_error = str(e)
                self.failure_counts[source['name']] += 1
                # 记录熔断器失败
                if breaker:
                    breaker.record_failure()
                logger.error(
                    f"{source['name'].value} 采集异常: {symbol} - {e}"
                )
                continue

        # 所有数据源都失败
        return FetchResult(
            success=False,
            data=None,
            error_type="all_sources_failed",
            error_message=f"所有数据源均失败，最后错误: {last_error}"
        )

    def _fetch_from_source(
        self,
        source: DataSource,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str,
        adjust: str
    ) -> FetchResult:
        """从指定源采集数据"""
        if source == DataSource.AKSHARE:
            return self._fetch_akshare(symbol, start_date, end_date, period, adjust)
        elif source == DataSource.BAOSTOCK:
            return self._fetch_baostock(symbol, start_date, end_date, period, adjust)
        elif source == DataSource.TUSHARE:
            return self._fetch_tushare(symbol, start_date, end_date, period, adjust)
        else:
            return FetchResult(
                success=False,
                data=None,
                error_type="unsupported_source",
                error_message=f"不支持的数据源: {source}"
            )

    @timeout(30)
    def _fetch_akshare(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str,
        adjust: str
    ) -> FetchResult:
        """从AKShare采集数据（带30秒超时）"""
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )

            # 检查是否为空
            if df is None or df.empty:
                return FetchResult(
                    success=False,
                    data=None,
                    error_type="empty_data",
                    error_message=f"AKShare返回空数据: {symbol}",
                    source="akshare"
                )

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

            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

            return FetchResult(
                success=True,
                data=df,
                source="akshare"
            )

        except Exception as e:
            error_type = type(e).__name__
            return FetchResult(
                success=False,
                data=None,
                error_type=error_type,
                error_message=str(e),
                source="akshare"
            )

    def _fetch_baostock(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str,
        adjust: str
    ) -> FetchResult:
        """从Baostock采集数据（线程安全）"""
        import baostock as bs

        try:
            # 使用线程本地存储，每个线程独立登录
            if not hasattr(_thread_local, 'bs_logged_in') or not _thread_local.bs_logged_in:
                lg = bs.login()
                if lg.error_code != '0':
                    return FetchResult(
                        success=False,
                        data=None,
                        error_type="login_failed",
                        error_message=f"Baostock登录失败: {lg.error_msg}",
                        source="baostock"
                    )
                _thread_local.bs_logged_in = True

            # 2. 转换股票代码格式: 000001 -> sz.000001, 600000 -> sh.600000
            if symbol.startswith('6'):
                bs_code = f'sh.{symbol}'
            else:
                bs_code = f'sz.{symbol}'

            # 3. 转换日期格式: 20260101 -> 2026-01-01
            if len(start_date) == 8 and start_date.isdigit():
                start_date = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}'
            if len(end_date) == 8 and end_date.isdigit():
                end_date = f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}'

            # 4. 转换周期: daily->d, weekly->w, monthly->m
            period_map = {'daily': 'd', 'weekly': 'w', 'monthly': 'm'}
            bs_period = period_map.get(period, 'd')

            # 5. 转换复权类型: qfq->1(前复权), hfq->2(后复权), ''->3(不复权)
            adjust_map = {'qfq': '1', 'hfq': '2', '': '3'}
            bs_adjust = adjust_map.get(adjust, '1')

            # 6. 查询数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency=bs_period,
                adjustflag=bs_adjust
            )

            if rs.error_code != '0':
                return FetchResult(
                    success=False,
                    data=None,
                    error_type="query_failed",
                    error_message=f"Baostock查询失败: {rs.error_msg}",
                    source="baostock"
                )

            # 7. 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())

            # 不主动logout，保持线程本地连接
            # bs.logout()

            if not data_list:
                return FetchResult(
                    success=False,
                    data=None,
                    error_type="empty_data",
                    error_message=f"Baostock返回空数据: {symbol}",
                    source="baostock"
                )

            # 8. 构建DataFrame
            df = pd.DataFrame(data_list, columns=rs.fields)

            # 9. 数据类型转换
            df['date'] = pd.to_datetime(df['date'])
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.sort_values('date').reset_index(drop=True)

            return FetchResult(
                success=True,
                data=df,
                source="baostock"
            )

        except Exception as e:
            # 出错时重置登录状态
            _thread_local.bs_logged_in = False

            return FetchResult(
                success=False,
                data=None,
                error_type=type(e).__name__,
                error_message=str(e),
                source="baostock"
            )

    @timeout(30)
    def _fetch_tushare(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str,
        adjust: str
    ) -> FetchResult:
        """从Tushare Pro采集数据"""
        if not hasattr(self, 'tushare_pro'):
            return FetchResult(
                success=False,
                data=None,
                error_type="not_initialized",
                error_message="Tushare Pro未初始化",
                source="tushare"
            )

        try:
            # 1. 转换股票代码格式: 000001 -> 000001.SZ, 600000 -> 600000.SH
            if symbol.startswith('6'):
                ts_code = f'{symbol}.SH'
            else:
                ts_code = f'{symbol}.SZ'

            # 2. 转换日期格式: 20260101 -> 20260101 (tushare用8位数字格式)
            # 不需要转换，已经是正确格式

            # 3. 查询数据
            df = self.tushare_pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                return FetchResult(
                    success=False,
                    data=None,
                    error_type="empty_data",
                    error_message=f"Tushare返回空数据: {symbol}",
                    source="tushare"
                )

            # 4. 重命名列
            df = df.rename(columns={
                'trade_date': 'date',
                'ts_code': 'code',
                # tushare的字段名已经是英文，直接使用
                'vol': 'volume',
            })

            # 5. 数据类型转换
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df = df.sort_values('date').reset_index(drop=True)

            return FetchResult(
                success=True,
                data=df,
                source="tushare"
            )

        except Exception as e:
            error_msg = str(e)
            # 检测权限错误
            if '没有访问权限' in error_msg or 'permission' in error_msg.lower():
                error_type = "permission_denied"
            else:
                error_type = type(e).__name__

            return FetchResult(
                success=False,
                data=None,
                error_type=error_type,
                error_message=error_msg,
                source="tushare"
            )

    def get_failure_stats(self) -> dict:
        """获取失败统计"""
        return {
            source['name'].value: self.failure_counts[source['name']]
            for source in self.sources
        }

    def get_circuit_breaker_status(self) -> list[dict]:
        """获取所有熔断器的状态"""
        return [
            breaker.get_status()
            for breaker in self.circuit_breakers.values()
        ]
