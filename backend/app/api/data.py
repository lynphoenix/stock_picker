# -*- coding: utf-8 -*-
"""
数据管理 API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.models.data import (
    DataOverview,
    StockDataList,
    StockDetail,
    DataRepairConfig,
    RepairTaskResponse,
    FetchScheduleConfig,
    FetchScheduleStatus
)
from backend.app.services.data_service import DataService

router = APIRouter()
service = DataService()


@router.get("/overview", response_model=DataOverview)
async def get_data_overview():
    """
    数据总览

    Returns:
        数据总览信息
    """
    return service.get_overview()


@router.get("/stocks", response_model=StockDataList)
async def get_stocks_data(
    market: str = Query("all", description="市场筛选"),
    sort_by: str = Query("completeness", description="排序字段"),
    only_missing: bool = Query(False, description="仅显示缺失"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页大小")
):
    """
    获取股票数据列表

    Args:
        market: 市场筛选
        sort_by: 排序字段
        only_missing: 仅显示缺失
        page: 页码
        page_size: 每页大小

    Returns:
        股票数据列表
    """
    return service.get_stocks_list(
        market=market,
        sort_by=sort_by,
        only_missing=only_missing,
        page=page,
        page_size=page_size
    )


@router.get("/stocks/{code}", response_model=StockDetail)
async def get_stock_detail(code: str):
    """
    获取单只股票详情

    Args:
        code: 股票代码

    Returns:
        股票详情
    """
    detail = service.get_stock_detail(code)
    if not detail:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    return detail


@router.post("/repair", response_model=RepairTaskResponse)
async def repair_data(config: DataRepairConfig, background_tasks: BackgroundTasks):
    """
    补充数据

    Args:
        config: 补充配置
        background_tasks: 后台任务

    Returns:
        任务ID
    """
    try:
        task_id = service.create_repair_task(config)
        background_tasks.add_task(service.run_repair_task, task_id, config)

        return RepairTaskResponse(
            task_id=task_id,
            status="running",
            progress=0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repair/status/{task_id}", response_model=RepairTaskResponse)
async def get_repair_status(task_id: str):
    """
    获取数据补充进度

    Args:
        task_id: 任务ID

    Returns:
        任务状态
    """
    status = service.get_repair_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return status


@router.get("/fetch-schedule", response_model=FetchScheduleStatus)
async def get_fetch_schedule():
    """
    获取采集调度配置

    Returns:
        调度配置和状态
    """
    return service.get_fetch_schedule()


@router.put("/fetch-schedule", response_model=FetchScheduleConfig)
async def update_fetch_schedule(config: FetchScheduleConfig):
    """
    更新采集调度配置

    Args:
        config: 新配置

    Returns:
        更新后的配置
    """
    try:
        updated = service.update_fetch_schedule(config)
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-now", response_model=dict)
async def trigger_fetch_now(background_tasks: BackgroundTasks):
    """
    立即执行一次采集

    Returns:
        任务ID
    """
    try:
        task_id = service.create_fetch_task()
        background_tasks.add_task(service.run_fetch_task, task_id)

        return {
            "task_id": task_id,
            "status": "running",
            "message": "数据采集已启动"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
