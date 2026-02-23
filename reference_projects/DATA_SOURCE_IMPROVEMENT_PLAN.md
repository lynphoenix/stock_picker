# 数据源模块改进计划

## 概述

基于 `DATA_SOURCE_DEEP_ANALYSIS.md` 分析结果，结合当前资源约束（无实时数据key、H100服务器部署），制定本改进计划。

### 约束条件
- **历史数据**: 使用 Baostock（免费、稳定）
- **实时数据**: 暂不测试（等待Tushare key）
- **部署环境**: H100 服务器
- **市场范围**: A股（一期），美股/港股（二期）

---

## 改进路线图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         改进时间线                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Phase 1 (本期)        │  Phase 2 (未来)                            │
│  ─────────────────────┼─────────────────────────────               │
│  • 智能熔断机制        │  • YFinance (美股/港股)                   │
│  • 多阶段数据刷新      │  • eFinance                                │
│  • 缓存策略升级        │  • Pytdx                                   │
│  • 并发采集优化        │  • 多市场统一接口                          │
│  • 监控面板            │                                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: 核心能力提升 ✅ 完成

### 1.1 智能熔断机制 [P0] ✅ 完成

**目标**: 实现 CircuitBreaker 模式，自动检测和恢复数据源故障

**实现位置**: `src/circuit_breaker.py` (新建)

**功能规格**:

```python
class DataSourceCircuitBreaker:
    """
    数据源熔断器

    状态机:
    CLOSED (正常) → OPEN (熔断) → HALF_OPEN (半开)
    """

    def __init__(
        self,
        failure_threshold: int = 5,      # 连续5次失败触发熔断
        success_threshold: int = 2,       # 连续2次成功恢复
        timeout: int = 60,               # 60秒后半开状态
        half_open_max_calls: int = 3      # 半开状态最多尝试3次
    ):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
```

**与现有系统集成**:

```python
# src/data_source_manager.py 改造

class DataSourceManager:
    def __init__(self, ...):
        # 新增熔断器
        self.circuit_breakers = {
            DataSource.AKSHARE: DataSourceCircuitBreaker(),
            DataSource.BAOSTOCK: DataSourceCircuitBreaker(),
            DataSource.TUSHARE: DataSourceCircuitBreaker(),
        }

    def fetch_with_fallback(self, ...):
        for source in sorted(self.sources, key=lambda x: x['priority']):
            breaker = self.circuit_breakers[source['name']]

            # 检查熔断状态
            if breaker.is_open():
                logger.info(f"{source['name']} 熔断中，跳过")
                continue

            try:
                result = self._fetch_from_source(...)
                if result.success:
                    breaker.record_success()
                else:
                    breaker.record_failure()
                return result
            except Exception as e:
                breaker.record_failure()
                continue
```

**任务清单**:
- [ ] 创建 `src/circuit_breaker.py`
- [ ] 实现熔断状态机 (CLOSED/OPEN/HALF_OPEN)
- [ ] 改造 `DataSourceManager` 集成熔断器
- [ ] 添加熔断事件日志
- [ ] 单元测试

**预计工作量**: 2-3 小时

---

### 1.2 多阶段数据刷新 [P0] ✅ 完成

**目标**: 实现 realtime → daily → historical 多阶段降级

**实现位置**: `src/multi_stage_fetcher.py` (新建)

**功能规格**:

```python
class MultiStageDataFetcher:
    """
    多阶段数据获取器

    降级策略:
    1. realtime (5s timeout)  - 实时行情
    2. daily (30s timeout)   - 日线数据
    3. historical (300s timeout) - 历史数据
    """

    STAGES = [
        {'name': 'realtime', 'timeout': 5, 'source': 'tushare'},
        {'name': 'daily', 'timeout': 30, 'source': 'baostock'},
        {'name': 'historical', 'timeout': 300, 'source': 'baostock'},
    ]

    def fetch(self, symbol: str, data_type: str = 'daily') -> FetchResult:
        stage = self._select_stage(data_type)
        return self._fetch_with_stage(symbol, stage)
```

**使用场景**:

```python
# 场景1: 需要最新收盘价 (降级到 daily)
fetcher.fetch('000001', data_type='daily')

# 场景2: 需要历史回测数据 (直接用 historical)
fetcher.fetch('000001', data_type='historical', start_date='20200101')

# 场景3: 需要实时行情 (先试 realtime，失败则降级)
fetcher.fetch('000001', data_type='realtime')
```

**任务清单**:
- [ ] 创建 `src/multi_stage_fetcher.py`
- [ ] 实现 stage 选择逻辑
- [ ] 实现超时降级
- [ ] 集成到 DataManager
- [ ] 单元测试

**预计工作量**: 2 小时

---

### 1.3 缓存策略升级 (SQLite) [P1] ✅ 完成

**目标**: 使用 SQLite 替代 JSON 文件缓存，支持索引和复杂查询

**实现位置**: `src/cache_manager.py` (改造)

**功能规格**:

```python
class SQLiteCacheManager:
    """
    SQLite 缓存管理器

    优势:
    - 支持 SQL 查询
    - 自动索引
    - 并发读写
    - 持久化可靠
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.CACHE_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        CREATE TABLE IF NOT EXISTS stock_cache (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            data_type TEXT NOT NULL,  # 'daily', 'realtime', 'fundamental'
            start_date TEXT,
            end_date TEXT,
            data_json TEXT NOT NULL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, data_type, start_date, end_date)
        );

        CREATE INDEX IF NOT EXISTS idx_symbol ON stock_cache(symbol);
        CREATE INDEX IF NOT EXISTS idx_data_type ON stock_cache(data_type);
        CREATE INDEX IF NOT EXISTS idx_updated_at ON stock_cache(updated_at);
```

**缓存策略**:
- **命中率统计**: 记录 hit/miss
- **LRU 淘汰**: 保留最近 30 天的数据
- **压缩**: 使用 zlib 压缩大数据

**任务清单**:
- [ ] 改造 `src/cache_manager.py` 为 SQLite
- [ ] 实现缓存命中率统计
- [ ] 实现 LRU 自动淘汰
- [ ] 数据迁移脚本 (JSON → SQLite)
- [ ] 性能测试

**预计工作量**: 3-4 小时

---

### 1.4 并发采集优化 [P1] ✅ 完成

**目标**: 使用 asyncio 替代 ThreadPoolExecutor，提高并发能力

**实现位置**: `src/async_fetcher.py` (新建)

**功能规格**:

```python
class AsyncDataFetcher:
    """
    异步数据采集器

    使用 asyncio 并发采集
    适用于大规模股票池批量采集
    """

    def __init__(self, max_concurrent: int = 20):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_batch(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, FetchResult]:
        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self.fetch_one(symbol, start_date, end_date))
                for symbol in symbols
            ]
        return {symbol: task.result() for symbol, task in zip(symbols, tasks)}
```

**性能对比**:

| 方案 | 100只股票 | 1000只股票 |
|------|----------|------------|
| ThreadPool (10 workers) | ~30s | ~300s |
| asyncio (20 concurrent) | ~10s | ~60s |

**任务清单**:
- [ ] 创建 `src/async_fetcher.py`
- [ ] 实现异步采集逻辑
- [ ] 改造批量采集任务使用异步
- [ ] 性能测试

**预计工作量**: 2-3 小时

---

### 1.5 监控面板 [P2] ✅ 完成

**目标**: 实时显示数据源健康状态、采集统计

**实现位置**: `backend/app/api/monitoring.py` (已存在，添加新接口)

**功能规格**:

```python
@router.get("/data-source-stats")
async def get_data_source_stats():
    """获取数据源状态统计"""

    return {
        "sources": [
            {
                "name": "baostock",
                "status": "healthy",  # healthy, degraded, circuit_open
                "failure_count": 0,
                "success_count": 1523,
                "success_rate": 99.8,
                "avg_response_time": 0.32,
                "circuit_state": "closed",
            },
            # ...
        ],
        "cache": {
            "hit_rate": 87.5,
            "total_requests": 12345,
            "cache_hits": 10802,
            "cache_misses": 1543,
        },
        "采集": {
            "today_total": 5234,
            "success": 5218,
            "failed": 16,
        }
    }
```

**前端展示**:
- 数据源状态卡片 (绿/黄/红)
- 成功率折线图
- 缓存命中率仪表盘
- 采集量统计

**任务清单**:
- [ ] 新增监控 API 接口
- [ ] 集成熔断器状态
- [ ] 集成缓存统计
- [ ] 前端监控页面
- [ ] 单元测试

**预计工作量**: 3-4 小时

---

## Phase 2: 多市场支持 (未来)

### 2.1 YFinance 数据源

**目标**: 支持美股/港股历史数据

**实现位置**: `src/data_providers/yfinance_provider.py` (新建)

```python
class YFinanceProvider:
    """Yahoo Finance 数据提供器"""

    def fetch_history(
        self,
        symbol: str,  # e.g., 'AAPL', '00700.HK'
        start_date: str,
        end_date: str,
        period: str = '1d'
    ) -> FetchResult:
        # 使用 yfinance 库
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, period=period)
        return FetchResult(success=True, data=df, source='yfinance')
```

### 2.2 eFinance 数据源

**目标**: A股数据补充

### 2.3 Pytdx 数据源

**目标**: 通达信数据（Level-2行情）

---

## 任务汇总

### Phase 1 任务清单

| 序号 | 任务 | 优先级 | 工作量 | 依赖 |
|------|------|--------|--------|------|
| 1.1 | 智能熔断机制 | P0 | 2-3h | - |
| 1.2 | 多阶段数据刷新 | P0 | 2h | 1.1 |
| 1.3 | SQLite 缓存升级 | P1 | 3-4h | - |
| 1.4 | 异步并发优化 | P1 | 2-3h | - |
| 1.5 | 监控面板 | P2 | 3-4h | 1.1, 1.3 |

### 预计总工作量

- **最小**: 9-12 小时
- **最大**: 15-18 小时

---

## 部署计划

### H100 服务器部署

```bash
# 1. 代码部署
cd /opt/stock_picker
git pull origin main

# 2. 安装依赖
pip install aiosqlite yfinance

# 3. 数据库迁移
python -m scripts.migrate_cache_to_sqlite

# 4. 重启服务
pm2 restart stock_picker

# 5. 验证
curl http://localhost:8000/api/data-source-stats
```

### 验证清单

- [ ] 熔断机制触发测试 (模拟数据源失败)
- [ ] 多阶段降级测试
- [ ] 缓存命中率 > 80%
- [ ] 批量采集性能测试 (1000只股票)
- [ ] 监控面板数据准确

---

## 优先级建议

**建议执行顺序**:

1. **智能熔断** - 最影响稳定性，优先实现
2. **多阶段刷新** - 提升容错能力
3. **SQLite 缓存** - 性能提升明显
4. **异步并发** - 批量采集性能
5. **监控面板** - 运维辅助

---

*文档版本: v1.0*
*创建时间: 2026-02-22*
