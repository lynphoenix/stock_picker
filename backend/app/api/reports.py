# -*- coding: utf-8 -*-
"""
报表 API
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.services.report_service import ReportService

router = APIRouter()
service = ReportService()


@router.get("/{task_id}/excel")
async def export_excel(task_id: str):
    """
    导出Excel报表

    Args:
        task_id: 回测任务ID

    Returns:
        Excel文件
    """
    try:
        file_path = service.generate_excel(task_id)
        return FileResponse(
            path=file_path,
            filename=f"backtest_report_{task_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 的结果不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/pdf")
async def export_pdf(task_id: str):
    """
    导出PDF报表

    Args:
        task_id: 回测任务ID

    Returns:
        PDF文件
    """
    try:
        file_path = service.generate_pdf(task_id)
        return FileResponse(
            path=file_path,
            filename=f"backtest_report_{task_id}.pdf",
            media_type="application/pdf"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 的结果不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
