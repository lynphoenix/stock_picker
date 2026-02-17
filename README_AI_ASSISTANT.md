# 智能投研助手系统 (AI Investment Assistant)

> 基于多智能体协作的智能股票筛选、分析和交易信号生成系统

## 一句话描述

基于技术面、舆情面和财报面的多维度分析，通过多智能体协作，为投资者提供股票筛选、深度分析、交易信号生成和风险管理的智能投研助手系统。

## 项目概述

本系统是一个全栈Web应用，结合了：

- **多智能体系统**: 5个专业Agent协同工作
- **实时数据分析**: 支持A股、港股、美股
- **AI驱动分析**: 使用DeepSeek/OpenAI进行智能分析
- **风险管理**: 投资组合风险评估和优化
- **回测系统**: 验证交易策略有效性

## 技术栈

### 前端
- React 18 + TypeScript
- Tailwind CSS + Ant Design
- ECharts (可视化)
- Zustand (状态管理)
- Socket.io-client (WebSocket)

### 后端
- FastAPI (Python 3.10+)
- SQLAlchemy (ORM)
- PostgreSQL + Redis + ChromaDB
- WebSocket (asyncio)
- LangGraph / LangChain (Agent框架)

### 数据源
- Tushare Pro / AKShare (实时行情)
- Baostock (历史数据)
- 东方财富 / 新浪财经 (财报数据)
- 财联社 / 雪球 (舆情数据)

## 快速开始

### 前置要求

- Docker & Docker Compose
- Python 3.10+
- Node.js 18+
- API Keys (DeepSeek, Tushare)

### 1. 环境初始化

```bash
./init.sh
```

这将会：
- 创建 `.env` 配置文件
- 启动 Docker 服务 (PostgreSQL, Redis, ChromaDB)
- 检查依赖

### 2. 配置 API Keys

编辑 `.env` 文件，填入必要的API Keys：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
TUSHARE_TOKEN=your_tushare_token_here
```

### 3. 安装依赖

**后端：**
```bash
cd backend
pip install -r requirements.txt
```

**前端：**
```bash
cd frontend
npm install
```

### 4. 初始化数据库

```bash
cd backend
python scripts/init_db.py
```

### 5. 启动开发服务器

**启动后端：**
```bash
cd backend
uvicorn main:app --reload --port 8888
```

**启动前端：**
```bash
cd frontend
npm run dev
```

### 6. 访问应用

- 前端界面: http://localhost:3000
- 后端API: http://localhost:8888
- API文档: http://localhost:8888/docs
- 数据监控: http://localhost:8888/api/data-quality/overview

## 项目结构

```
stock_picker/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API端点
│   │   ├── agents/         # AI智能体
│   │   ├── core/           # 核心功能
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务服务
│   │   └── db/             # 数据库操作
│   ├── tests/              # 测试
│   └── scripts/            # 脚本
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面
│   │   ├── services/       # API服务
│   │   ├── store/          # 状态管理
│   │   └── types/          # TypeScript类型
│   └── e2e/                # E2E测试
├── docker/                 # Docker配置
├── docs/                   # 文档
├── scripts/                # 公共脚本
├── feature_list.json       # 功能清单（200+测试用例）
├── init.sh                 # 环境初始化脚本
└── docker-compose.yml      # Docker服务配置
```

## 核心功能

### P0 - 必须有（MVP）

#### 1. AI聊天助手
- 自然语言交互
- 多智能体协作
- 实时流式响应
- 会话持久化

#### 2. 多智能体系统
- **ScreenerAgent**: 股票筛选
- **AnalyzerAgent**: 深度分析
- **SignalAgent**: 交易信号
- **ValidatorAgent**: 信号验证
- **RiskAgent**: 风险评估

#### 3. 交易信号生成
- 买入/卖出/观望建议
- 目标价和止损价
- 仓位建议
- 风险提示

### P1 - 应该有

#### 4. 数据质量监控
- 数据完整性仪表板
- 自动数据修复
- 采集日志查询

#### 5. 多市场支持
- A股、港股、美股
- 汇率转换
- 市场识别

#### 6. 数据仪表板
- 实时行情
- 信号监控
- 持仓分析
- 板块热度

### P2 - 可以有

#### 7. 策略回测
- 历史数据验证
- 性能指标计算
- 交易历史分析

#### 8. 投资组合优化
- 现代投资组合理论
- 有效前沿
- 风险优化

## 页面导航

- `/` - 仪表板首页
- `/chat` - AI聊天助手
- `/signals` - 交易信号监控
- `/data-monitor` - 数据质量监控
- `/backtest` - 策略回测
- `/portfolio` - 投资组合
- `/settings` - 系统设置

## 测试

### 运行测试

**后端测试：**
```bash
cd backend
pytest
```

**前端测试：**
```bash
cd frontend
npm test
```

**E2E测试：**
```bash
cd frontend
npx playwright test
```

### 测试覆盖率

目标：≥ 70%

```bash
# 后端覆盖率
cd backend
pytest --cov=app --cov-report=html

# 前端覆盖率
cd frontend
npm run test:coverage
```

## API文档

访问 http://localhost:8888/docs 查看完整的Swagger/OpenAPI文档。

### 主要端点

#### 聊天相关
- `POST /api/chat` - 发送聊天消息
- `WebSocket /api/chat/stream` - 流式聊天

#### 信号相关
- `POST /api/signals/generate` - 生成交易信号
- `GET /api/signals/realtime` - 获取实时信号

#### 数据质量
- `GET /api/data-quality/overview` - 数据质量概览
- `POST /api/data-quality/stock/{code}/repair` - 修复数据

## Docker服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

## 开发规范

### 代码风格
- Python: PEP 8
- TypeScript: ESLint + Prettier
- Git: Conventional Commits

### 提交规范
```
feat: 新功能
fix: 修复bug
docs: 文档
test: 测试
refactor: 重构
```

### 分支策略
- `main` - 生产环境
- `develop` - 开发环境
- `feature/*` - 功能分支
- `hotfix/*` - 紧急修复

## 验收标准

- [x] 所有 P0 功能正常工作
- [ ] 5个Agent协同工作正常
- [ ] 用户流程端到端测试通过
- [ ] 符合 UI 设计规范
- [ ] 无控制台错误
- [ ] 测试覆盖率 ≥ 70%
- [ ] 数据质量监控功能正常

## 非功能性需求

### 性能
- 页面首屏加载 < 2秒
- API响应时间 < 500ms
- WebSocket延迟 < 100ms

### 安全
- JWT认证
- API密钥加密
- SQL注入防护
- XSS防护
- CORS配置

### 可用性
- 系统可用性 ≥ 99%
- 数据完整率 ≥ 95%
- Agent失败降级机制

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查Docker服务
   docker-compose ps
   # 重启PostgreSQL
   docker-compose restart postgres
   ```

2. **Redis连接失败**
   ```bash
   # 重启Redis
   docker-compose restart redis
   ```

3. **API超时**
   - 检查网络连接
   - 验证API Keys
   - 查看后端日志

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

本项目采用 MIT 许可证。

## 更新日志

### v1.0.0 (2026-02-17)
- 初始版本发布
- 完成P0功能
- 实现5个Agent系统
- 数据质量监控
- 多市场支持

---

**生成时间**: 2026-02-17
**版本**: v1.0
