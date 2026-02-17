# 股票回测系统后端

基于FastAPI的股票策略回测后端服务

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动开发服务器

```bash
# 方式1: 直接运行
python -m backend.app.main

# 方式2: 使用uvicorn
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API概览

### 策略管理 `/api/strategies`

- `GET /api/strategies` - 获取所有策略列表
- `GET /api/strategies/{id}` - 获取策略详情
- `POST /api/strategies` - 创建新策略
- `PUT /api/strategies/{id}` - 更新策略
- `DELETE /api/strategies/{id}` - 删除策略

### 回测 `/api/backtest`

- `POST /api/backtest/quick` - 快速回测
- `POST /api/backtest/full` - 完整回测
- `GET /api/backtest/status/{task_id}` - 获取回测进度
- `GET /api/backtest/result/{task_id}` - 获取回测结果

### 数据管理 `/api/data`

- `GET /api/data/overview` - 数据总览
- `GET /api/data/stocks` - 股票数据列表
- `GET /api/data/stocks/{code}` - 股票详情
- `POST /api/data/repair` - 补充数据
- `GET /api/data/fetch-schedule` - 获取采集调度配置
- `POST /api/data/fetch-now` - 立即采集数据

### 报表 `/api/reports`

- `GET /api/reports/{task_id}/excel` - 导出Excel
- `GET /api/reports/{task_id}/pdf` - 导出PDF

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI入口
│   ├── api/                 # API路由
│   │   ├── strategies.py
│   │   ├── backtest.py
│   │   ├── data.py
│   │   └── reports.py
│   ├── services/            # 业务逻辑
│   │   ├── strategy_service.py
│   │   ├── backtest_service.py
│   │   ├── data_service.py
│   │   └── report_service.py
│   └── models/              # 数据模型
│       ├── strategy.py
│       ├── backtest.py
│       └── data.py
└── requirements.txt
```

## 开发说明

### 添加新API

1. 在 `models/` 中定义数据模型
2. 在 `services/` 中实现业务逻辑
3. 在 `api/` 中添加路由
4. 在 `main.py` 中注册路由

### 测试API

```bash
# 健康检查
curl http://localhost:8000/health

# 获取策略列表
curl http://localhost:8000/api/strategies

# 快速回测
curl -X POST http://localhost:8000/api/backtest/quick \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "enhanced_multi_factor", "market": "sh_star", "year": "2026"}'
```

## 部署

见项目根目录的 `docker/` 配置
