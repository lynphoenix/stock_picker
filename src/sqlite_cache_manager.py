# -*- coding: utf-8 -*-
"""
SQLite 缓存管理器 - 替代 JSON 文件缓存

优势:
- 支持 SQL 查询
- 自动索引
- 并发读写
- 持久化可靠
- LRU 淘汰策略

使用示例:
    cache = SQLiteCacheManager()

    # 设置缓存
    cache.set("stock:000001:daily", df, metadata={"source": "baostock"})

    # 获取缓存
    df = cache.get("stock:000001:daily")

    # 检查缓存是否存在
    if cache.exists("stock:000001:daily"):
        ...

    # 获取统计
    stats = cache.get_stats()
"""
import sqlite3
import json
import threading
import os
import sys
import zlib
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.logger_config import setup_logger

logger = setup_logger(__name__)


@dataclass
class CacheStats:
    """缓存统计"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    total_keys: int = 0
    total_size_bytes: int = 0


class SQLiteCacheManager:
    """
    SQLite 缓存管理器

    表结构:
        CREATE TABLE stock_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT NOT NULL UNIQUE,
            data BLOB NOT NULL,           # 压缩后的数据
            metadata TEXT,                 # JSON 元数据
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 1,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_cache_key ON stock_cache(cache_key);
        CREATE INDEX idx_updated_at ON stock_cache(updated_at);
        CREATE INDEX idx_last_accessed ON stock_cache(last_accessed);
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        db_path: str = None,
        max_age_days: int = 30,
        max_entries: int = 10000,
        compress: bool = True,
    ):
        """
        初始化 SQLite 缓存管理器

        Args:
            db_path: 数据库文件路径（默认 ~/.cache/stock_picker/cache.db）
            max_age_days: 缓存最大保留天数
            max_entries: 最大缓存条目数（用于 LRU 淘汰）
            compress: 是否压缩数据
        """
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        if db_path is None:
            cache_dir = os.path.expanduser("~/.cache/stock_picker")
            os.makedirs(cache_dir, exist_ok=True)
            db_path = os.path.join(cache_dir, "cache.db")

        self.db_path = db_path
        self.max_age_days = max_age_days
        self.max_entries = max_entries
        self.compress = compress

        # 统计
        self._stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0,
        }
        self._stats_lock = threading.Lock()

        # 初始化数据库
        self._init_db()

        self._initialized = True
        logger.info(f"SQLiteCacheManager initialized: {db_path}")

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT NOT NULL UNIQUE,
                    data BLOB NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON stock_cache(cache_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON stock_cache(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_accessed ON stock_cache(last_accessed)")

            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _serialize(self, data: Any) -> bytes:
        """序列化数据（JSON + 可选压缩）"""
        try:
            # 优先尝试 JSON 序列化
            json_str = json.dumps(data, default=str, ensure_ascii=False)
            if self.compress:
                return zlib.compress(json_str.encode('utf-8'))
            return json_str.encode('utf-8')
        except (TypeError, ValueError):
            # 如果 JSON 失败，使用 pickle
            import pickle
            pickled = pickle.dumps(data)
            if self.compress:
                return zlib.compress(pickled)
            return pickled

    def _deserialize(self, data: bytes) -> Any:
        """反序列化数据"""
        try:
            # 尝试解压
            try:
                data = zlib.decompress(data)
            except zlib.error:
                pass

            # 尝试 JSON
            try:
                return json.loads(data.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass

            # 使用 pickle
            import pickle
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"反序列化失败: {e}")
            return None

    def get(self, key: str, ttl: int = None) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键
            ttl: 过期时间（秒），None 表示无过期时间

        Returns:
            缓存数据，不存在或过期返回 None
        """
        with self._stats_lock:
            self._stats['total_requests'] += 1

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT data, created_at, access_count FROM stock_cache WHERE cache_key = ?",
                    (key,)
                )
                row = cursor.fetchone()

                if row is None:
                    with self._stats_lock:
                        self._stats['misses'] += 1
                    return None

                # 检查 TTL
                if ttl is not None:
                    created_at = datetime.fromisoformat(row['created_at'])
                    age = (datetime.now() - created_at).total_seconds()
                    if age > ttl:
                        with self._stats_lock:
                            self._stats['misses'] += 1
                        return None

                # 更新访问计数
                conn.execute(
                    "UPDATE stock_cache SET access_count = access_count + 1, "
                    "last_accessed = CURRENT_TIMESTAMP WHERE cache_key = ?",
                    (key,)
                )
                conn.commit()

                with self._stats_lock:
                    self._stats['hits'] += 1

                return self._deserialize(row['data'])

        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            with self._stats_lock:
                self._stats['misses'] += 1
            return None

    def set(self, key: str, value: Any, metadata: dict = None):
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存数据
            metadata: 元数据
        """
        try:
            serialized = self._serialize(value)
            metadata_json = json.dumps(metadata) if metadata else None

            with self._get_connection() as conn:
                # 使用 INSERT OR REPLACE
                conn.execute("""
                    INSERT OR REPLACE INTO stock_cache
                    (cache_key, data, metadata, updated_at, last_accessed)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (key, serialized, metadata_json))

                conn.commit()

            # 定期清理过期数据
            self._cleanup_if_needed()

        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM stock_cache WHERE cache_key = ?",
                    (key,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"检查缓存存在失败 {key}: {e}")
            return False

    def delete(self, key: str):
        """删除缓存"""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM stock_cache WHERE cache_key = ?", (key,))
                conn.commit()
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")

    def clear(self, pattern: str = None):
        """
        清除缓存

        Args:
            pattern: 可选的键匹配模式（SQL LIKE）
        """
        try:
            with self._get_connection() as conn:
                if pattern:
                    conn.execute(
                        "DELETE FROM stock_cache WHERE cache_key LIKE ?",
                        (pattern,)
                    )
                else:
                    conn.execute("DELETE FROM stock_cache")
                conn.commit()
                logger.info(f"缓存已清除: {pattern or '全部'}")
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")

    def _cleanup_if_needed(self):
        """定期清理（过期数据 + LRU 淘汰）"""
        try:
            with self._get_connection() as conn:
                # 1. 删除过期数据
                cutoff = datetime.now() - timedelta(days=self.max_age_days)
                conn.execute(
                    "DELETE FROM stock_cache WHERE updated_at < ?",
                    (cutoff.isoformat(),)
                )

                # 2. LRU 淘汰
                conn.execute("""
                    DELETE FROM stock_cache WHERE id NOT IN (
                        SELECT id FROM stock_cache
                        ORDER BY last_accessed DESC
                        LIMIT ?
                    )
                """, (self.max_entries,))

                conn.commit()

        except Exception as e:
            logger.error(f"清理缓存失败: {e}")

    def get_stats(self) -> CacheStats:
        """获取缓存统计"""
        try:
            with self._get_connection() as conn:
                # 获取记录数和大小
                cursor = conn.execute(
                    "SELECT COUNT(*) as count, SUM(LENGTH(data)) as size FROM stock_cache"
                )
                row = cursor.fetchone()

                total_keys = row['count'] or 0
                total_size = row['size'] or 0

                # 计算命中率
                with self._stats_lock:
                    hits = self._stats['hits']
                    misses = self._stats['misses']
                    total = self._stats['total_requests']

                hit_rate = (hits / total * 100) if total > 0 else 0.0

                return CacheStats(
                    total_requests=total,
                    cache_hits=hits,
                    cache_misses=misses,
                    hit_rate=hit_rate,
                    total_keys=total_keys,
                    total_size_bytes=total_size,
                )

        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return CacheStats()

    def get_all_keys(self, pattern: str = None) -> list:
        """获取所有缓存键"""
        try:
            with self._get_connection() as conn:
                if pattern:
                    cursor = conn.execute(
                        "SELECT cache_key FROM stock_cache WHERE cache_key LIKE ? ORDER BY last_accessed DESC",
                        (pattern,)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT cache_key FROM stock_cache ORDER BY last_accessed DESC"
                    )
                return [row['cache_key'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取键列表失败: {e}")
            return []

    def migrate_from_json(self, json_dir: str):
        """
        从 JSON 缓存迁移

        Args:
            json_dir: JSON 缓存目录
        """
        import glob

        if not os.path.exists(json_dir):
            logger.warning(f"JSON 缓存目录不存在: {json_dir}")
            return

        logger.info(f"开始从 {json_dir} 迁移缓存...")

        count = 0
        for json_file in glob.glob(os.path.join(json_dir, "**/*.pkl"), recursive=True):
            try:
                import pickle
                with open(json_file, 'rb') as f:
                    cache_data = pickle.load(f)

                # 从生成 key
                rel_path = os.path.relpath(json_file, json_dir)
                key = rel_path.replace('/', ':').replace('\\', ':').replace('.pkl', '')

                # 提取数据
                data = cache_data.get('data')
                metadata = cache_data.get('metadata', {})

                if data is not None:
                    self.set(key, data, metadata)
                    count += 1

            except Exception as e:
                logger.warning(f"迁移失败 {json_file}: {e}")

        logger.info(f"迁移完成: {count} 条缓存")


# 全局实例
_global_cache: Optional[SQLiteCacheManager] = None


def get_cache() -> SQLiteCacheManager:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = SQLiteCacheManager()
    return _global_cache
