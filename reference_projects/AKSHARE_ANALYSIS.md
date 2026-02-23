# AKShare 项目技术分析文档

## 1. 项目概述

**项目名称**: AKShare
**GitHub**: https://github.com/akfamily/akshare
**主要语言**: Python
**Star**: 10,000+
**许可证**: MIT

AKShare 是**中国金融数据接口库**，提供A股、期货、基金、债券等数据的统一访问接口。

---

## 2. 项目结构

```
akshare/
├── akshare/                    # 主包
│   ├── __init__.py            # 统一导出接口
│   ├── request.py             # HTTP请求模块
│   ├── exceptions.py          # 异常定义
│   ├── stock/                 # 股票数据 (45个子目录)
│   ├── stock_feature/         # 股票特征数据
│   ├── stock_fundamental/     # 股票基本面数据
│   ├── futures/               # 期货数据
│   ├── fund/                  # 基金数据
│   ├── bond/                  # 债券数据
│   ├── index/                 # 指数数据
│   ├── forex/                 # 外汇数据
│   ├── crypto/                # 加密货币
│   ├── economic/              # 经济数据
│   └── utils/                 # 工具函数
├── tests/                     # 测试
└── docs/                      # 文档
```

---

## 3. 核心功能模块

| 类别 | 数据源 | 功能示例 |
|------|--------|----------|
| **股票** | 东方财富、新浪、同花顺 | 实时行情、历史K线、资金流向、龙虎榜 |
| **基金** | 天天基金网 | 基金净值、持仓、排行 |
| **期货** | 新浪期货 | 期货行情、持仓 |
| **债券** | 权威债券平台 | 债券行情 |
| **指数** | 各种指数平台 | 指数行情 |
| **期权** | 期权数据源 | 期权数据 |
| **外汇/加密货币** | 外汇/币安API | 实时行情 |

---

## 4. 技术架构

### 4.1 整体架构
```
用户调用 (ak.stock_zh_a_hist())
        ↓
__init__.py 统一导出接口
        ↓
具体数据模块 (stock_feature/stock_hist_em.py)
        ↓
工具层 (utils/func.py, utils/request.py)
        ↓
HTTP请求层 (requests)
        ↓
外部数据源 (东方财富/新浪等)
```

### 4.2 HTTP请求层
```python
# 重试机制 (指数退避 + 随机延迟)
delay = base_delay * (2**attempt) + random.uniform(*random_delay_range)
time.sleep(delay)
```

### 4.3 核心依赖
```
pandas >= 2.0.0       # 数据处理
requests >= 2.22.0    # HTTP客户端
beautifulsoup4        # HTML解析
lxml                  # XML/HTML解析
curl_cffi             # 反爬虫C语言库
tqdm                  # 进度条
py-mini-racer         # JavaScript执行环境
```

### 4.4 异常处理
```python
AkshareException (基类)
├── APIError           # API请求失败
├── DataParsingError  # 数据解析失败
├── InvalidParameterError  # 参数错误
├── NetworkError       # 网络错误
└── RateLimitError     # 频率限制
```

---

## 5. 使用示例

```python
import akshare as ak

# 股票历史K线
df = ak.stock_zh_a_hist(symbol="000001", period="daily",
                         start_date="20220101", end_date="20231231")

# 实时行情
df = ak.stock_zh_a_spot_em()

# 资金流向
df = ak.stock_individual_fund_flow(stock="000001")
```

---

## 6. 技术特点

| 特点 | 说明 |
|------|------|
| **易用性** | 一行代码获取数据 |
| **数据源多样** | 整合多个数据源 |
| **模块化设计** | 按数据类型划分模块 |
| **容错机制** | HTTP重试、指数退避 |
| **反爬应对** | curl_cffi + mini-racer |
| **依赖精简** | 不需要数据库 |

---

## 7. 可借鉴的设计

1. **统一接口** - __init__.py 导出所有接口
2. **重试机制** - 指数退避 + 随机延迟
3. **异常体系** - 清晰的异常分类
4. **代理支持** - ProxyContext 上下文管理器

---

*文档生成时间: 2026-02-21*
