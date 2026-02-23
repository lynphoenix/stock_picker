# -*- coding: utf-8 -*-
"""
数据源监控API - 独立版本
"""
from fastapi import APIRouter, HTTPException, Query
import sys
from pathlib import Path

# 添加项目根目录到路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

# 数据源监控 imports
from src.data_source_manager import DataSourceManager
from src.sqlite_cache_manager import get_cache
from src.logger_config import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/data-source/stats")
async def get_data_source_stats():
    """
    获取数据源状态统计
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
