# 数据采集模块详细设计方案

> 版本: v1.0
> 日期: 2026-02-24
> 参考: Daily Stock Analysis + Baostock

---

## 一、模块架构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端 (React)                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  采集控制面板 (FetchControlPanel)                                     │  │
│  │  - 手动触发按钮 | 股票池选择 | 日期范围选择                           │  │
│  │  - 实时进度条 | 成功率统计 | 错误日志                              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │ HTTP/WebSocket
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                            后端 (FastAPI)                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │  采集API        │  │  状态API         │  │  WebSocket                │ │
│  │  - fetch-now   │  │  - status       │  │  - 实时进度推送           │ │
│  │  - fetch-stop  │  │  - stats        │  │  - 错误通知               │ │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬────────────┘ │
└───────────┼────────────────────┼──────────────────────────┼──────────────┘
            │                    │                          │
┌───────────▼────────────────────▼──────────────────────────▼──────────────┐
│                         采集服务层 (AutoDataFetcher)                        │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         调度控制器                                     │ │
│  │  - 定时任务触发 (DataScheduler)                                      │ │
│  │  - 手动任务触发 (API调用)                                            │ │
│  │  - 任务状态管理 (running/paused/stopped)                             │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         采集核心                                      │ │
│  │  - 股票列表获取 (stock_pools.json / API)                            │ │
│  │  - 缓存检查 (增量采集)                                              │ │
│  │  - 并发控制器 (asyncio.Semaphore)                                   │ │
│  │  - 速率限制 (随机延迟 0-2秒)                                        │ │
│  │  - 采集统计 (FetchStats)                                            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                       数据源层 (DataSourceManager)                          │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      数据源优先级管理器                               │  │
│   │   优先级: Baostock(主,priority=1) → AKShare(备,priority=2)       │  │
│   │   故障转移: 当前源失败自动切换到备用源                               │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────┐ │
│   │    Baostock        │    │    AKShare          │    │   Tushare      │ │
│   │  - login/logout   │    │  - get_hist_...    │    │ (可选,需token) │ │
│   │  - query_hist... │    │  - get_realtime    │    │                 │ │
│   │  - 线程安全      │    │                     │    │                 │ │
│   └─────────────────────┘    └─────────────────────┘    └─────────────────┘ │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      熔断器 (CircuitBreaker)                         │  │
│   │   状态: CLOSED(正常) → OPEN(熔断) → HALF_OPEN(半开)                │  │
│   │   触发: 连续5次失败 → OPEN                                          │  │
│   │   恢复: 连续2次成功 → CLOSED                                        │  │
│   │   超时: 60秒后进入HALF_OPEN                                         │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                          缓存层 (SQLiteCacheManager)                        │
│                                                                             │
│   stock_cache 表:                                                          │
│   ┌────────────┬────────────┬──────────┬──────────┬────────────┬────────┐ │
│   │ id(PK)    │ symbol     │ data_type│ start_dt │ end_dt    │ data   │ │
│   ├────────────┼────────────┼──────────┼──────────┼────────────┼────────┤ │
│   │ 1         │ 000001     │ daily    │20250101  │20250110   │ {...}  │ │
│   └────────────┴────────────┴──────────┴──────────┴────────────┴────────┘ │
│                                                                             │
│   索引: symbol, data_type, start_dt, end_dt                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、模块详细设计

### 2.1 采集核心模块 (AutoDataFetcher)

**文件**: `core/data/auto_fetcher.py`

**参考**: Daily Stock Analysis - 定时任务 + 失败重试

```python
class AutoDataFetcher:
    """
    自动数据采集器

    设计要点:
    1. 支持定时/手动两种触发方式
    2. 增量采集：检查缓存，只采集缺失数据
    3. 并发控制：避免对数据源压力过大
    4. 随机延迟：避免API限流 (参考 Daily Stock Analysis)
    5. 采集统计：记录成功/失败/跳过
    """

    def __init__(self):
        self.data_source_manager = DataSourceManager()  # 整合多数据源
        self.cache = SQLiteCacheManager()               # SQLite缓存
        self.stats = FetchStats()
        self.status = FetchStatus.IDLE
        self.current_task = None

    def should_fetch_today(self) -> bool:
        """
        判断今天是否为交易日

        实现逻辑:
        1. 检查是否周末 (weekday >= 5)
        2. 检查是否节假日 (chinese_calendar.is_holiday)

        Returns:
            True: 是交易日
            False: 非交易日
        """
        pass

    def get_stock_list(self) -> List[str]:
        """
        获取股票代码列表

        优先级:
        1. stock_pools.json (自定义股票池)
        2. DataSourceManager.get_stock_list() (API获取)
        3. 默认股票列表 (常用30只)

        Returns:
            股票代码列表
        """
        pass

    def is_cache_valid(self, symbol: str, start_date: str, end_date: str) -> bool:
        """
        检查缓存是否有效

        实现逻辑:
        1. 查询 SQLite 缓存表
        2. 检查数据完整性 (记录数 > 0)

        Returns:
            True: 缓存有效
            False: 需要重新采集
        """
        pass

    async def fetch_daily_data(
        self,
        stock_pool: str = "all",
        start_date: str = None,
        end_date: str = None,
        max_concurrent: int = 10,
        retry_times: int = 3,
        on_progress: Callable = None
    ) -> Dict[str, Any]:
        """
        执行每日数据采集

        参数:
            stock_pool: 股票池 (all/AI软件/半导体/机器人)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            max_concurrent: 最大并发数
            retry_times: 失败重试次数
            on_progress: 进度回调函数

        实现逻辑 (参考 Daily Stock Analysis):
            1. 获取股票列表
            2. 检查缓存，决定需要采集的股票
            3. 并发采集 (Semaphore控制)
            4. 每次请求随机延迟 0-2秒 (避免限流)
            5. 失败重试 (最多3次)
            6. 保存到缓存
            7. 更新进度

        Returns:
            {
                "status": "completed",
                "total": 5000,
                "success": 4950,
                "failed": 50,
                "skipped": 100,
                "duration": 600.5,
                "errors": [...]
            }
        """
        pass

    def _fetch_with_retry(self, symbol, start_date, end_date, retry_times):
        """
        带重试的采集

        实现逻辑:
            1. 调用 DataSourceManager.fetch_with_fallback()
            2. 失败则重试，最多重试retry_times次
            3. 返回 FetchResult
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """获取当前采集状态"""
        pass
```

---

### 2.2 数据源管理模块 (DataSourceManager)

**文件**: `src/data_source_manager.py` (已有，需启用)

**参考**: Baostock 官方API + Daily Stock Analysis 多源策略

```python
class DataSourceManager:
    """
    多数据源管理器

    设计要点 (参考 Baostock + Daily Stock Analysis):
    1. 多源优先级: Baostock(主) → AKShare(备)
    2. 故障转移: 主源失败自动切换到备源
    3. 熔断机制: 连续失败5次触发熔断
    4. 线程安全: Baostock 需要线程本地存储
    """

    def __init__(self, tushare_token: str = None):
        """
        初始化数据源管理器

        数据源优先级:
        - 有tushare: tushare → baostock → akshare
        - 无tushare: baostock → akshare

        每个数据源配有 CircuitBreaker
        """
        pass

    def fetch_with_fallback(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> FetchResult:
        """
        故障转移采集

        实现逻辑:
            1. 按优先级遍历数据源
            2. 检查熔断器状态
            3. 调用数据源获取数据
            4. 成功则记录，失败则切换下一个
            5. 全部失败返回失败结果

        Returns:
            FetchResult (success, data, error_message, source)
        """
        pass

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取股票列表

        使用 Baostock: query_all_stock()

        Returns:
            DataFrame columns: [code, name, exchange]
        """
        pass
```

---

### 2.3 Baostock 数据源

**文件**: `src/data_source_manager.py` (已有实现)

**参考**: Baostock 官方文档

```python
# Baostock 关键实现细节

# 1. 登录/登出 (线程安全)
import baostock as bs

# 每个线程独立登录
if not hasattr(_thread_local, 'bs_logged_in') or not _thread_local.bs_logged_in:
    lg = bs.login()
    _thread_local.bs_logged_in = True

# 2. 股票代码转换
def convert_symbol(symbol: str) -> str:
    """股票代码转换为 Baostock 格式"""
    if symbol.startswith('6'):
        return f'sh.{symbol}'  # 沪市
    else:
        return f'sz.{symbol}'  # 深市

# 3. 日期格式转换
def convert_date(date: str) -> str:
    """YYYYMMDD → YYYY-MM-DD"""
    if len(date) == 8 and date.isdigit():
        return f'{date[:4]}-{date[4:6]}-{date[6:8]}'
    return date

# 4. 周期转换
PERIOD_MAP = {'daily': 'd', 'weekly': 'w', 'monthly': 'm'}

# 5. 复权类型转换
ADJUST_MAP = {'qfq': '1', 'hfq': '2', '': '3'}

# 6. 查询字段
FIELDS = "date,code,open,high,low,close,volume,amount"

# 7. 示例调用
rs = bs.query_history_k_data_plus(
    "sh.600000",           # 股票代码
    FIELDS,                # 字段
    start_date='2025-01-01',
    end_date='2025-01-10',
    frequency="d",         # 日线
    adjustflag="1"        # 前复权
)

# 8. 结果解析
data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())
df = pd.DataFrame(data_list, columns=rs.fields)
```

---

### 2.4 熔断器模块 (CircuitBreaker)

**文件**: `src/circuit_breaker.py` (已有实现)

**参考**: 经典熔断器模式

```python
class CircuitState(Enum):
    CLOSED = "closed"      # 正常：允许请求
    OPEN = "open"          # 熔断：拒绝请求
    HALF_OPEN = "half_open"  # 半开：允许探测

class DataSourceCircuitBreaker:
    """
    数据源熔断器

    设计参数 (参考 Daily Stock Analysis 故障处理):
        - failure_threshold: 5 (连续5次失败触发熔断)
        - success_threshold: 2 (连续2次成功恢复)
        - timeout: 60 (60秒后进入半开状态)
        - half_open_max_calls: 3 (半开状态最多探测3次)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0

    def is_open(self) -> bool:
        """检查是否熔断中"""
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).seconds
                if elapsed > self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return False  # 半开状态，允许尝试
            return True  # 熔断中
        return False

    def record_success(self):
        """记录成功"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            self.failure_count = 0

    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN  # 重新熔断
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

---

### 2.5 缓存模块 (SQLiteCacheManager)

**文件**: `src/sqlite_cache_manager.py` (已有实现，需启用)

```python
class SQLiteCacheManager:
    """
    SQLite缓存管理器

    设计要点:
    1. 表结构: stock_cache
    2. 索引: symbol, data_type, start_date, end_date
    3. TTL: 可配置过期时间
    4. 压缩: 大数据使用 zlib 压缩
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.CACHE_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        CREATE TABLE IF NOT EXISTS stock_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            data_type TEXT NOT NULL,  # 'daily', 'realtime', 'fundamental'
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            data BLOB NOT NULL,       # zlib 压缩的 JSON
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, data_type, start_date, end_date)
        )

        CREATE INDEX IF NOT EXISTS idx_symbol ON stock_cache(symbol)
        CREATE INDEX IF NOT EXISTS idx_data_type ON stock_cache(data_type)
        CREATE INDEX IF NOT EXISTS idx_dates ON stock_cache(start_date, end_date)

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """读取缓存"""
        pass

    def set(self, key: str, value: Any, metadata: dict = None):
        """写入缓存"""
        pass
```

---

### 2.6 调度模块 (DataScheduler)

**文件**: `backend/scheduler.py` (已有框架，需完善)

```python
class DataScheduler:
    """
    定时任务调度器

    设计要点 (参考 Daily Stock Analysis GitHub Actions):
    1. 定时触发: 每日21:30 (北京时间)
    2. 交易日检查: 自动跳过周末/节假日
    3. 随机延迟: 0-60秒，避免API高峰
    """

    def schedule_daily_fetch(self, hour: int = 21, minute: int = 30):
        """配置每日定时采集"""
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone="Asia/Shanghai"
        )
        self.scheduler.add_job(
            func=self._fetch_job,
            trigger=trigger,
            id="daily_data_fetch",
            name="每日数据采集",
            replace_existing=True
        )

    def _fetch_job(self):
        """定时任务执行"""
        # 1. 检查是否交易日
        if not self.fetcher.should_fetch_today():
            print("⏸️  今日非交易日，跳过")
            return

        # 2. 随机延迟 0-60秒 (参考 Daily Stock Analysis)
        import random
        delay = random.randint(0, 60)
        print(f"⏳ 随机延迟 {delay} 秒...")
        time.sleep(delay)

        # 3. 执行采集
        result = self.fetcher.fetch_daily_data(
            stock_pool="all",
            start_date=None,  # 自动计算
            end_date=None
        )
```

---

### 2.7 后端 API

**文件**: `backend/app/api/data.py` (需完善)

```python
@router.post("/fetch-now")
async def trigger_fetch_now(
    stock_pool: str = "all",
    start_date: str = None,
    end_date: str = None,
    background_tasks: BackgroundTasks = None
):
    """
    手动触发数据采集

    Body:
        stock_pool: 股票池 (all/AI软件/半导体/机器人)
        start_date: 开始日期 (YYYYMMDD, 可选)
        end_date: 结束日期 (YYYYMMDD, 可选)

    Response:
        {
            "task_id": "uuid",
            "status": "started",
            "message": "数据采集已启动"
        }
    """
    task_id = str(uuid.uuid4())
    # 启动后台任务
    asyncio.create_task(run_fetch_task(task_id, stock_pool, start_date, end_date))
    return {"task_id": task_id, "status": "started"}


@router.get("/fetch/status/{task_id}")
async def get_fetch_status(task_id: str):
    """获取采集进度"""
    pass


@router.get("/fetch/stats")
async def get_fetch_stats():
    """获取采集统计"""
    pass


@router.get("/fetch/stop")
async def stop_fetch():
    """停止采集"""
    pass
```

---

### 2.8 前端采集控制面板

**文件**: `frontend/src/pages/FetchControl.tsx` (新建)

```tsx
// 组件设计

interface FetchControlPanelProps {
  // Props
}

// 功能:
// 1. 手动触发按钮
// 2. 股票池选择 (all/AI软件/半导体/机器人)
// 3. 日期范围选择
// 4. 实时进度条 (Progress)
// 5. 统计卡片 (Total/Success/Failed/Skipped)
// 6. 错误日志表格
// 7. 停止按钮
```

---

## 三、测试计划

### 3.1 单元测试

| 测试项 | 测试内容 | 验收标准 | 测试文件 |
|--------|---------|---------|---------|
| **should_fetch_today** | 节假日/周末判断 | 周末返回False，交易日返回True | `tests/test_fetcher.py` |
| **get_stock_list** | 股票列表获取 | 返回非空列表 | `tests/test_fetcher.py` |
| **is_cache_valid** | 缓存检查 | 有缓存返回True，无返回False | `tests/test_cache.py` |
| **fetch_daily_data** | 单股票采集 | 返回非空DataFrame | `tests/test_fetcher.py` |
| **fetch_with_retry** | 重试机制 | 失败重试3次，记录失败 | `tests/test_fetcher.py` |
| **DataSourceManager** | 多源fallback | 主源失败自动切换备源 | `tests/test_data_source.py` |
| **CircuitBreaker** | 熔断/恢复 | 5次失败熔断，2次成功恢复 | `tests/test_circuit_breaker.py` |
| **SQLiteCache** | 缓存读写 | 写入后可读取，数据一致 | `tests/test_cache.py` |

### 3.2 集成测试

| 测试项 | 测试内容 | 验收标准 | 测试文件 |
|--------|---------|---------|---------|
| **Scheduler** | 定时任务触发 | 21:30自动执行 | `tests/test_scheduler.py` |
| **API-fetch-now** | 采集接口 | 返回task_id | `tests/test_api.py` |
| **API-fetch-status** | 进度查询 | 返回实时进度 | `tests/test_api.py` |
| **增量采集** | 已有缓存跳过 | 第二次采集跳过缓存 | `tests/test_integration.py` |
| **采集统计** | 统计正确 | success+failed+skipped=total | `tests/test_integration.py` |

### 3.3 E2E测试

| 测试场景 | 操作步骤 | 验收标准 | 工具 |
|---------|---------|---------|------|
| **手动采集** | 1. 前端点击"立即采集"<br>2. 等待完成<br>3. 检查缓存 | 缓存文件数量增加 | Playwright |
| **进度显示** | 1. 触发采集<br>2. 查看进度条 | 进度百分比正确更新 | Playwright |
| **统计展示** | 1. 采集完成<br>2. 查看统计 | Success/Failed正确 | Playwright |
| **错误处理** | 1. 断网采集<br>2. 查看错误日志 | 错误正确显示 | Playwright |
| **全量采集** | 1. 触发全量采集<br>2. 等待完成 | 5000+股票采集成功 | Playwright |

---

## 四、验收计划

### 4.1 功能验收

| 序号 | 功能 | 验收条件 | 测试方法 |
|------|------|---------|---------|
| 1 | 交易日判断 | 周末返回False，工作日返回True | 单元测试 |
| 2 | 股票列表获取 | 返回A股股票代码列表 | 单元测试 |
| 3 | Baostock采集 | 单股票数据正确返回 | 单元测试 |
| 4 | 多源fallback | Baostock失败自动切换AKShare | 集成测试 |
| 5 | 熔断机制 | 连续5次失败触发熔断 | 集成测试 |
| 6 | 缓存存储 | 采集后数据写入SQLite | 集成测试 |
| 7 | 增量采集 | 已有缓存的股票跳过 | E2E测试 |
| 8 | API触发 | /api/data/fetch-now 返回200 | API测试 |
| 9 | 进度查询 | /api/data/fetch/stats 返回实时进度 | API测试 |
| 10 | 前端采集 | 点击按钮触发，前端显示进度 | E2E测试 |

### 4.2 性能验收

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 单股票采集 | <3秒 | 计时测试 |
| 100股票采集 | <60秒 (串行) | 计时测试 |
| 并发采集 | <30秒 (10并发) | 计时测试 |
| API响应 | <500ms | 性能测试 |
| 5000股票采集 | <30分钟 | 完整采集测试 |

### 4.3 稳定性验收

| 场景 | 预期行为 |
|------|---------|
| 网络超时 | 自动重试3次，记录失败 |
| 数据源故障 | 熔断器触发，切换备用源 |
| 采集中断 | 可停止，状态正确保存 |
| 重复采集 | 幂等处理，不重复写入 |
| 非交易日 | 自动跳过，不执行采集 |

---

## 五、实施顺序

```
Phase 1: 核心采集 (第1天)
├── 1.1 完善 auto_fetcher.py
├── 1.2 测试 Baostock 单股票采集
├── 1.3 测试多源fallback
└── 1.4 单元测试

Phase 2: 缓存+熔断 (第2天)
├── 2.1 启用 SQLiteCacheManager
├── 2.2 启用 CircuitBreaker
├── 2.3 增量采集逻辑
└── 2.4 集成测试

Phase 3: 后端API (第3天)
├── 3.1 完善 /api/data/fetch-now
├── 3.2 完善 /api/data/fetch/stats
├── 3.3 任务状态管理
└── 3.4 API测试

Phase 4: 前端 (第4天)
├── 4.1 创建 FetchControlPanel 组件
├── 4.2 集成到 DataMonitoring 页面
├── 4.3 进度展示
└── 4.4 E2E测试

Phase 5: 全量采集测试 (第5天)
├── 5.1 触发全量采集
├── 5.2 监控采集进度
├── 5.3 解决问题
└── 5.4 最终验收
```

---

*文档版本: v1.0*
*等待用户批准后开始实施*
