# Fibooks 项目技术分析文档

## 1. 项目概述

**项目名称**: Fibooks
**GitHub**: https://github.com/TimoKats/fibooks
**许可证**: MIT

Fibooks 是一个**财务报表分析Python库**，支持三张财务报表的分析和估值。

---

## 2. 项目结构

```
fibooks/
├── fibooks/
│   ├── balance_sheet.py       # 资产负债表
│   ├── income_statement.py    # 利润表
│   ├── statement_of_cashflows.py  # 现金流量表
│   ├── excel_parser.py       # Excel解析
│   └── other.py              # 估值工具
└── demo/
```

---

## 3. 核心功能

### 3.1 三大财务报表类

| 类 | 功能 |
|-----|------|
| `balance_sheet` | 资产负债表分析 |
| `income_statement` | 利润表分析 |
| `statement_of_cashflows` | 现金流量表分析 |

### 3.2 分析工具

- `npv()` - 净现值计算
- `combine_statements()` - 合并报表
- `income_based_valuation()` - 基于收入的估值

---

## 4. 技术架构

- **数据格式**: Excel/CSV/Pandas DataFrame
- **依赖**: openpyxl, pandas
- **设计模式**: 模板驱动 (JSON模板)

---

## 5. 特点

| 特点 | 说明 |
|------|------|
| 轻量级 | 专注于财务报表分析 |
| 模板驱动 | JSON定义科目分类 |
| 易扩展 | 面向对象设计 |

---

*文档生成时间: 2026-02-22*
