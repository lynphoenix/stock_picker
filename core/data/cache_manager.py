# -*- coding: utf-8 -*-
"""
统一缓存管理器
"""
import os
import pickle
import json
from datetime import datetime, timedelta
from typing import Any, Optional
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config


class CacheManager:
    """统一缓存管理器"""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or config.CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def get(self, key: str, ttl: int = None) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键
            ttl: 缓存有效期(秒)，None表示永久有效

        Returns:
            缓存数据，如果不存在或过期返回None
        """
        cache_file = self._get_cache_path(key)

        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, "rb") as f:
                cache_data = pickle.load(f)

            # 检查是否过期
            if ttl is not None:
                cached_time = cache_data.get("timestamp")
                if cached_time:
                    age = (datetime.now() - cached_time).total_seconds()
                    if age > ttl:
                        return None

            return cache_data.get("data")

        except Exception as e:
            print(f"读取缓存失败 {key}: {e}")
            return None

    def set(self, key: str, value: Any, metadata: dict = None):
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存数据
            metadata: 元数据
        """
        cache_file = self._get_cache_path(key)

        cache_data = {
            "data": value,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            print(f"保存缓存失败 {key}: {e}")

    def clear(self, pattern: str = None):
        """
        清除缓存

        Args:
            pattern: 键名模式，None表示清除所有
        """
        if pattern is None:
            # 清除所有缓存
            for file in os.listdir(self.cache_dir):
                os.remove(os.path.join(self.cache_dir, file))
        else:
            # 清除匹配的缓存
            for file in os.listdir(self.cache_dir):
                if pattern in file:
                    os.remove(os.path.join(self.cache_dir, file))

    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        # 将键名中的特殊字符替换为下划线
        safe_key = key.replace("/", "_").replace(":", "_")
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
