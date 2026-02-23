# Stock Monitor 项目技术分析文档

## 1. 项目概述

**项目名称**: YFinance Alert Manager (Stock Monitor)
**GitHub**: https://github.com/marketcalls/YFinance-Alert-Manager
**许可证**: MIT

Stock Monitor 是一个**实时股票价格监控和告警系统**。

---

## 2. 项目结构

```
stock-monitor/
├── app.py               # Flask主应用
├── requirements.txt     # 依赖
├── templates/
│   └── index.html      # 前端界面
└── static/
```

---

## 3. 核心功能

### 3.1 实时监控
- 多只股票同时监控
- Yahoo Finance WebSocket实时价格

### 3.2 告警系统
- **条件**: 价格高于/低于/等于目标价
- **自动暂停**: 触发后防止重复
- **历史记录**: SQLite持久化

### 3.3 UI界面
- 三栏布局 (订阅/价格/告警)
- 深色/浅色主题

---

## 4. 技术架构

### 4.1 技术栈

| 技术 | 用途 |
|------|------|
| Flask | Web框架 |
| Flask-SocketIO | WebSocket |
| Flask-SQLAlchemy | ORM |
| yfinance | 数据源 |
| SQLite | 数据库 |
| DaisyUI | 前端组件 |

### 4.2 架构模式
- **WebSocket**: 实时价格推送
- **事件驱动**: 订阅/告警/触发

---

## 5. 技术特点

| 特点 | 说明 |
|------|------|
| 实时性 | WebSocket毫秒级更新 |
| 响应式 | 支持桌面/移动端 |
| 持久化 | SQLite存储 |
| 单文件后端 | 便于部署 |

---

*文档生成时间: 2026-02-22*
