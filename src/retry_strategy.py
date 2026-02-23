# -*- coding: utf-8 -*-
"""
智能重试策略 - 指数退避
"""
import time
import random
from typing import Callable, Any
from src.logger_config import setup_logger

logger = setup_logger(__name__)


class ExponentialBackoffRetry:
    """指数退避重试策略"""

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Args:
            initial_delay: 初始延迟（秒）
            max_delay: 最大延迟（秒）
            exponential_base: 指数基数
            jitter: 是否添加抖动（避免雷鸣群效应）
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def execute(
        self,
        func: Callable,
        *args,
        max_retries: int = 5,
        **kwargs
    ) -> Any:
        """
        执行带重试的函数

        Args:
            func: 要执行的函数
            max_retries: 最大重试次数
            *args, **kwargs: 函数参数

        Returns:
            函数执行结果

        Raises:
            最后一次执行的异常
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                
                # 如果是FetchResult对象，检查success
                if hasattr(result, 'success'):
                    if result.success:
                        return result
                    else:
                        # 失败但不抛异常，准备重试
                        last_exception = Exception(result.error_message)
                        if attempt < max_retries - 1:
                            delay = self._get_delay(attempt)
                            logger.warning(
                                f"尝试 {attempt+1}/{max_retries} 失败，"
                                f"{delay:.1f}秒后重试: {result.error_message}"
                            )
                            time.sleep(delay)
                        continue
                else:
                    # 普通函数，直接返回
                    return result

            except Exception as e:
                last_exception = e

                if attempt < max_retries - 1:
                    delay = self._get_delay(attempt)
                    logger.warning(
                        f"尝试 {attempt+1}/{max_retries} 失败，"
                        f"{delay:.1f}秒后重试: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"所有重试失败: {e}")

        # 所有重试都失败
        raise last_exception

    def _get_delay(self, attempt: int) -> float:
        """
        计算延迟时间

        Args:
            attempt: 当前尝试次数（从0开始）

        Returns:
            延迟秒数
        """
        # 基础延迟: initial_delay * (exponential_base ^ attempt)
        delay = self.initial_delay * (self.exponential_base ** attempt)

        # 限制最大延迟
        delay = min(delay, self.max_delay)

        # 添加抖动（避免雷鸣群效应）
        if self.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)
