# -*- coding: utf-8 -*-
"""
策略相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


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

    class Config:
        json_schema_extra = {
            "example": {
                "id": "enhanced_multi_factor",
                "name": "增强多因子策略",
                "description": "基于10+因子的综合评分选股策略",
                "params": {
                    "min_score": 60,
                    "top_n": 20,
                    "rebalance_days": 5
                },
                "created_at": "2026-01-29T10:00:00",
                "updated_at": "2026-01-29T10:00:00",
                "performance_history": []
            }
        }


class StrategyDetailResponse(StrategyResponse):
    """策略详情响应（包含代码）"""
    code: str = Field(..., description="策略源代码")
