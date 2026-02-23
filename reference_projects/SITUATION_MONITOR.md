# Situation Monitor 项目技术分析文档

## 1. 项目概述

**项目名称**: Situation Monitor
**GitHub**: https://github.com/hipcityreg/situation-monitor
**主要语言**: TypeScript (Svelte 5)
**许可证**: MIT

Situation Monitor 是一个**实时全球新闻与市场监控平台**，追踪地缘政治事件、市场动态和情报信息。

---

## 2. 项目结构

```
situation-monitor/
├── src/
│   ├── lib/
│   │   ├── analysis/       # 智能分析引擎
│   │   ├── api/           # 外部数据获取
│   │   ├── components/     # UI组件
│   │   ├── config/         # 配置管理
│   │   ├── services/       # 弹性服务层
│   │   ├── stores/         # Svelte状态管理
│   │   ├── types/          # 类型定义
│   │   └── utils/          # 工具函数
│   └── routes/             # SvelteKit路由
├── tests/                   # Playwright测试
└── package.json
```

---

## 3. 核心功能模块

### 3.1 数据获取
| 数据源 | 功能 |
|--------|------|
| GDELT API | 全球新闻事件 |
| RSS Feeds | 30+ 新闻源 |
| CoinGecko | 加密货币数据 |
| FRED API | 美联储经济数据 |
| 自定义情报源 | CSIS、Brookings等智库 |

### 3.2 智能分析
- **Correlation Engine**: 跨新闻项模式关联
- **Narrative Tracker**: 叙事追踪
- **Main Character Detection**: 实体显著性分析

### 3.3 监控告警
- 自定义关键词监控
- 新闻匹配和告警
- 区域/主题检测

---

## 4. 技术架构

### 4.1 弹性服务层

**三大核心组件**:

| 组件 | 功能 |
|------|------|
| **CacheManager** | 两级缓存 (L1内存 + L2 localStorage) |
| **CircuitBreaker** | 断路器 (CLOSED/HALF_OPEN/OPEN) |
| **RequestDeduplicator** | 请求去重 |

**架构流程**:
```
请求 → [缓存] → [断路器] → [去重] → [执行] → [重试] → [缓存]
```

### 4.2 多阶段刷新

| 阶段 | 类别 | 延迟 |
|------|------|------|
| Critical | news, markets, alerts | 0ms |
| Secondary | crypto, commodities | 2s |
| Tertiary | contracts, whales | 4s |

### 4.3 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | SvelteKit 2.0 + Svelte 5 |
| 语言 | TypeScript (strict) |
| 样式 | Tailwind CSS |
| 测试 | Vitest + Playwright |
| 可视化 | D3.js + TopoJSON |
| 部署 | GitHub Pages |

---

## 5. 监控机制

### 5.1 实时刷新
- 自动刷新: 默认1小时间隔
- 手动刷新: 用户触发全量刷新
- 分阶段加载: 避免UI阻塞

### 5.2 错误处理
- 断路器: 故障时返回缓存
- 重试: 指数退避 (1s, 2s, 4s + 抖动)
- 降级: 过期缓存兜底

### 5.3 健康监控
- 熔断状态可视化
- 缓存命中率统计
- 请求去重计数

---

## 6. 技术特点

| 特点 | 说明 |
|------|------|
| **可靠性优先** | 断路器 + 多级缓存 + 去重 |
| **配置驱动** | 业务规则外部化 |
| **渐进加载** | 三阶段刷新优化首屏 |
| **智能分析** | 关联检测、叙事追踪 |
| **TypeScript** | 严格类型安全 |
| **静态部署** | 无服务器端 |

---

## 7. 可借鉴的设计

1. **断路器模式** - 故障自动隔离
2. **两级缓存** - 内存 + localStorage
3. **多阶段刷新** - 关键数据优先
4. **配置驱动** - 业务规则外部化

---

*文档生成时间: 2026-02-22*
