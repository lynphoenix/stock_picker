# Baostock 项目技术分析文档

## 1. 项目概述

**项目名称**: Baostock
**GitHub**: https://github.com/baostock/baostock
**主要语言**: Python
**许可证**: MIT

Baostock 是**中国A股数据接口库**，提供历史K线、财务数据、宏观数据等，无需注册即可使用。

---

## 2. 项目结构

```
baostock/
├── baostock/              # 核心代码
│   ├── __init__.py
│   ├── bs                 # 主要模块
├── test/                  # 测试
├── docs/                  # 文档
└── setup.py               # 项目配置
```

---

## 3. 核心功能模块

| 模块 | 功能说明 |
|------|----------|
| **登录/登出** | `login()` / `logout()` - 无需注册建立会话 |
| **历史K线** | `query_history_k_data_plus()` - 日/周/月/分钟K线 |
| **股票基本信息** | `query_all_stock()` - A股代码列表 |
| **交易日历** | `query_trade_dates()` - 交易日查询 |
| **实时行情** | `query_real_time_price()` - 快照价格 |
| **复权因子** | `query_adjust_factor()` - 前后复权因子 |
| **分红配送** | `query_dividend_data()` - 股息信息 |
| **财务数据** | 利润表、资产负债表、现金流量表、杜邦分析 |
| **宏观数据** | 贷款利率、存款准备金率、货币供应量 |
| **板块数据** | 行业分类、指数成分股 |

---

## 4. 技术架构

### 4.1 整体架构
```
用户代码 (Python)
        ↓
baostock Python 包
   ├── requests    (HTTP客户端)
   ├── pandas      (数据格式)
   └── ResultSet   (结果解析)
        ↓
BaoStock REST API
```

### 4.2 工作流程
```python
import baostock as bs
import pandas as pd

# 1. 登录 (无需注册)
lg = bs.login()

# 2. 查询历史K线
rs = bs.query_history_k_data_plus(
    "sh.600000",
    "date,open,high,low,close,volume",
    start_date='2022-01-01',
    end_date='2022-12-31',
    frequency="d",
    adjustflag="3"
)

# 3. 转为DataFrame
data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())
df = pd.DataFrame(data_list, columns=rs.fields)

# 4. 登出
bs.logout()
```

### 4.3 数据频率
- 日线 (`d`)
- 周线 (`w`)
- 月线 (`m`)
- 5/15/30/60分钟线

### 4.4 复权机制
- `adjustflag="1"` - 后复权 (适合回测)
- `adjustflag="2"` - 前复权 (适合技术分析)
- `adjustflag="3"` - 不复权 (原始价格)

---

## 5. 技术特点

| 特点 | 说明 |
|------|------|
| **免费开源** | 无需注册，完全免费 |
| **数据丰富** | 覆盖A股、指数、财务、宏观 |
| **易于集成** | pandas DataFrame 输出 |
| **轻量高效** | 依赖少，RESTful 接口 |
| **无需注册** | login() 即可使用 |

---

## 6. 可借鉴的设计

1. **无需注册** - 降低使用门槛
2. **RESTful设计** - HTTP GET/POST + JSON
3. **Pandas优先** - DataFrame 输出
4. **复权因子** - 完整的复权机制

---

*文档生成时间: 2026-02-21*
