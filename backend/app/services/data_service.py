# -*- coding: utf-8 -*-
"""
数据服务层
"""
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import sys

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.models.data import (
    DataOverview,
    StockDataList,
    StockDataItem,
    StockDetail,
    DataRepairConfig,
    RepairTaskResponse,
    FetchScheduleConfig,
    FetchScheduleStatus
)
from core.data.data_monitor import DataMonitor


class DataService:
    """数据服务"""

    def __init__(self):
        self.monitor = DataMonitor()
        self.config_file = Path(root_dir) / "data" / "fetch_schedule.json"
        self.tasks_dir = Path(root_dir) / "data" / "repair_tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.running_tasks = {}
        # 采集任务相关
        self.fetch_tasks = {}
        self.current_fetch_task_id = None
        self.fetch_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "last_run": None,
            "errors": []
        }
        # 导入AutoDataFetcher
        from core.data.auto_fetcher import AutoDataFetcher
        self.fetcher = AutoDataFetcher()

    # ============================================================
    # 1. 数据总览
    # ============================================================

    def get_overview(self) -> DataOverview:
        """获取数据总览"""
        overview = self.monitor.get_overview()
        return DataOverview(**overview)

    # ============================================================
    # 2. 股票数据列表
    # ============================================================

    def get_stocks_list(
        self,
        market: str = "all",
        sort_by: str = "completeness",
        only_missing: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> StockDataList:
        """获取股票数据列表"""
        data = self.monitor.get_stocks_list(
            market=market,
            sort_by=sort_by,
            only_missing=only_missing,
            page=page,
            page_size=page_size
        )

        stocks = [StockDataItem(**item) for item in data["stocks"]]

        return StockDataList(
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
            stocks=stocks
        )

    # ============================================================
    # 3. 股票详情
    # ============================================================

    def get_stock_detail(self, code: str) -> Optional[StockDetail]:
        """获取股票详情"""
        detail = self.monitor.get_stock_detail(code)
        if not detail:
            return None

        return StockDetail(**detail)

    # ============================================================
    # 4. 数据补充
    # ============================================================

    def create_repair_task(self, config: DataRepairConfig) -> str:
        """创建数据补充任务"""
        task_id = str(uuid.uuid4())

        self.running_tasks[task_id] = {
            "status": "pending",
            "progress": 0,
            "total": 0,
            "completed": 0,
            "current": "",
            "config": config.dict(),
            "created_at": datetime.now().isoformat()
        }

        self._save_repair_status(task_id)

        return task_id

    async def run_repair_task(self, task_id: str, config: DataRepairConfig):
        """执行数据补充任务（后台）"""
        try:
            self._update_repair_status(task_id, "running", 0, 0, 0, "初始化...")

            # 1. 确定需要补充的股票列表
            if config.mode == "auto":
                # 自动检测缺失
                codes = self._detect_missing_stocks()
            else:
                # 手动指定
                codes = config.codes or []

            total = len(codes)
            self._update_repair_status(task_id, "running", 5, total, 0, f"准备补充{total}只股票...")

            # 2. 批量补充数据
            for i, code in enumerate(codes):
                self._update_repair_status(
                    task_id, "running",
                    10 + int(i / total * 85),
                    total, i,
                    f"{code} 补充中..."
                )

                # TODO: 实际调用数据采集
                # await self._repair_stock_data(code, config)

                # 模拟延迟
                import asyncio
                await asyncio.sleep(0.1)

            # 3. 完成
            self._update_repair_status(task_id, "completed", 100, total, total, "完成")

        except Exception as e:
            self._update_repair_status(task_id, "failed", 0, 0, 0, str(e))

    def get_repair_status(self, task_id: str) -> Optional[RepairTaskResponse]:
        """获取补充任务状态"""
        if task_id in self.running_tasks:
            status = self.running_tasks[task_id]
            return RepairTaskResponse(**{
                "task_id": task_id,
                "status": status["status"],
                "progress": status.get("progress"),
                "total": status.get("total"),
                "completed": status.get("completed"),
                "current": status.get("current")
            })

        # 从文件加载
        status_file = self.tasks_dir / f"{task_id}_status.json"
        if status_file.exists():
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
                return RepairTaskResponse(**{
                    "task_id": task_id,
                    "status": status["status"],
                    "progress": status.get("progress"),
                    "total": status.get("total"),
                    "completed": status.get("completed"),
                    "current": status.get("current")
                })

        return None

    def _update_repair_status(self, task_id, status, progress, total, completed, current):
        """更新补充任务状态"""
        if task_id not in self.running_tasks:
            self.running_tasks[task_id] = {}

        self.running_tasks[task_id].update({
            "status": status,
            "progress": progress,
            "total": total,
            "completed": completed,
            "current": current,
            "updated_at": datetime.now().isoformat()
        })

        self._save_repair_status(task_id)

    def _save_repair_status(self, task_id):
        """保存补充任务状态"""
        status_file = self.tasks_dir / f"{task_id}_status.json"
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(self.running_tasks[task_id], f, ensure_ascii=False, indent=2)

    def _detect_missing_stocks(self) -> list:
        """自动检测需要补充的股票"""
        # TODO: 实现实际检测逻辑
        return []

    # ============================================================
    # 5. 采集调度配置
    # ============================================================

    def get_fetch_schedule(self) -> FetchScheduleStatus:
        """获取采集调度配置"""
        config = self._load_fetch_config()

        return FetchScheduleStatus(
            config=FetchScheduleConfig(**config),
            last_run={
                "date": "2026-01-29",
                "status": "success",
                "duration": 125.3
            },
            next_run="2026-01-30 21:30:00"
        )

    def update_fetch_schedule(self, config: FetchScheduleConfig) -> FetchScheduleConfig:
        """更新采集调度配置"""
        self._save_fetch_config(config.dict())
        return config

    def create_fetch_task(self) -> str:
        """创建立即采集任务"""
        task_id = str(uuid.uuid4())
        self.current_fetch_task_id = task_id

        self.fetch_tasks[task_id] = {
            "status": "running",
            "progress": 0,
            "started_at": datetime.now().isoformat(),
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        return task_id

    async def run_fetch_task(self, task_id: str):
        """执行立即采集任务"""
        try:
            if task_id not in self.fetch_tasks:
                return

            # 更新状态
            self.fetch_tasks[task_id]["status"] = "running"

            # 执行采集（使用同步版本）
            result = self.fetcher.fetch_daily_data_sync(
                stock_pool="all",
                max_concurrent=10,
                retry_times=3
            )

            # 更新结果
            self.fetch_tasks[task_id].update({
                "status": result.get("status", "completed"),
                "progress": 100,
                "total": result.get("total", 0),
                "success": result.get("success", 0),
                "failed": result.get("failed", 0),
                "skipped": result.get("skipped", 0),
                "errors": result.get("errors", []),
                "ended_at": datetime.now().isoformat()
            })

            # 更新全局统计
            self.fetch_stats["total"] = result.get("total", 0)
            self.fetch_stats["success"] = result.get("success", 0)
            self.fetch_stats["failed"] = result.get("failed", 0)
            self.fetch_stats["skipped"] = result.get("skipped", 0)
            self.fetch_stats["last_run"] = datetime.now().isoformat()
            self.fetch_stats["errors"] = result.get("errors", [])[-10:]
            self.fetch_stats["current_status"] = result.get("status", "completed")

        except Exception as e:
            self.fetch_tasks[task_id].update({
                "status": "failed",
                "error": str(e),
                "ended_at": datetime.now().isoformat()
            })

    def get_fetch_status(self, task_id: str) -> Optional[dict]:
        """获取采集任务状态"""
        if task_id in self.fetch_tasks:
            return self.fetch_tasks[task_id]
        return None

    def get_fetch_stats(self) -> dict:
        """获取采集统计 - 优化：直接返回缓存的统计信息"""
        # 直接返回缓存的统计信息，避免不必要的调用
        return {
            "total": self.fetch_stats.get("total", 0),
            "success": self.fetch_stats.get("success", 0),
            "failed": self.fetch_stats.get("failed", 0),
            "skipped": self.fetch_stats.get("skipped", 0),
            "last_run": self.fetch_stats.get("last_run"),
            "errors": self.fetch_stats.get("errors", []),
            "current_status": self.fetch_stats.get("current_status", "idle")
        }

    def stop_fetch(self) -> dict:
        """停止采集"""
        self.fetcher.stop()
        if self.current_fetch_task_id and self.current_fetch_task_id in self.fetch_tasks:
            self.fetch_tasks[self.current_fetch_task_id]["status"] = "stopped"
            self.fetch_tasks[self.current_fetch_task_id]["ended_at"] = datetime.now().isoformat()
        return {"status": "stopped", "message": "采集已停止"}

    def _load_fetch_config(self) -> Dict:
        """加载采集配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 默认配置
        return {
            "enabled": True,
            "schedule_time": "21:30",
            "retry_times": 3,
            "retry_interval": 10,
            "content": ["daily", "basic_info", "indicators"]
        }

    def _save_fetch_config(self, config: Dict):
        """保存采集配置"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
