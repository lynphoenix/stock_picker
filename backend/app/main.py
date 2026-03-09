# -*- coding: utf-8 -*-
"""
FastAPI 主应用
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print("✓ Loaded .env configuration")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys

# 添加项目根目录到路径
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.api import strategies, backtest, data, reports, monitoring, chat
from backend.app.api.agents import router as agents_router
from backend.scheduler import DataScheduler

# 全局调度器实例
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global scheduler

    # 启动时
    scheduler = DataScheduler()
    scheduler.schedule_daily_fetch(hour=21, minute=30)
    scheduler.start()
    print("✅ 数据采集调度器已启动")

    yield

    # 关闭时
    if scheduler:
        scheduler.stop()
        print("⏹️  数据采集调度器已停止")


# 创建FastAPI应用
app = FastAPI(
    title="股票回测系统 API",
    description="策略管理、回测、数据监控API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS（允许前端访问）
# 从环境变量读取允许的源，如果未设置则使用开发环境默认值
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(strategies.router, prefix="/api/strategies", tags=["策略管理"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["回测"])
app.include_router(data.router, prefix="/api/data", tags=["数据管理"])
app.include_router(reports.router, prefix="/api/reports", tags=["报表"])
app.include_router(monitoring.router, prefix="/api", tags=["监控系统"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI聊天"])
app.include_router(agents_router, prefix="/api/agents", tags=["AI Agents"])


@app.get("/")
async def root():
    return {
        "message": "股票回测系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/scheduler/status")
async def get_scheduler_status():
    if scheduler:
        return scheduler.get_status()
    return {"error": "调度器未启动"}


@app.post("/scheduler/trigger")
async def trigger_scheduler():
    if scheduler:
        import threading
        thread = threading.Thread(target=scheduler.trigger_now)
        thread.start()
        return {"message": "采集任务已触发，正在后台执行"}
    return {"error": "调度器未启动"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
