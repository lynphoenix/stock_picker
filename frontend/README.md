# 量化回测终端 - Frontend

## 🚀 启动项目

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问: http://localhost:3000

### 构建生产版本

```bash
npm run build
```

## 📐 项目结构

```
frontend/
├── src/
│   ├── components/      # 公共组件
│   │   └── Layout.tsx   # 应用布局
│   ├── pages/           # 页面组件
│   │   ├── StrategyWorkspace.tsx  # 策略回测工作台
│   │   └── DataMonitoring.tsx     # 数据监控中心
│   ├── services/        # API服务
│   │   └── api.ts       # API封装
│   ├── App.tsx          # 应用入口
│   ├── main.tsx         # React入口
│   └── index.css        # 全局样式
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 🎨 设计理念

**Terminal Elegance** - 专业交易终端与现代数据科学的完美融合

### 特色功能

1. **策略回测工作台**
   - 对话式策略选择
   - 快速回测验证（30秒）
   - 实时结果展示
   - 专业级数据可视化

2. **数据监控中心**
   - 5329只股票实时监控
   - 95%数据完整率展示
   - 指标状态可视化
   - 股票列表详情查询

### 视觉特点

- 🌌 深色主题，电子蓝强调色
- 📊 玻璃态卡片，流畅动画
- 🔤 Playfair Display (标题) + JetBrains Mono (数据) + Inter (正文)
- ✨ 微交互与状态反馈
- 📱 完全响应式设计

## 🔌 API连接

前端通过Vite代理连接后端API:

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://100.100.152.204:8888',
    changeOrigin: true,
  }
}
```

## 📦 主要依赖

- **React 18** - UI框架
- **Ant Design 5** - 组件库
- **ECharts** - 数据可视化
- **Axios** - HTTP客户端
- **React Router** - 路由管理
- **TypeScript** - 类型安全
- **Vite** - 构建工具

## 🎯 下一步开发

- [ ] 完整回测报表（年度对比、资金曲线、回撤曲线）
- [ ] 交易明细表格
- [ ] 策略对比功能
- [ ] 数据修复功能
- [ ] WebSocket实时数据推送
- [ ] 导出报告（Excel/PDF）
