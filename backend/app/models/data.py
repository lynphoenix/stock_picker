# -*- coding: utf-8 -*-
"""
数据管理相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum


class DataRepairMode(str, Enum):
    """数据补充模式"""
    AUTO = "auto"  # 自动检测缺失
    MANUAL = "manual"  # 手动指定


class RepairStatus(str, Enum):
    """补充状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DataOverview(BaseModel):
    """数据总览"""
    total_stocks: int = Field(..., description="股票总数")
    date_range: Dict[str, str] = Field(..., description="数据时间范围")
    completeness: float = Field(..., description="总体完整率 %")
    last_fetch: Dict[str, Any] = Field(..., description="最后采集信息")
    next_fetch: str = Field(..., description="下次采集时间")
    indicators: Dict[str, Dict[str, Any]] = Field(..., description="指标统计")


class StockDataItem(BaseModel):
    """股票数据项"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    start_date: str = Field(..., description="起始日期")
    end_date: str = Field(..., description="最新日期")
    total_days: int = Field(..., description="总交易日")
    available_days: int = Field(..., description="已有数据天数")
    completeness: float = Field(..., description="完整率 %")
    missing_days: int = Field(..., description="缺失天数")


class StockDataList(BaseModel):
    """股票数据列表"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页大小")
    stocks: List[StockDataItem] = Field(..., description="股票列表")


class MissingDate(BaseModel):
    """缺失日期"""
    date: str = Field(..., description="日期")
    reason: str = Field(..., description="原因")


class IndicatorStatus(BaseModel):
    """指标状态"""
    status: str = Field(..., description="状态：complete/incomplete")
    days: int = Field(..., description="已计算天数")


class DataQuality(BaseModel):
    """数据质量"""
    has_abnormal_price: bool = Field(..., description="是否有异常价格")
    has_zero_volume: bool = Field(..., description="是否有零成交量")
    qfq_status: str = Field(..., description="复权状态")


class StockDetail(BaseModel):
    """股票详情"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    list_date: str = Field(..., description="上市日期")
    data_start: str = Field(..., description="数据起始")
    data_end: str = Field(..., description="数据结束")
    total_days: int = Field(..., description="总天数")
    available_days: int = Field(..., description="已有天数")
    completeness: float = Field(..., description="完整率 %")
    missing_dates: List[MissingDate] = Field(..., description="缺失日期")
    indicators: Dict[str, IndicatorStatus] = Field(..., description="指标状态")
    data_quality: DataQuality = Field(..., description="数据质量")


class DataRepairConfig(BaseModel):
    """数据补充配置"""
    mode: DataRepairMode = Field(..., description="补充模式")
    codes: Optional[List[str]] = Field(None, description="股票代码列表（manual模式）")
    date_range: Optional[Dict[str, str]] = Field(None, description="日期范围")
    options: List[str] = Field(
        default=["daily", "qfq", "indicators"],
        description="补充选项"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "manual",
                "codes": ["688005", "688008"],
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2026-01-29"
                },
                "options": ["daily", "qfq", "indicators"]
            }
        }


class RepairTaskResponse(BaseModel):
    """补充任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: RepairStatus = Field(..., description="状态")
    progress: Optional[int] = Field(None, description="进度 %")
    total: Optional[int] = Field(None, description="总数")
    completed: Optional[int] = Field(None, description="已完成")
    current: Optional[str] = Field(None, description="当前处理")


class FetchScheduleConfig(BaseModel):
    """采集调度配置"""
    enabled: bool = Field(True, description="是否启用")
    schedule_time: str = Field("21:30", description="调度时间 HH:MM")
    retry_times: int = Field(3, description="重试次数")
    retry_interval: int = Field(10, description="重试间隔（分钟）")
    content: List[str] = Field(
        default=["daily", "basic_info", "indicators"],
        description="采集内容"
    )


class FetchScheduleStatus(BaseModel):
    """采集调度状态"""
    config: FetchScheduleConfig = Field(..., description="配置")
    last_run: Optional[Dict[str, Any]] = Field(None, description="最后运行")
    next_run: str = Field(..., description="下次运行时间")
