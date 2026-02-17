# 智能投研助手系统设计文档

**项目名称**: A股/港股/美股智能投研助手
**版本**: v3.0
**设计日期**: 2026-02-17
**状态**: 设计阶段

---

## 1. 项目概述

### 1.1 项目目标

在现有A股智能选股系统的基础上，构建一个**智能投研助手系统**，实现：

1. **市场数据汇总分析** - 技术面 + 舆情 + 财报多维度分析
2. **聊天交互界面** - 对话式股票筛选和分析
3. **智能买卖点生成** - 给出具体操作信号和价格点位
4. **审核分析论证** - 对每个信号进行推理验证

### 1.2 核心需求

| 需求 | 描述 | 优先级 |
|------|------|--------|
| 实时交易信号 | 系统自动提示买卖点 | P0 |
| 多市场支持 | A股 + 港股 + 美股 | P0 |
| 舆情分析 | 新闻情感分析，热点追踪 | P0 |
| 财报分析 | 三大报表解析，财务指标计算 | P0 |
| 投资组合优化 | 基于风险和收益的仓位分配 | P1 |
| 聊天界面 | 自然语言交互选股 | P0 |
| 仪表板 | 实时监控和可视化 | P1 |
| 数据质量监控 | 数据完整性检查和修复 | P1 |

### 1.3 用户场景

**典型对话流程:**
```
用户: "帮我找一些AI板块的股票，ROE>15%，最近有催化剂"

系统:
1. 筛选: AI板块 + ROE>15% + 市值>50亿
2. 分析: 财报、舆情、技术面
3. 信号: 科大讯飞买入，目标¥55，止损¥44，仓位15%
4. 审核: 验证数据时效、逻辑合理性、风险边界
```

---

## 2. 系统架构

### 2.1 整体分层架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          用户交互层 (Frontend)                           │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐    │
│  │       AI 聊天助手              │  │        量化仪表板              │    │
│  │  • 对话选股                    │  │  • 行情监控                  │    │
│  │  • 意图理解                    │  │  • 信号推送                  │    │
│  │  • 论证展示                    │  │  • 数据质量监控              │    │
│  └──────────────────────────────┘  └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                     ▲
                                     │ WebSocket + REST API
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         服务层 (Backend Services)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ ChatService │  │ DataService  │  │SignalService│  │QualityService│ │
│  │ (对话管理)   │  │ (数据查询)   │  │ (信号生成)   │  │ (数据质量)   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent 协调层 (Multi-Agent)                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │  ScreenerAgent   │  │  AnalyzerAgent   │  │  SignalAgent     │     │
│  │  (选股筛选)       │  │  (深度分析)       │  │  (信号生成)       │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│  ┌──────────────────┐  ┌──────────────────┐                           │
│  │  ValidatorAgent  │  │  RiskAgent       │                           │
│  │  (审核验证)       │  │  (风险管理)       │                           │
│  └──────────────────┘  └──────────────────┘                           │
└─────────────────────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           RAG 知识层 (Knowledge)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  向量数据库   │  │  财报数据库  │  │  舆情数据库  │  │ 时序数据库  │ │
│  │  (ChromaDB)  │  │  (PostgreSQL)│  │  (PostgreSQL)│  │ (Redis)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           数据源层 (Data Sources)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐│
│  │Tushare   │  │Baostock  │  │东方财富  │  │新闻API   │  │财报API   ││
│  │(实时)    │  │(历史)    │  │(财务)    │  │(舆情)    │  │(结构化)  ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术选型

| 层级 | 技术选择 | 说明 |
|------|----------|------|
| **前端** | React 18 + TypeScript + Tailwind | Terminal Elegance 设计风格 |
| **图表** | ECharts / Recharts | 专业的金融图表 |
| **后端** | FastAPI | 高性能异步 API |
| **LLM** | DeepSeek / OpenAI API | 商业 LLM，效果最佳 |
| **Agent框架** | LangGraph / LangChain | 多 Agent 协调 |
| **向量库** | ChromaDB | 轻量级，易于部署 |
| **关系库** | PostgreSQL | 财报、舆情结构化数据 |
| **缓存** | Redis | 实时数据缓存 |
| **消息队列** | Redis Pub/Sub | 实时信号推送 |

---

## 3. Agent 协调层设计

### 3.1 Agent 列表

| Agent | 职责 | 主要工具 | 输出 |
|-------|------|----------|------|
| **ScreenerAgent** | 选股筛选 | 板块过滤、基本面筛选、技术面筛选 | 股票列表 (top 50) |
| **AnalyzerAgent** | 深度分析 | 财报解析、舆情分析、估值计算 | 分析报告 (打分+理由) |
| **SignalAgent** | 信号生成 | 技术信号、仓位计算、风控检查 | 交易信号 (买卖+价位) |
| **ValidatorAgent** | 审核验证 | 数据时效、逻辑自检、风险评估 | 验证结果 (通过/拒绝) |
| **RiskAgent** | 风险管理 | 组合风险、权重优化、相关性检查 | 风险报告 + 仓位建议 |

### 3.2 Agent 协作流程

```
用户请求 → 意图识别 → Agent协调器 → 并行调用Agent → 结果聚合 → 返回用户
```

**典型场景分析:**
```
1. ScreenerAgent: 筛选AI板块 + ROE>15% → [科大讯飞, 寒武纪, ...]
2. AnalyzerAgent: 对每只股票进行财报/舆情/估值分析 → 打分
3. SignalAgent: 综合分析，生成买卖信号 → 买入科大讯飞@48.5
4. ValidatorAgent: 验证数据时效和逻辑合理性 → 通过
5. RiskAgent: 检查组合风险 → 建议仓位15%
```

---

## 4. 数据源设计

### 4.1 多数据源策略

| 数据类型 | 主数据源 | 备用数据源1 | 备用数据源2 |
|----------|----------|-------------|-------------|
| 实时行情 (分钟) | Tushare Pro | AKShare | 本地缓存 |
| 历史数据 (日) | Baostock | AKShare | 本地缓存 |
| 财报数据 | 东方财富 | 新浪财经 | 本地缓存 |
| 舆情数据 | 财联社API | 雪球API | 本地缓存 |

### 4.2 数据采集调度

| 任务 | 频率 | 时间窗口 | 数据源 |
|------|------|----------|--------|
| 实时行情采集 | 每分钟 | 9:30-15:00 | Tushare |
| 日终数据同步 | 每日2次 | 15:30 + 21:30 | Baostock/东方财富 |
| 舆情数据采集 | 每小时 | 全天 | 新闻API |
| 增量数据修复 | 每日1次 | 凌晨2:00 | 多源轮询 |

---

## 5. 前端界面设计

### 5.1 页面结构

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | 仪表板首页 | 实时监控、信号推送 |
| `/chat` | AI聊天助手 | 对话式选股分析 |
| `/backtest` | 回测分析 | 策略回测和对比 |
| `/data-monitor` | 数据质量监控 | 数据完整性检查和修复 |
| `/portfolio` | 投资组合 | 持仓分析和优化 |

### 5.2 聊天界面

**核心组件:**
- 消息列表 (用户消息 + AI回复)
- 信号卡片 (可执行的交易建议)
- 分析卡片 (可视化分析结果)
- 快捷操作按钮 (筛选条件)

**消息类型:**
1. 用户消息 - 纯文本输入
2. AI分析中 - 加载状态
3. 分析结果卡片 - 富文本展示
4. 交易信号卡片 - 带操作按钮

### 5.3 数据监控页面

**核心指标:**
- 整体数据概况 (股票数、完整率、问题数)
- 按市场分组的完整率
- 按数据类型的完整率
- 完整率分布图
- 问题股票列表
- 单股票详细数据视图
- 数据采集日志

---

## 6. API 设计

### 6.1 核心 API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/chat` | POST | 聊天对话接口 |
| `/api/chat/stream` | WebSocket | 流式对话 |
| `/api/stocks/screen` | POST | 股票筛选 |
| `/api/stocks/{code}/analyze` | GET | 股票分析 |
| `/api/signals/generate` | POST | 生成交易信号 |
| `/api/signals/realtime` | WebSocket | 实时信号推送 |
| `/api/data-quality/overview` | GET | 数据质量概览 |
| `/api/data-quality/stocks/{code}` | GET | 股票数据详情 |
| `/api/data-quality/repair` | POST | 数据修复 |
| `/api/backtest/run` | POST | 运行回测 |

### 6.2 数据质量 API

```python
GET  /api/data-quality/overview           # 整体概况
GET  /api/data-quality/by-market          # 按市场分组
GET  /api/data-quality/by-type            # 按数据类型
GET  /api/data-quality/distribution       # 完整率分布
GET  /api/data-quality/issues             # 问题列表
GET  /api/data-quality/stock/{code}/detail # 股票详情
POST /api/data-quality/stock/{code}/repair # 修复数据
POST /api/data-quality/batch-repair       # 批量修复
GET  /api/data-quality/logs               # 采集日志
GET  /api/data-quality/alerts             # 质量告警
```

---

## 7. 数据库设计

### 7.1 PostgreSQL 表结构

**stocks (股票基础)**
```sql
CREATE TABLE stocks (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    market VARCHAR(20) NOT NULL,  -- SH, SZ, HK, US
    sector VARCHAR(100),
    market_cap DECIMAL(20, 2),
    list_date DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**financial_statements (财报数据)**
```sql
CREATE TABLE financial_statements (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) REFERENCES stocks(code),
    report_date DATE NOT NULL,
    report_type VARCHAR(10),  -- Q1, Q2, Q3, annual
    revenue DECIMAL(20, 2),
    profit DECIMAL(20, 2),
    roe DECIMAL(10, 4),
    debt_ratio DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(stock_code, report_date, report_type)
);
```

**news_sentiment (舆情数据)**
```sql
CREATE TABLE news_sentiment (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) REFERENCES stocks(code),
    title VARCHAR(500),
    content TEXT,
    sentiment DECIMAL(5, 2),  -- -1 to 1
    keywords VARCHAR(200)[],
    publish_time TIMESTAMP,
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**data_quality_log (数据质量日志)**
```sql
CREATE TABLE data_quality_log (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20),
    data_type VARCHAR(50),
    check_date DATE DEFAULT CURRENT_DATE,
    total_expected INT,
    total_actual INT,
    completeness_rate DECIMAL(5, 2),
    missing_dates DATE[],
    status VARCHAR(20),  -- excellent, good, fair, poor
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 7.2 Redis 缓存结构

```
# 实时价格 (5分钟过期)
price:{code}:1m → {timestamp, open, high, low, close, volume}

# 技术指标 (1小时过期)
indicator:{code} → {MA5, MA20, MACD, RSI, ...}

# 最新信号 (1小时过期)
signal:{code} → {action, price, target, stop_loss, confidence}

# 板块热度 (30分钟过期)
sector:{sector_name}:heat → {score, rank, change}
```

---

## 8. 实施计划

### 8.1 分阶段实施

| 阶段 | 内容 | 交付物 | 预计时间 |
|------|------|--------|----------|
| **Phase 0** | 基础设施搭建 | 项目结构、基础框架 | 1周 |
| **Phase 1** | 数据层 | 多源数据采集、存储、质量监控 | 2周 |
| **Phase 2** | Agent层 | 5个Agent实现、RAG知识库 | 3周 |
| **Phase 3** | API层 | FastAPI服务、WebSocket推送 | 2周 |
| **Phase 4** | 前端层 | 聊天界面、仪表板、监控页面 | 3周 |
| **Phase 5** | 集成测试 | 端到端测试、性能优化 | 2周 |
| **Phase 6** | 部署上线 | 生产部署、监控告警 | 1周 |

### 8.2 技术债务与复用

**可复用组件:**
- `core/data/` - 数据层 (已有，需扩展港股/美股)
- `core/indicators/` - 技术指标 (完全复用)
- `core/strategies/` - 交易策略 (参考复用)
- `core/backtest/` - 回测引擎 (完全复用)

**需要新建:**
- `core/agents/` - Agent协调层
- `core/rag/` - RAG知识库
- `core/sentiment/` - 舆情分析
- `core/financial/` - 财报分析
- `backend/app/api/chat.py` - 聊天API
- `backend/app/services/agent_service.py` - Agent服务
- `frontend/src/pages/Chat.tsx` - 聊天页面
- `frontend/src/pages/DataMonitor.tsx` - 数据监控页面

---

## 9. 非功能性需求

### 9.1 性能要求

| 指标 | 目标 |
|------|------|
| API响应时间 | < 200ms (P95) |
| 聊天响应时间 | < 3秒 (流式) |
| 数据更新延迟 | < 1分钟 (实时) |
| 并发用户 | 100+ |

### 9.2 可用性要求

| 指标 | 目标 |
|------|------|
| 系统可用性 | 99.5% |
| 数据完整率 | > 95% |
| 信号准确率 | > 60% (胜率) |

### 9.3 安全要求

- API认证 (JWT Token)
- 敏感数据加密
- 访问日志记录
- 速率限制

---

## 10. 风险与挑战

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据源不稳定 | 高 | 多源备份、本地缓存 |
| LLM API成本 | 中 | 缓存、Prompt优化 |
| 实时性能 | 中 | Redis缓存、异步处理 |
| 港股/美股数据 | 中 | 分阶段接入 |

---

## 11. 附录

### 11.1 参考项目

| 项目 | Stars | 借鉴点 |
|------|-------|--------|
| daily_stock_analysis | 11,697 | LLM驱动、多数据源 |
| TradingAgents | 30,084 | 多Agent框架 |
| valuecell | 9,176 | 多智能体金融平台 |
| quantstats | 6,701 | 投资组合分析 |
| FinanceToolkit | 4,434 | 财务报表分析 |

### 11.2 术语表

| 术语 | 解释 |
|------|------|
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| Agent | 智能体，具有自主决策能力的AI组件 |
| 舆情分析 | 对新闻和社交媒体的情感分析 |
| 财报分析 | 对三大报表的财务分析 |
| 买卖点 | 具体的买入/卖出价格和时机建议 |

---

**文档版本**: v1.0
**最后更新**: 2026-02-17
**状态**: 待用户审核
