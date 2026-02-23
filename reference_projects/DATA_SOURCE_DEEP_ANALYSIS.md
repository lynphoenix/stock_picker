# 数据源模块深度对比分析

## 一、整体架构对比

### Daily Stock Analysis 数据源架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    data_provider/                               │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│ akshare_    │ tushare_    │ baostock_   │ yfinance_   efinance│
│ fetcher.py  │ fetcher.py  │ fetcher.py  │ fetcher.py pytdx   │
└──────┬──────┴──────┬──────┴──────┬──────┴─────────┬─────────┘
       │              │              │                │
       ▼              ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     统一接口层                                    │
│  - fetch_daily()                                               │
│  - fetch_realtime()                                            │
│  - fetch_fundamentals()                                        │
└─────────────────────────────────────────────────────────────────┘
```

### stock_picker 数据源架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    DataSourceManager                             │
│  - fetch_with_fallback() [带降级的多源采集]                      │
│  - 优先级: tushare → baostock → akshare                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Tushare   │    │  Baostock   │    │   AKShare   │
│ (需要token) │    │  (免费)     │    │   (免费)    │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 二、具体实现细节对比

### 1. 数据源数量

| 特性 | Daily Stock Analysis | stock_picker | 差距分析 |
|------|---------------------|--------------|----------|
| **数据源数量** | 6个 | 2-3个 | ❌ 缺少 4 个 |
| **支持的市场** | A股、港股、美股 | 仅A股 | ❌ 缺少港股、美股 |
| **代码组织** | 每个源独立文件 | 统一 Manager | 架构相似 |

**stock_picker 缺失的数据源:**
- YFinance (美股/港股)
- eFinance
- Pytdx (通达信)

### 2. 故障转移机制 (Failover)

#### Daily Stock Analysis 的实现

根据文档，Daily Stock Analysis 采用**多源优先级 + 故障自动切换**策略：

```python
# 伪代码 - 推测实现
sources = [
    {'name': 'tushare', 'priority': 1, 'enabled': True},
    {'name': 'akshare', 'priority': 2, 'enabled': True},
    {'name': 'baostock', 'priority': 3, 'enabled': True},
    # ... 依优先级尝试
]
```

#### stock_picker 的实现 (data_source_manager.py:88-153)

```python
def fetch_with_fallback(self, symbol, start_date, end_date, period, adjust):
    last_error = None
    for source in sorted(self.sources, key=lambda x: x['priority']):
        if not source['enabled']:
            continue
        try:
            result = self._fetch_from_source(...)
            if result.success:
                self.failure_counts[source['name']] = 0  # 重置失败计数
                return result
            else:
                self.failure_counts[source['name']] += 1  # 记录失败
                continue
        except Exception as e:
            self.failure_counts[source['name']] += 1
            continue
    return FetchResult(success=False, ...)
```

**对比分析:**

| 特性 | Daily Stock Analysis | stock_picker |
|------|---------------------|--------------|
| 优先级切换 | ✅ | ✅ |
| 失败计数 | ✅ | ✅ (failure_counts) |
| 智能熔断 | 未详述 | ❌ 缺失 |
| 失败阈值自动禁用 | 未详述 | ❌ 缺失 |

**stock_picker 缺失的故障转移能力:**
- 连续失败 N 次后自动禁用该数据源
- 定期探测恢复
- 故障率统计与可视化

### 3. 限流机制 (Rate Limiting)

#### stock_picker 已有 (rate_limiter.py)

```python
class TokenBucket:
    def __init__(self, rate: int = 200, capacity: int = 300):
        # 每分钟 200 个请求，桶容量 300
```

#### Daily Stock Analysis 的实现

根据文档:
- **随机延迟**: 0-60秒 避免 API 限流
- **并发控制**: 同一时间只运行一个任务
- **定时任务**: 随机延迟 + 手动触发

**对比:**

| 特性 | Daily Stock Analysis | stock_picker |
|------|---------------------|--------------|
| Token Bucket | ❌ | ✅ |
| 随机延迟 | ✅ | ❌ |
| 简单易实现 | ✅ | 需配置 |
| 适用场景 | GitHub Actions | 服务器常驻 |

### 4. 重试机制

#### stock_picker 已有 (retry_strategy.py)

```python
class ExponentialBackoffRetry:
    def __init__(
        self,
        initial_delay: float = 1.0,    # 初始延迟 1s
        max_delay: float = 60.0,        # 最大 60s
        exponential_base: float = 2.0,  # 指数 2
        jitter: bool = True              # 添加抖动
    ):
```

**重试策略:**
- 指数退避: 1s → 2s → 4s → 8s → 16s → 32s → 60s
- 最大 5 次重试
- 随机抖动避免雷鸣群效应

#### Daily Stock Analysis

- 未在文档中详述具体实现

**结论:** stock_picker 重试机制更完善

### 5. 超时处理

#### stock_picker (timeout_utils.py)

```python
@timeout(30)  # 30秒超时
def _fetch_akshare(self, symbol, start_date, end_date, period, adjust):
    ...
```

**各数据源超时配置:**

| 数据源 | 超时时间 | 实现方式 |
|--------|----------|----------|
| AKShare | 30s | @timeout 装饰器 |
| Baostock | 30s | 内置 |
| Tushare | 30s | @timeout 装饰器 |

#### Daily Stock Analysis

- 文档未详述

**结论:** stock_picker 超时处理完善

### 6. 数据质量保障

#### stock_picker 当前实现

| 模块 | 功能 | 代码位置 |
|------|------|----------|
| DataValidator | 数据验证 | core/data/data_validator.py |
| DataMonitor | 数据质量监控 | core/data/data_monitor.py |

```python
# data_validator.py - 推测实现
class DataValidator:
    def validate(self, df):
        # 检查列完整性
        # 检查数据类型
        # 检查数值范围
        # 检查缺失值
```

#### Daily Stock Analysis

- 文档未详述数据验证细节

**结论:** stock_picker 有专门的数据验证模块

---

## 三、关键实现差距

### 差距 1: 智能熔断机制 (Circuit Breaker)

**Daily Stock Analysis (Situation Monitor 参考):**

Situation Monitor 使用了 **CircuitBreaker** 模式:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold  # 5次失败触发熔断
        self.recovery_timeout = recovery_timeout     # 60秒后尝试恢复
        self.state = CLOSED
        self.failure_count = 0

    def call(self, func, *args):
        if self.state == OPEN:
            if time.time() > self.last_failure_time + self.recovery_timeout:
                self.state = HALF_OPEN  # 半开，允许试探
            else:
                raise CircuitOpenException()

        try:
            result = func(*args)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
```

**stock_picker 当前状态:**
- 只有简单的失败计数 `failure_counts`
- 没有熔断状态机
- 没有自动恢复机制

### 差距 2: 多阶段数据刷新

**Situation Monitor 的多阶段刷新:**

```python
class MultiStageRefresh:
    stages = [
        {'name': 'realtime', 'timeout': 5},
        {'name': 'daily', 'timeout': 30},
        {'name': 'historical', 'timeout': 300},
    ]

    def refresh(self, data_type):
        for stage in self.stages:
            try:
                return self.fetch_with_timeout(data_type, stage)
            except TimeoutError:
                continue  # 降级到下一阶段
```

**stock_picker:**
- 只有单一的数据获取方式
- 缺少实时/日线/历史的多阶段降级

### 差距 3: 数据缓存策略

#### stock_picker 现有缓存

```python
# cache_manager.py
class CacheManager:
    def get(self, key):
        # 检查 JSON 文件缓存
        # 返回缓存数据
```

#### Daily Stock Analysis 的缓存

根据文档，使用 **SQLite + SQLAlchemy**:
- 结构化存储
- 支持复杂查询
- 数据库级别的索引

### 差距 4: 并发采集

#### stock_picker (concurrent_fetcher.py)

```python
class ConcurrentFetcher:
    def fetch_batch(self, symbols, max_workers=10):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(self.fetch_one, symbols))
```

#### Daily Stock Analysis

- 文档提到使用 **asyncio** 进行并发采集
- 支持更高并发量

**对比:**

| 特性 | stock_picker | Daily Stock Analysis |
|------|--------------|---------------------|
| 并发方式 | ThreadPoolExecutor | asyncio |
| 适用场景 | CPU 密集 | I/O 密集 |
| 性能 | 中等 | 更高 |

---

## 四、改进建议

### 优先级 P0 (高)

#### 1. 补充缺失的数据源

```
需要增加:
├── yfinance_fetcher.py    # 美股/港股
├── efinance_fetcher.py    # A股补充
└── pytdx_fetcher.py       # 通达信
```

#### 2. 实现智能熔断机制

```python
class DataSourceCircuitBreaker:
    def __init__(
        self,
        failure_threshold=5,      # 连续5次失败
        success_threshold=2,       # 连续2次成功恢复
        timeout=60,               # 60秒后半开
        half_open_max_calls=3     # 半开状态最多尝试3次
    ):
        self.state = CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
```

### 优先级 P1 (中)

#### 3. 多阶段数据刷新

```python
class MultiStageDataFetcher:
    STAGES = [
        {'name': 'realtime', 'timeout': 5, 'source': 'tushare'},
        {'name': 'daily', 'timeout': 30, 'source': 'akshare'},
        {'name': 'historical', 'timeout': 300, 'source': 'baostock'},
    ]
```

#### 4. 完善缓存策略

- 考虑 SQLite 替代 JSON 文件缓存
- 添加缓存命中率统计
- 实现 LRU 淘汰策略

### 优先级 P2 (低)

#### 5. 异步改造

- 将 ThreadPoolExecutor 改为 asyncio
- 更高的并发能力

#### 6. 增强监控

- 数据源健康状态面板
- 失败率趋势图
- 采集耗时统计

---

## 五、总结

| 能力项 | Daily Stock Analysis | stock_picker | 改进建议 |
|--------|---------------------|--------------|----------|
| 数据源数量 | 6个 | 2-3个 | 增加 3-4 个 |
| 故障转移 | ✅ 基础 | ✅ 基础 | 需加熔断 |
| 限流 | 随机延迟 | TokenBucket | 两者皆可 |
| 重试 | 未详述 | 指数退避 | 已完善 |
| 超时 | 未详述 | 30s 装饰器 | 已完善 |
| 数据验证 | 未详述 | 独立模块 | 已完善 |
| 缓存 | SQLite | JSON 文件 | 考虑升级 |
| 并发 | asyncio | ThreadPool | 考虑升级 |

**核心改进点:**
1. 增加数据源 (YFinance, eFinance, Pytdx)
2. 实现智能熔断机制
3. 升级缓存策略 (SQLite)
4. 考虑异步改造 (asyncio)
