# -*- coding: utf-8 -*-
"""
数据缓存管理器
避免重复下载历史数据
"""

import os
import pickle
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
import pandas as pd

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import CACHE_DIR, CACHE_ENABLED, CACHE_EXPIRE_DAYS


class CacheManager:
    """数据缓存管理器"""

    def __init__(self, cache_dir: Path = None, expire_days: int = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.expire_days = expire_days or CACHE_EXPIRE_DAYS
        self.enabled = CACHE_ENABLED

        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str, cache_type: str = "data") -> Path:
        """获取缓存文件路径"""
        if cache_type == "data":
            return self.cache_dir / f"{key}.pkl"
        elif cache_type == "json":
            return self.cache_dir / f"{key}.json"
        else:
            return self.cache_dir / key

    def _is_expired(self, cache_path: Path) -> bool:
        """检查缓存是否过期"""
        if not self.expire_days:
            return False

        if not cache_path.exists():
            return True

        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expire_time = datetime.now() - timedelta(days=self.expire_days)
        return mtime < expire_time

    def get(self, key: str, cache_type: str = "data") -> Optional[Any]:
        """获取缓存数据"""
        if not self.enabled:
            return None

        cache_path = self._get_cache_path(key, cache_type)

        if not cache_path.exists() or self._is_expired(cache_path):
            return None

        try:
            if cache_type == "data":
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            elif cache_type == "json":
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(cache_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            # 缓存读取失败，返回None
            return None

    def set(self, key: str, data: Any, cache_type: str = "data") -> bool:
        """保存缓存数据"""
        if not self.enabled:
            return False

        cache_path = self._get_cache_path(key, cache_type)

        try:
            if cache_type == "data":
                with open(cache_path, 'wb') as f:
                    pickle.dump(data, f)
            elif cache_type == "json":
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                with open(cache_path, 'wb') as f:
                    f.write(data)
            return True
        except Exception as e:
            return False

    def delete(self, key: str, cache_type: str = "data") -> bool:
        """删除缓存数据"""
        cache_path = self._get_cache_path(key, cache_type)

        if cache_path.exists():
            try:
                cache_path.unlink()
                return True
            except Exception:
                return False
        return False

    def clear(self) -> bool:
        """清空所有缓存"""
        try:
            for file in self.cache_dir.iterdir():
                if file.is_file():
                    file.unlink()
            return True
        except Exception:
            return False

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        files = list(self.cache_dir.iterdir())
        total_size = sum(f.stat().st_size for f in files if f.is_file())

        return {
            "file_count": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir)
        }


# 便捷函数
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """获取缓存管理器单例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cache_stock_history(symbol: str, start_date: str, end_date: str, adjust: str = "qfq") -> callable:
    """股票历史数据缓存装饰器"""
    cache_manager = get_cache_manager()

    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"stock_{symbol}_{start_date}_{end_date}_{adjust}"

            # 尝试从缓存获取
            cached_data = cache_manager.get(cache_key, "data")
            if cached_data is not None:
                return cached_data

            # 调用原函数获取数据
            result = func(*args, **kwargs)

            # 保存到缓存
            if result is not None:
                cache_manager.set(cache_key, result, "data")

            return result

        return wrapper

    return decorator
