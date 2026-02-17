# -*- coding: utf-8 -*-
"""
策略管理 API
"""
from fastapi import APIRouter, HTTPException
from typing import List
import sys
from pathlib import Path

# 添加项目根目录到路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.models.strategy import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategyDetailResponse
)
from backend.app.services.strategy_service import StrategyService

router = APIRouter()
service = StrategyService()


@router.get("/", response_model=List[StrategyResponse])
async def list_strategies():
    """
    获取所有策略列表

    Returns:
        策略列表
    """
    strategies = service.list_all()
    return strategies


@router.get("/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy(strategy_id: str):
    """
    获取策略详情

    Args:
        strategy_id: 策略ID

    Returns:
        策略详情（包含代码）
    """
    strategy = service.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return strategy


@router.post("/", response_model=StrategyResponse, status_code=201)
async def create_strategy(strategy: StrategyCreate):
    """
    创建新策略

    Args:
        strategy: 策略信息

    Returns:
        创建的策略
    """
    try:
        created = service.create(strategy)
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(strategy_id: str, strategy: StrategyUpdate):
    """
    更新策略

    Args:
        strategy_id: 策略ID
        strategy: 更新内容

    Returns:
        更新后的策略
    """
    try:
        updated = service.update(strategy_id, strategy)
        if not updated:
            raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(strategy_id: str):
    """
    删除策略

    Args:
        strategy_id: 策略ID
    """
    success = service.delete(strategy_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return None
