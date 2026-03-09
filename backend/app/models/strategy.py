# -*- coding: utf-8 -*-
"""
策略相关数据模型 - 包含CRUD模型和AI生成模型
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


# ===================== 原有CRUD模型 =====================

class StrategyBase(BaseModel):
    """策略基础模型"""
    name: str = Field(..., description="策略名称")
    description: str = Field("", description="策略描述")
    params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")


class StrategyCreate(StrategyBase):
    """创建策略"""
    code: str = Field(..., description="策略代码")


class StrategyUpdate(BaseModel):
    """更新策略"""
    name: Optional[str] = None
    description: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    code: Optional[str] = None


class StrategyResponse(StrategyBase):
    """策略响应"""
    id: str = Field(..., description="策略ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    performance_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="历史回测表现"
    )


class StrategyDetailResponse(StrategyResponse):
    """策略详情响应（包含代码）"""
    code: str = Field(..., description="策略源代码")


# ===================== 新增AI生成模型 =====================

class GenerateStrategyRequest(BaseModel):
    """AI生成策略请求"""
    description: str = Field(..., description="自然语言策略描述", min_length=10)
    name: str = Field(..., description="策略名称", min_length=1)
    stock_pool: Optional[list[str]] = Field(default_factory=lambda: ["000001", "600000"], description="股票池")
    start_date: Optional[str] = Field("20250101", description="开始日期 YYYYMMDD")
    end_date: Optional[str] = Field("20251231", description="结束日期 YYYYMMDD")
    initial_capital: Optional[float] = Field(100000, description="初始资金")
class BacktestResult(BaseModel):
    """回测结果"""
    total_return: float = Field(..., description="总收益率")
    sharpe_ratio: float = Field(..., description="夏普比率")
    max_drawdown: float = Field(..., description="最大回撤")
    win_rate: float = Field(..., description="胜率")
    trades_count: int = Field(..., description="交易次数")
    holding_periods: list[int] = Field(default_factory=list, description="持仓周期分布")


class GenerateStrategyResponse(BaseModel):
    """AI生成策略响应"""
    success: bool = Field(..., description="是否成功")
    strategy_code: Optional[str] = Field(None, description="生成的策略代码")
    errors: Optional[list[str]] = Field(None, description="错误列表")
    backtest_result: Optional[BacktestResult] = Field(None, description="回测结果")
    message: Optional[str] = Field(None, description="附加消息")
