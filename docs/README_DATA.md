# 数据管理文档

## 概述

本项目的数据管理分为两个主要部分：
1. **历史数据下载** - 一次性下载全市场历史数据
2. **每日数据更新** - 定时任务增量更新和指标计算

## 数据架构

```
data/
├── cache/                    # 缓存目录
│   ├── stock_hist_*.pkl     # 股票历史数据
│   ├── stock_list_*.pkl     # 股票列表缓存
│   └── industry_stats_*.pkl # 行业统计数据
└── backtest_results/        # 回测结果
```

## 脚本说明

### 1. 历史数据下载脚本

**文件**: `scripts/download_market_data.py`

**功能**:
- 获取全A股列表
- 过滤ST、退市等无效股票
- 下载指定年份范围的日线数据
- 支持断点续传
- 数据完整性验证

**使用方法**:

```bash
# 下载2015年至今的全市场数据（推荐先用小样本测试）
python scripts/download_market_data.py --start-year 2023 --end-year 2024 --max-stocks 100

# 正式下载全市场数据
python scripts/download_market_data.py --start-year 2015

# 从指定股票继续下载（断点续传）
python scripts/download_market_data.py --resume 600000

# 只验证数据，不下载
python scripts/download_market_data.py --verify
```

**数据存储格式**:
- 缓存键: `stock_hist_{code}_{start_date}_{end_date}_qfq`
- 每只股票每年一个文件
- 自动跳过已存在的有效数据

**反爬虫策略**:
- 每次请求延迟 0.05 秒
- 每 100 只股票暂停 3 秒
- 支持断点续传

### 2. 每日数据更新脚本

**文件**: `scripts/daily_update.py`

**功能**:
- 下载当日市场数据
- 计算技术指标（MA5/10/20/60/120/250）
- 更新行业统计数据
- 支持定时任务

**使用方法**:

```bash
# 手动运行今天的更新
python scripts/daily_update.py

# 运行指定日期的更新
python scripts/daily_update.py --date 20250126

# 启动定时任务（每个交易日16:00自动执行）
python scripts/daily_update.py --schedule

# 测试模式（只处理100只股票）
python scripts/daily_update.py --test
```

**计算指标**:
- MA5, MA10, MA20, MA60, MA120, MA250（移动平均线）
- 使用250日历史数据计算
- 结果缓存带 `_with_indicators` 后缀

### 3. 数据验证脚本

**文件**: `scripts/validate_and_fetch_data.py`

**功能**:
- 检查缓存数据完整性
- 统计数据覆盖情况
- 补充缺失数据

**使用方法**:

```bash
# 检查数据完整性
python scripts/validate_and_fetch_data.py --check

# 补充2025年数据
python scripts/validate_and_fetch_data.py --fetch-2025

# 抓取指数数据
python scripts/validate_and_fetch_data.py --fetch-index

# 生成数据报告
python scripts/validate_and_fetch_data.py --report
```

## 技术指标说明

### 移动平均线 (MA)

| 指标 | 周期 | 用途 |
|------|------|------|
| MA5 | 5日 | 短期趋势 |
| MA10 | 10日 | 短期趋势 |
| MA20 | 20日 | 月线趋势 |
| MA60 | 60日 | 季度趋势 |
| MA120 | 120日 | 半年趋势 |
| MA250 | 250日 | 年线趋势 |

### 数据获取策略

1. **最小化网络请求**: 计算指标时优先使用缓存数据
2. **本地计算**: 在本地计算均线等技术指标，避免频繁请求
3. **增量更新**: 每日只下载新增数据，减少API调用
4. **智能缓存**: 自动管理缓存过期时间

## 定时任务配置

建议使用系统 cron 或 Windows 任务计划程序：

### Linux (crontab)

```bash
# 每个交易日 16:00 执行
0 16 * * 1-5 cd /path/to/stock_picker && python scripts/daily_update.py
```

### Windows 任务计划程序

创建基本任务：
- 触发器: 每周一至周五 16:00
- 操作: 运行 `python scripts/daily_update.py`

## 数据完整性检查

### 检查项目

1. **文件数量**: 缓存文件是否完整
2. **数据覆盖**: 日期范围是否连续
3. **字段完整性**: 必需字段是否存在
4. **数据质量**: 是否有空值或异常值

### 修复方法

```bash
# 1. 验证数据
python scripts/validate_and_fetch_data.py --check

# 2. 补充缺失数据
python scripts/download_market_data.py --start-year 2023

# 3. 验证修复结果
python scripts/download_market_data.py --verify
```

## 常见问题

### Q: 下载速度慢？

A: 这是正常的，为了避免触发反爬虫：
- 每次请求延迟 0.05 秒
- 每 100 只股票暂停 3 秒
- 下载全市场约需数小时

### Q: 如何断点续传？

A: 使用 `--resume` 参数：
```bash
python scripts/download_market_data.py --resume 600000
```

### Q: 定时任务没有执行？

A: 检查以下几点：
1. 确认 crontab 或任务计划程序配置正确
2. 检查脚本路径是否正确
3. 查看日志文件确认错误

### Q: 数据文件占用空间大？

A: 可以定期清理旧缓存：
```bash
# 清理2020年之前的数据
find data/cache -name "stock_hist_*201*.pkl" -delete
```

## 附录

### 主要指数代码

| 代码 | 名称 |
|------|------|
| 000001 | 上证指数 |
| 399001 | 深证成指 |
| 399006 | 创业板指 |
| 000300 | 沪深300 |
| 000016 | 上证50 |
| 399905 | 中证500 |

### 数据源

- **行情数据**: 东方财富网 (通过 akshare)
- **行业数据**: 东方财富网行业分类
- **财务数据**: (待实现)
