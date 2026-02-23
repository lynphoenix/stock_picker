# -*- coding: utf-8 -*-
"""
监控API路由 - Phase 3监控系统
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import sys
from pathlib import Path

# 添加项目根目录到路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from core.monitoring.enhanced_monitor import enhanced_monitor, MonitorSnapshot
from core.monitoring.alert_system import alert_system
from core.repair.auto_repair import auto_repair
from src.logger_config import setup_logger

# 数据源监控 imports
from src.data_source_manager import DataSourceManager
from src.sqlite_cache_manager import get_cache

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/monitoring/overview")
async def get_monitoring_overview():
    """获取监控总览"""
    try:
        overview = enhanced_monitor.get_overview()
        return {
            "success": True,
            "data": overview
        }
    except Exception as e:
        logger.error(f"获取监控总览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/trend")
async def get_trend(hours: int = Query(24, ge=1, le=168)):
    """
    获取趋势数据

    Args:
        hours: 查询小时数 (1-168)
    """
    try:
        trend_data = enhanced_monitor.get_trend_data(hours=hours)
        return {
            "success": True,
            "data": trend_data,
            "count": len(trend_data)
        }
    except Exception as e:
        logger.error(f"获取趋势数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/errors")
async def get_error_statistics(hours: int = Query(24, ge=1, le=168)):
    """
    获取错误统计

    Args:
        hours: 查询小时数 (1-168)
    """
    try:
        errors = enhanced_monitor.get_error_statistics(hours=hours)
        return {
            "success": True,
            "data": errors
        }
    except Exception as e:
        logger.error(f"获取错误统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/missing")
async def diagnose_missing():
    """诊断缺失数据"""
    try:
        missing = enhanced_monitor.diagnose_missing_data()
        return {
            "success": True,
            "data": missing
        }
    except Exception as e:
        logger.error(f"诊断缺失数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/realtime")
async def get_realtime_state():
    """获取实时状态"""
    try:
        state = enhanced_monitor.get_realtime_state()
        return {
            "success": True,
            "data": state
        }
    except Exception as e:
        logger.error(f"获取实时状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/snapshot")
async def record_snapshot(snapshot: dict):
    """记录监控快照"""
    try:
        snap = MonitorSnapshot(**snapshot)
        enhanced_monitor.record_snapshot(snap)

        # 检查告警
        alert_system.check_and_alert(snapshot)

        return {
            "success": True,
            "message": "快照记录成功"
        }
    except Exception as e:
        logger.error(f"记录快照失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repair/scan")
async def scan_missing_data():
    """扫描缺失数据"""
    try:
        result = auto_repair.scan_missing_data()
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"扫描缺失数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repair/fix")
async def repair_missing(
    priority: str = Query("critical", regex="^(critical|moderate|all)$")
):
    """
    修复缺失数据

    Args:
        priority: 优先级 (critical, moderate, all)
    """
    try:
        logger.info(f"开始修复缺失数据: priority={priority}")

        # 异步执行修复（避免阻塞）
        import threading

        result_container = {}

        def repair_task():
            try:
                result = auto_repair.repair_missing_stocks(priority=priority)
                result_container['result'] = result
            except Exception as e:
                result_container['error'] = str(e)

        thread = threading.Thread(target=repair_task)
        thread.start()

        # 等待最多2秒获取初步结果
        thread.join(timeout=2)

        if thread.is_alive():
            # 仍在执行中
            return {
                "success": True,
                "message": f"修复任务已启动 (priority={priority})，正在后台执行",
                "status": "running"
            }
        else:
            # 已完成
            if 'error' in result_container:
                raise HTTPException(status_code=500, detail=result_container['error'])

            return {
                "success": True,
                "message": "修复完成",
                "data": result_container.get('result', {})
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修复缺失数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repair/yesterday")
async def repair_yesterday():
    """修复昨天的缺失数据"""
    try:
        result = auto_repair.auto_repair_yesterday()
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"修复昨天数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """WebSocket监控推送"""
    await websocket.accept()
    enhanced_monitor.add_websocket_connection(websocket)

    logger.info("WebSocket连接已建立")

    try:
        while True:
            # 接收客户端消息（心跳）
            data = await websocket.receive_text()

            # 可以处理客户端请求
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        enhanced_monitor.remove_websocket_connection(websocket)
        logger.info("WebSocket连接已断开")


@router.get("/alerts/history")
async def get_alert_history(limit: int = Query(100, ge=1, le=1000)):
    """
    获取告警历史

    Args:
        limit: 返回数量 (1-1000)
    """
    try:
        alerts = alert_system.get_alert_history(limit=limit)

        # 转换为可序列化格式
        alert_dicts = []
        for alert in alerts:
            alert_dicts.append({
                'level': alert.level.value,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.timestamp,
                'details': alert.details
            })

        return {
            "success": True,
            "data": alert_dicts,
            "count": len(alert_dicts)
        }
    except Exception as e:
        logger.error(f"获取告警历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/test")
async def test_alert():
    """测试告警系统"""
    try:
        # 触发测试告警
        test_metrics = {
            'success_rate': 0.5,
            'total': 100,
            'success': 50,
            'failed': 50
        }

        alerts = alert_system.check_and_alert(test_metrics)

        return {
            "success": True,
            "message": f"触发了{len(alerts)}个告警",
            "alerts": [a.title for a in alerts]
        }
    except Exception as e:
        logger.error(f"测试告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 数据源监控 API (Phase 1.5)
# ============================================================

@router.get("/data-source/stats")
async def get_data_source_stats():
    """
    获取数据源状态统计

    返回:
        - 数据源健康状态
        - 熔断器状态
        - 缓存命中率
        - 采集统计
    """
    try:
        # 1. 获取熔断器状态
        dsm = DataSourceManager()
        circuit_breakers = dsm.get_circuit_breaker_status()

        # 2. 获取缓存统计
        cache = get_cache()
        cache_stats = cache.get_stats()

        # 3. 构建响应
        sources = []
        for cb in circuit_breakers:
            total = cb.get('total_calls', 0)
            successes = cb.get('total_successes', 0)
            failures = cb.get('total_failures', 0)
            success_rate = (successes / total * 100) if total > 0 else 100.0

            # 确定状态
            state = cb.get('state', 'closed')
            if state == 'open':
                status = 'circuit_open'
            elif state == 'half_open':
                status = 'degraded'
            else:
                status = 'healthy' if success_rate > 95 else 'degraded'

            sources.append({
                'name': cb.get('name', 'unknown'),
                'status': status,
                'circuit_state': state,
                'total_calls': total,
                'successes': successes,
                'failures': failures,
                'success_rate': round(success_rate, 2),
            })

        return {
            'success': True,
            'data': {
                'sources': sources,
                'cache': {
                    'hit_rate': round(cache_stats.hit_rate, 2),
                    'total_requests': cache_stats.total_requests,
                    'cache_hits': cache_stats.cache_hits,
                    'cache_misses': cache_stats.cache_misses,
                    'total_keys': cache_stats.total_keys,
                    'total_size_mb': round(cache_stats.total_size_bytes / 1024 / 1024, 2),
                }
            }
        }

    except Exception as e:
        logger.error(f"获取数据源统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-source/circuit-breakers")
async def get_circuit_breaker_details():
    """获取熔断器详细状态"""
    try:
        dsm = DataSourceManager()
        breakers = dsm.get_circuit_breaker_status()

        return {
            'success': True,
            'data': breakers
        }

    except Exception as e:
        logger.error(f"获取熔断器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-source/cache")
async def get_cache_stats():
    """获取缓存统计"""
    try:
        cache = get_cache()
        stats = cache.get_stats()

        return {
            'success': True,
            'data': {
                'hit_rate': round(stats.hit_rate, 2),
                'total_requests': stats.total_requests,
                'cache_hits': stats.cache_hits,
                'cache_misses': stats.cache_misses,
                'total_keys': stats.total_keys,
                'total_size_bytes': stats.total_size_bytes,
                'total_size_mb': round(stats.total_size_bytes / 1024 / 1024, 2),
            }
        }

    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-source/cache/clear")
async def clear_cache(pattern: str = Query(None, description="缓存键匹配模式")):
    """清除缓存"""
    try:
        cache = get_cache()
        cache.clear(pattern)

        return {
            'success': True,
            'message': f"缓存已清除: {pattern or '全部'}"
        }

    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
