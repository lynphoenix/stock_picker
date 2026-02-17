# -*- coding: utf-8 -*-
"""
FastAPI 主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# 添加项目根目录到路径
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.api import strategies, backtest, data, reports, monitoring
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(strategies.router, prefix="/api/strategies", tags=["策略管理"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["回测"])
app.include_router(data.router, prefix="/api/data", tags=["数据管理"])
app.include_router(reports.router, prefix="/api/reports", tags=["报表"])
app.include_router(monitoring.router, prefix="/api", tags=["监控系统"])  # Phase 3监控


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "股票回测系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.get("/scheduler/status")
async def get_scheduler_status():
    """获取调度器状态"""
    if scheduler:
        return scheduler.get_status()
    return {"error": "调度器未启动"}


@app.post("/scheduler/trigger")
async def trigger_scheduler():
    """手动触发一次数据采集"""
    if scheduler:
        import threading
        thread = threading.Thread(target=scheduler.trigger_now)
        thread.start()
        return {"message": "采集任务已触发，正在后台执行"}
    return {"error": "调度器未启动"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
