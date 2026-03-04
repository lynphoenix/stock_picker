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
    sort_by: str = Query("code", description="排序字段"),
    search: str = Query("", description="搜索关键词"),
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
        search=search,
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
async def trigger_fetch_now(
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query(None, description="起始日期，如 20250101"),
    end_date: Optional[str] = Query(None, description="结束日期，如 20260226")
):
    """
    立即执行一次采集

    Args:
        start_date: 起始日期（可选，默认最近30天）
        end_date: 结束日期（可选，默认今天）

    Returns:
        任务ID
    """
    try:
        task_id = service.create_fetch_task(start_date=start_date, end_date=end_date)
        
        # 使用后台任务执行采集
        background_tasks.add_task(service.run_fetch_task, task_id)

        return {
            "task_id": task_id,
            "status": "started",
            "message": f"数据采集已启动 ({start_date or '默认'} ~ {end_date or '默认'})"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

        def run_async_task(task_id):
            asyncio.run(service.run_fetch_task(task_id))
        
        background_tasks.add_task(run_async_task, task_id)

        return {
            "task_id": task_id,
            "status": "started",
            "message": "数据采集已启动"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fetch/status/{task_id}", response_model=dict)
async def get_fetch_status(task_id: str):
    """
    获取采集进度

    Args:
        task_id: 任务ID

    Returns:
        进度信息
    """
    status = service.get_fetch_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return status


@router.get("/fetch/stats", response_model=dict)
async def get_fetch_stats():
    """
    获取采集统计

    Returns:
        统计信息
    """
    return service.get_fetch_stats()


@router.post("/fetch/stop", response_model=dict)
async def stop_fetch():
    """
    停止采集

    Returns:
        停止结果
    """
    result = service.stop_fetch()
    return result


@router.get("/stock/{code}")
async def get_stock_prices(code: str):
    """获取股票每日价格数据"""
    detail = service.monitor.get_stock_detail(code)
    if not detail or "error" in detail:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    return detail


@router.get("/stock/{code}/minute")
async def get_stock_minute(code: str, date: str = None):
    """获取股票分钟级数据（分时图）"""
    import baostock as bs

    lg = bs.login()
    if lg.error_code != '0':
        raise HTTPException(status_code=500, detail=f"Baostock登录失败: {lg.error_msg}")

    try:
        # 使用指定日期或最近的交易日 (2026-01-23 有数据)
        # 判断股票代码前缀
        bs_code = code
        if len(code) == 6 and code.isdigit():
            bs_code = "sh." + code if code.startswith('6') else "sz." + code

        # 自动获取最近一个有分钟数据的交易日
        target_date = date
        if not target_date:
            from datetime import datetime
            # 从缓存获取最近交易日
            from core.data.data_monitor import get_trading_days_set
            trading_dates = get_trading_days_set()
            today = datetime.now().strftime('%Y-%m-%d')
            valid_dates = sorted([d for d in trading_dates if d < today], reverse=True)

            # 只查最近的一个交易日
            if valid_dates:
                target_date = valid_dates[0]

        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,time,open,high,low,close,volume",
            start_date=target_date,
            end_date=target_date,
            frequency="5",
            adjustflag="3"
        )

        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        if not data_list:
            bs.logout()
            return {"code": code, "date": target_date, "data": [], "message": "无分钟数据"}

        # 格式化数据
        result = []
        for row in data_list:
            time_str = row[1][8:12] if len(row[1]) >= 12 else ""
            hour = int(time_str[:2]) if time_str else 0
            minute = int(time_str[2:4]) if len(time_str) >= 4 else 0
            result.append({
                "time": f"{hour:02d}:{minute:02d}",
                "open": float(row[2]) if row[2] else 0,
                "high": float(row[3]) if row[3] else 0,
                "low": float(row[4]) if row[4] else 0,
                "close": float(row[5]) if row[5] else 0,
                "volume": float(row[6]) if row[6] else 0
            })

        bs.logout()
        return {"code": code, "date": target_date, "data": result}

    except Exception as e:
        bs.logout()
        raise HTTPException(status_code=500, detail=str(e))
