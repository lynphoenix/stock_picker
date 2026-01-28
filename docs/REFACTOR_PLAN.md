# 数据模块架构重构计划

## 当前问题
1. 数据获取和计算逻辑分散在多个文件
2. 没有统一的数据调度机制
3. 计算结果没有持久化
4. 缺少定时任务支持

## 新架构设计

```
src/data/
├── __init__.py
├── cache.py                  # 缓存管理（已有）
├── stock_loader.py           # 股票数据加载（已有）
│
├── fetchers/                 # 数据抓取器（新增）
│   ├── __init__.py
│   ├── market_fetcher.py         # 市场行情数据
│   │   - 抓取日线数据
│   │   - 抓取实时行情
│   │   - 抓取指数数据
│   ├── industry_fetcher.py       # 行业数据
│   │   - 抓取行业分类
│   │   - 抓取成分股列表
│   │   - 抓取行业指数
│   └── fundamental_fetcher.py    # 财务数据
│       - 抓取财报数据
│       - 抓取估值指标
│
├── processors/              # 数据处理器（新增）
│   ├── __init__.py
│   ├── technical_processor.py    # 技术指标
│   │   - 计算均线（MA5, MA10, MA20...）
│   │   - 计算MACD
│   │   - 计算KDJ
│   │   - 计算RSI
│   ├── industry_processor.py     # 行业统计
│   │   - 计算行业涨跌幅
│   │   - 计算行业资金流向
│   │   - 计算行业相对强度
│   └── signal_processor.py       # 信号计算
│       - 计算涨停信号
│       - 计算回调信号
│       - 计算其他策略信号
│
├── schedulers/              # 定时任务（新增）
│   ├── __init__.py
│   ├── data_scheduler.py        # 数据调度器
│   │   - 管理所有定时任务
│   │   - 任务依赖管理
│   │   - 失败重试
│   └── tasks.py                 # 具体任务
│       - update_daily_data()    # 每日数据更新
│       - update_industry_data() # 行业数据更新
│       - calculate_indicators() # 指标计算
│       - generate_signals()     # 信号生成
│
└── storage/                 # 数据存储（新增）
    ├── __init__.py
    ├── base.py                   # 存储基类
    ├── file_store.py             # 文件存储
    └── db.py                     # 数据库存储（可选）
```

## 数据流设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        定时任务调度器                              │
│                    (每天自动执行)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据抓取器                                │
│  1. 抓取日线数据                                                 │
│  2. 抓取行业数据                                                 │
│  3. 抓取财务数据                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据处理器                                │
│  1. 计算技术指标（均线、MACD等）                                 │
│  2. 计算行业统计数据                                             │
│  3. 生成交易信号                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据存储                                  │
│  1. 持久化到文件/数据库                                          │
│  2. 建立索引                                                    │
│  3. 缓存热点数据                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     应用层（策略、回测等）                        │
│  - 直接读取预处理好的数据                                        │
│  - 不需要重复计算                                                │
└─────────────────────────────────────────────────────────────────┘
```

## 实施计划

### Phase 1: 创建新目录结构
```bash
mkdir -p src/data/{fetchers,processors,schedulers,storage}
```

### Phase 2: 迁移现有代码
1. **data_fetcher.py** → `src/data/fetchers/market_fetcher.py`
2. **fundamentals.py** → `src/data/fetchers/fundamental_fetcher.py`
3. **technical.py** → `src/data/processors/technical_processor.py`
4. **scripts/analyze_results_by_sector.py** → `src/data/processors/industry_processor.py`

### Phase 3: 创建定时任务
创建 `src/data/schedulers/data_scheduler.py`
- 每日盘后更新数据
- 计算技术指标
- 生成交易信号

### Phase 4: 优化存储
- 添加数据库支持（SQLite）
- 优化文件存储结构

## 数据存储结构

```
data/
├── market/                  # 市场数据
│   ├── daily/              # 日线数据
│   │   └── {stock_code}.csv
│   ├── realtime/           # 实时数据
│   └── index/              # 指数数据
│
├── industry/               # 行业数据
│   ├── classification/     # 行业分类
│   ├── constituents/       # 成分股
│   └── statistics/         # 行业统计
│
├── indicators/            # 技术指标
│   ├── ma/                 # 均线
│   ├── macd/
│   └── signals/            # 交易信号
│
└── backtest/              # 回测结果
    └── results/
```

## 定时任务配置

```python
# config/scheduler.yaml
tasks:
  - name: update_daily_data
    schedule: "15:30"  # 每个交易日15:30
    function: update_market_data

  - name: calculate_indicators
    schedule: "16:00"  # 每个交易日16:00
    function: calculate_all_indicators

  - name: update_industry_stats
    schedule: "16:30"
    function: update_industry_statistics

  - name: generate_signals
    schedule: "17:00"
    function: generate_trading_signals
```

要开始实施这个重构吗？
