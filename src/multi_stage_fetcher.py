# -*- coding: utf-8 -*-
"""
多阶段数据获取器 - Multi-Stage Data Fetcher

支持数据获取的多阶段降级策略:
1. realtime (5s timeout) - 实时行情
2. daily (30s timeout)  - 日线数据
3. historical (300s timeout) - 历史数据

当高优先级数据获取失败时，自动降级到下一阶段。
"""
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.fetch_result import FetchResult
from src.data_source_manager import DataSourceManager
from src.timeout_utils import timeout
from src.logger_config import setup_logger

logger = setup_logger(__name__)


class DataStage(Enum):
    """数据获取阶段"""
    REALTIME = "realtime"    # 实时行情
    DAILY = "daily"          # 日线数据
    HISTORICAL = "historical"  # 历史数据


@dataclass
class StageConfig:
    """阶段配置"""
    stage: DataStage
    timeout: int           # 超时时间（秒）
    priority_sources: list  # 优先使用的数据源
    description: str


# 默认阶段配置
DEFAULT_STAGES = [
    StageConfig(
        stage=DataStage.REALTIME,
        timeout=5,
        priority_sources=["tushare"],
        description="实时行情（5秒超时）"
    ),
    StageConfig(
        stage=DataStage.DAILY,
        timeout=30,
        priority_sources=["baostock", "akshare"],
        description="日线数据（30秒超时）"
    ),
    StageConfig(
        stage=DataStage.HISTORICAL,
        timeout=300,
        priority_sources=["baostock"],
        description="历史数据（5分钟超时）"
    ),
]


class MultiStageDataFetcher:
    """
    多阶段数据获取器

    使用示例:
        fetcher = MultiStageDataFetcher()

        # 获取最新收盘价（自动降级）
        result = fetcher.fetch_latest("000001")

        # 获取历史数据
        result = fetcher.fetch_historical(
            "000001",
            start_date="20200101",
            end_date="20231231"
        )

        # 获取指定阶段数据
        result = fetcher.fetch("000001", stage=DataStage.DAILY)
    """

    def __init__(
        self,
        stages: list[StageConfig] = None,
        use_fallback: bool = True,
    ):
        """
        初始化多阶段数据获取器

        Args:
            stages: 阶段配置列表
            use_fallback: 是否启用自动降级
        """
        self.stages = stages or DEFAULT_STAGES
        self.use_fallback = use_fallback
        self.data_source_manager = DataSourceManager()

        # 统计
        self._stage_stats = {
            stage.stage.value: {"success": 0, "failed": 0, "fallback": 0}
            for stage in self.stages
        }

        logger.info(
            f"MultiStageDataFetcher initialized with {len(self.stages)} stages"
        )

    def fetch(
        self,
        symbol: str,
        stage: DataStage = None,
        start_date: str = None,
        end_date: str = None,
        adjust: str = "qfq"
    ) -> FetchResult:
        """
        获取数据（指定阶段）

        Args:
            symbol: 股票代码
            stage: 数据阶段（默认自动选择）
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型

        Returns:
            FetchResult
        """
        # 如果没有指定阶段，使用默认策略
        if stage is None:
            return self.fetch_with_fallback(symbol, start_date, end_date, adjust)

        return self._fetch_by_stage(symbol, stage, start_date, end_date, adjust)

    def fetch_latest(self, symbol: str) -> FetchResult:
        """
        获取最新数据（自动降级）

        优先级: realtime → daily → historical

        Args:
            symbol: 股票代码

        Returns:
            FetchResult
        """
        return self.fetch_with_fallback(symbol, None, None, "qfq")

    def fetch_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq"
    ) -> FetchResult:
        """
        获取历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            adjust: 复权类型

        Returns:
            FetchResult
        """
        # 优先用 daily，失败则降级到 historical
        result = self._fetch_by_stage(
            symbol, DataStage.DAILY, start_date, end_date, adjust
        )

        if not result.success and self.use_fallback:
            logger.info(f"DAILY failed, falling back to HISTORICAL for {symbol}")
            self._stage_stats["daily"]["fallback"] += 1
            result = self._fetch_by_stage(
                symbol, DataStage.HISTORICAL, start_date, end_date, adjust
            )

        return result

    def fetch_with_fallback(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str
    ) -> FetchResult:
        """
        带降级的数据获取

        自动按优先级尝试各阶段:
        1. realtime (5s) - 实时数据
        2. daily (30s)  - 日线数据
        3. historical (300s) - 历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型

        Returns:
            FetchResult
        """
        last_error = None

        for stage_config in self.stages:
            logger.debug(
                f"Trying {stage_config.stage.value} for {symbol} "
                f"(timeout={stage_config.timeout}s)"
            )

            result = self._fetch_by_stage(
                symbol,
                stage_config.stage,
                start_date,
                end_date,
                adjust,
                timeout_seconds=stage_config.timeout
            )

            if result.success:
                self._stage_stats[stage_config.stage.value]["success"] += 1
                return result
            else:
                self._stage_stats[stage_config.stage.value]["failed"] += 1
                last_error = result.error_message
                logger.warning(
                    f"{stage_config.stage.value} failed for {symbol}: {last_error}"
                )

                if not self.use_fallback:
                    break

        # 所有阶段都失败
        return FetchResult(
            success=False,
            data=None,
            error_type="all_stages_failed",
            error_message=f"所有阶段均失败: {last_error}"
        )

    def _fetch_by_stage(
        self,
        symbol: str,
        stage: DataStage,
        start_date: Optional[str],
        end_date: Optional[str],
        adjust: str,
        timeout_seconds: int = None
    ) -> FetchResult:
        """
        按阶段获取数据

        Args:
            symbol: 股票代码
            stage: 数据阶段
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型
            timeout_seconds: 超时时间

        Returns:
            FetchResult
        """
        # 根据阶段确定日期范围
        if start_date is None or end_date is None:
            from datetime import datetime, timedelta
            today = datetime.now().strftime("%Y%m%d")

            if stage == DataStage.REALTIME:
                # 实时：最近30天
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
                end_date = today
            elif stage == DataStage.DAILY:
                # 日线：最近365天
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                end_date = today
            else:
                # 历史：默认3年
                start_date = (datetime.now() - timedelta(days=1095)).strftime("%Y%m%d")
                end_date = today

        # 根据阶段选择数据源优先级
        stage_config = self._get_stage_config(stage)
        if stage_config:
            # 临时调整数据源优先级
            original_sources = self.data_source_manager.sources.copy()
            self._adjust_source_priority(stage_config.priority_sources)

        try:
            # 使用数据源管理器获取
            result = self.data_source_manager.fetch_with_fallback(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                period="daily",
                adjust=adjust
            )

            # 添加阶段信息
            if result.success:
                result.data_source = f"{stage.value}:{result.source}"

            return result

        finally:
            # 恢复原始数据源优先级
            if stage_config:
                self.data_source_manager.sources = original_sources

    def _get_stage_config(self, stage: DataStage) -> Optional[StageConfig]:
        """获取阶段配置"""
        for config in self.stages:
            if config.stage == stage:
                return config
        return None

    def _adjust_source_priority(self, priority_sources: list) -> None:
        """调整数据源优先级"""
        sources = self.data_source_manager.sources
        priority_map = {name: idx for idx, name in enumerate(priority_sources)}

        # 按指定优先级排序
        def sort_key(src):
            name = src['name'].value
            if name in priority_map:
                return priority_map[name]
            return len(priority_sources) + src['priority']

        sources.sort(key=sort_key)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "stages": self._stage_stats,
            "total_success": sum(s["success"] for s in self._stage_stats.values()),
            "total_failed": sum(s["failed"] for s in self._stage_stats.values()),
            "total_fallback": sum(s["fallback"] for s in self._stage_stats.values()),
        }

    def reset_stats(self) -> None:
        """重置统计"""
        for key in self._stage_stats:
            self._stage_stats[key] = {"success": 0, "failed": 0, "fallback": 0}


# 全局实例
_global_fetcher: Optional[MultiStageDataFetcher] = None


def get_multi_stage_fetcher() -> MultiStageDataFetcher:
    """获取全局多阶段数据获取器"""
    global _global_fetcher
    if _global_fetcher is None:
        _global_fetcher = MultiStageDataFetcher()
    return _global_fetcher
