# -*- coding: utf-8 -*-
"""
数据源熔断器 - Circuit Breaker Pattern

用于数据源的故障检测和自动恢复，防止级联故障。

状态机:
CLOSED (正常) → OPEN (熔断) → HALF_OPEN (半开探测)
"""
import time
import threading
from enum import Enum
from typing import Optional
from src.logger_config import setup_logger

logger = setup_logger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常，允许请求通过
    OPEN = "open"          # 熔断，拒绝请求
    HALF_OPEN = "half_open"  # 半开，允许探测请求


class CircuitBreakerError(Exception):
    """熔断器异常"""
    def __init__(self, message: str, state: CircuitState):
        super().__init__(message)
        self.state = state


class DataSourceCircuitBreaker:
    """
    数据源熔断器

    使用方式:
        breaker = DataSourceCircuitBreaker(
            failure_threshold=5,    # 连续5次失败触发熔断
            success_threshold=2,     # 连续2次成功恢复
            timeout=60,            # 60秒后半开
            half_open_max_calls=3   # 半开状态最多尝试3次
        )

        # 在调用数据源前检查
        if not breaker.can_execute():
            raise CircuitBreakerError("Circuit is open", breaker.state)

        try:
            result = data_source.fetch(...)
            if result.success:
                breaker.record_success()
            else:
                breaker.record_failure()
            return result
        except Exception as e:
            breaker.record_failure()
            raise
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        half_open_max_calls: int = 3,
        name: str = "default"
    ):
        """
        Args:
            failure_threshold: 连续失败次数阈值，达到后触发熔断
            success_threshold: 半开状态下连续成功次数，达到后关闭熔断
            timeout: 熔断持续时间（秒），超时后进入半开状态
            half_open_max_calls: 半开状态下允许的最大探测次数
            name: 熔断器名称（用于日志区分）
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

        # 统计信息
        self._total_calls = 0
        self._total_successes = 0
        self._total_failures = 0

        logger.info(
            f"CircuitBreaker [{name}] initialized: "
            f"failure_threshold={failure_threshold}, "
            f"success_threshold={success_threshold}, "
            f"timeout={timeout}s"
        )

    def _get_state_internal(self) -> CircuitState:
        """获取内部状态（不触发状态转换）"""
        return self._state

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            # 检查是否需要从 OPEN 转换到 HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._last_failure_time is not None:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
                        logger.info(f"CircuitBreaker [{self.name}] transitioned to HALF_OPEN")
            return self._state

    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        elif state == CircuitState.HALF_OPEN:
            # 半开状态，检查是否还有探测名额
            return self._half_open_calls < self.half_open_max_calls
        return False

    def record_success(self) -> None:
        """记录成功调用"""
        with self._lock:
            self._total_calls += 1
            self._total_successes += 1

            # 使用 state property 来确保状态是最新的（可能触发 OPEN -> HALF_OPEN 转换）
            current_state = self._get_state_internal()

            if current_state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_calls += 1
                logger.debug(
                    f"CircuitBreaker [{self.name}] success in HALF_OPEN: "
                    f"{self._success_count}/{self.success_threshold}"
                )

                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(f"CircuitBreaker [{self.name}] transitioned to CLOSED")
            elif current_state == CircuitState.CLOSED:
                # 成功后重置失败计数
                self._failure_count = 0

    def record_failure(self) -> None:
        """记录失败调用"""
        with self._lock:
            self._total_calls += 1
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()

            # 使用内部状态
            current_state = self._get_state_internal()

            if current_state == CircuitState.CLOSED:
                logger.warning(
                    f"CircuitBreaker [{self.name}] failure: "
                    f"{self._failure_count}/{self.failure_threshold}"
                )
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"CircuitBreaker [{self.name}] transitioned to OPEN "
                        f"(will retry after {self.timeout}s)"
                    )
            elif self._state == CircuitState.HALF_OPEN:
                # 半开状态下失败，立即回到 OPEN
                self._state = CircuitState.OPEN
                self._success_count = 0
                self._half_open_calls = 0
                logger.warning(
                    f"CircuitBreaker [{self.name}] HALF_OPEN failed, back to OPEN"
                )
            elif self._state == CircuitState.OPEN:
                # 已经是 OPEN，更新失败时间
                pass

    def get_status(self) -> dict:
        """获取熔断器状态"""
        with self._lock:
            # 直接访问_state避免死锁（不调用state属性getter）
            state_value = self._state.value
            total = self._total_calls
            successes = self._total_successes
            return {
                "name": self.name,
                "state": state_value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "last_failure_time": self._last_failure_time,
                "total_calls": total,
                "total_successes": successes,
                "total_failures": self._total_failures,
                "success_rate": (
                    successes / total * 100
                    if total > 0 else 0
                ),
            }

    def reset(self) -> None:
        """重置熔断器到初始状态"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            logger.info(f"CircuitBreaker [{self.name}] reset to CLOSED")

    def __repr__(self) -> str:
        return f"DataSourceCircuitBreaker(name={self.name}, state={self.state.value})"


class CircuitBreakerManager:
    """
    熔断器管理器

    统一管理多个数据源的熔断器
    """

    def __init__(self):
        self._breakers: dict[str, DataSourceCircuitBreaker] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
    ) -> DataSourceCircuitBreaker:
        """注册一个新的熔断器"""
        with self._lock:
            if name in self._breakers:
                return self._breakers[name]

            breaker = DataSourceCircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout,
            )
            self._breakers[name] = breaker
            logger.info(f"CircuitBreakerManager registered: {name}")
            return breaker

    def get(self, name: str) -> Optional[DataSourceCircuitBreaker]:
        """获取熔断器"""
        return self._breakers.get(name)

    def get_all_status(self) -> list[dict]:
        """获取所有熔断器状态"""
        with self._lock:
            return [breaker.get_status() for breaker in self._breakers.values()]

    def reset_all(self) -> None:
        """重置所有熔断器"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("CircuitBreakerManager reset all breakers")


# 全局熔断器管理器
_global_breaker_manager = CircuitBreakerManager()


def get_breaker_manager() -> CircuitBreakerManager:
    """获取全局熔断器管理器"""
    return _global_breaker_manager
