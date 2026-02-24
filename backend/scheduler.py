# -*- coding: utf-8 -*-
"""
定时任务调度器 - 每天21:30自动采集数据
"""
import sys
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import chinese_calendar

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from core.data.auto_fetcher import AutoDataFetcher


class DataScheduler:
    """数据采集调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.fetcher = AutoDataFetcher()
        self.last_result = None

    def schedule_daily_fetch(
        self,
        hour: int = 21,
        minute: int = 30,
        timezone: str = "Asia/Shanghai"
    ):
        """
        配置每日定时采集

        Args:
            hour: 小时 (0-23)
            minute: 分钟 (0-59)
            timezone: 时区
        """
        # 创建cron触发器 - 每天指定时间
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=timezone
        )

        # 添加任务
        self.scheduler.add_job(
            func=self._fetch_job,
            trigger=trigger,
            id="daily_data_fetch",
            name="每日数据采集",
            replace_existing=True
        )

        print(f"✅ 已配置定时采集: 每天 {hour:02d}:{minute:02d} (北京时间)")

    def _fetch_job(self):
        """定时任务执行函数"""
        print(f"\n{'='*60}")
        print(f"🚀 触发定时采集 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # 检查是否交易日
        if not self.fetcher.should_fetch_today():
            print("⏸️  今日非交易日，跳过采集")
            return

        # 执行采集（使用同步版本）
        try:
            result = self.fetcher.fetch_daily_data_sync(
                retry_times=3
            )

            self.last_result = result

            print(f"\n✅ 采集成功完成!")
            print(f"  - 总数: {result['total']}")
            print(f"  - 成功: {result['success']}")
            print(f"  - 失败: {result['failed']}")
            print(f"  - 耗时: {result['duration']}秒")

        except Exception as e:
            print(f"\n❌ 采集失败: {e}")
            import traceback
            traceback.print_exc()

    def start(self):
        """启动调度器"""
        self.scheduler.start()
        print("📅 调度器已启动")

        # 显示所有任务
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            try:
                next_run = job.next_run_time
                print(f"  - {job.name}: {next_run}")
            except Exception:
                print(f"  - {job.name}")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        print("⏹️  调度器已停止")

    def get_status(self) -> dict:
        """获取调度器状态"""
        jobs = self.scheduler.get_jobs()

        job_list = []
        for job in jobs:
            try:
                next_run = job.next_run_time.isoformat() if job.next_run_time else None
            except Exception:
                next_run = None
            job_list.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run
            })

        return {
            "running": self.scheduler.running,
            "jobs": job_list,
            "last_result": self.last_result
        }

    def trigger_now(self):
        """立即触发一次采集"""
        print("🔄 手动触发采集...")
        self._fetch_job()


def main():
    """主函数 - 独立运行调度器"""
    print("╔════════════════════════════════════════╗")
    print("║      数据采集调度器                     ║")
    print("╚════════════════════════════════════════╝")

    scheduler = DataScheduler()

    # 配置每天21:30采集
    scheduler.schedule_daily_fetch(hour=21, minute=30)

    # 启动
    scheduler.start()

    try:
        # 保持运行
        print("\n按 Ctrl+C 停止调度器...\n")
        while True:
            import time
            time.sleep(60)

    except (KeyboardInterrupt, SystemExit):
        print("\n\n⚠️  收到停止信号")
        scheduler.stop()
        print("✅ 调度器已安全停止")


if __name__ == "__main__":
    main()
