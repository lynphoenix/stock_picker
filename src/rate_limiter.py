# -*- coding: utf-8 -*-
"""
限流器 - Token Bucket算法
"""
import time
import threading
from src.logger_config import setup_logger

logger = setup_logger(__name__)


class TokenBucket:
    """令牌桶限流器"""

    def __init__(self, rate: int = 200, capacity: int = 300):
        """
        Args:
            rate: 每分钟令牌数
            capacity: 桶容量
        """
        self.rate = rate / 60.0  # 转为每秒
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = threading.Lock()
        
        logger.info(f"TokenBucket初始化: rate={rate}/min, capacity={capacity}")

    def acquire(self, tokens: int = 1, timeout: float = None) -> bool:
        """
        获取令牌（阻塞或超时）

        Args:
            tokens: 需要的令牌数
            timeout: 超时时间（秒），None表示无限等待

        Returns:
            是否成功获取令牌
        """
        start_time = time.time()
        
        with self.lock:
            while True:
                self._refill()

                # 有足够的令牌
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                # 检查超时
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        logger.warning(f"获取令牌超时: 需要{tokens}个，当前{self.tokens:.1f}个")
                        return False

                # 计算需要等待的时间
                tokens_needed = tokens - self.tokens
                sleep_time = tokens_needed / self.rate
                
                # 限制单次等待时间
                sleep_time = min(sleep_time, 1.0)
                
                # 暂时释放锁，让其他线程也能访问
                self.lock.release()
                time.sleep(sleep_time)
                self.lock.acquire()

    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.rate

        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now

    def get_status(self) -> dict:
        """获取当前状态"""
        with self.lock:
            self._refill()
            return {
                'tokens': self.tokens,
                'capacity': self.capacity,
                'rate_per_second': self.rate,
                'utilization': (self.capacity - self.tokens) / self.capacity * 100
            }
