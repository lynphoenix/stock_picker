# -*- coding: utf-8 -*-
"""
超时控制工具
"""
import signal
from functools import wraps
import platform


class TimeoutError(Exception):
    """超时异常"""
    pass


def timeout(seconds=30):
    """
    超时装饰器

    Args:
        seconds: 超时时间（秒）

    Note:
        仅在Unix/Linux/MacOS系统上使用signal.SIGALRM
        Windows系统会跳过超时控制
    """
    def decorator(func):
        # Windows系统不支持signal.SIGALRM，跳过超时控制
        if platform.system() == 'Windows':
            return func

        def _handle_timeout(signum, frame):
            raise TimeoutError(f"Function '{func.__name__}' timed out after {seconds}s")

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 设置超时信号
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                # 取消超时信号
                signal.alarm(0)
            return result
        return wrapper
    return decorator
