# -*- coding: utf-8 -*-
"""
数据下载进度监控和定时汇报程序
功能：
1. 监控下载进度（读取缓存文件变化）
2. 定时输出进度报告
3. 预估剩余时间
4. 检测下载卡死情况
"""

import sys
from pathlib import Path
import pickle
import time
from datetime import datetime, timedelta
from collections import defaultdict
import json

sys.path.append(str(Path(__file__).parent.parent))

from settings import CACHE_DIR


class DownloadMonitor:
    """下载进度监控器"""

    def __init__(self, report_interval_minutes: int = 30):
        """
        Args:
            report_interval_minutes: 汇报间隔（分钟）
        """
        self.cache_dir = CACHE_DIR
        self.report_interval = timedelta(minutes=report_interval_minutes)
        self.last_report_time = None

        # 记录初始状态
        self.initial_files = set()
        self.initial_stats = {}

        # 目标配置（根据实际需要修改）
        self.target_years = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        self.target_stock_count = 5370  # 预期股票数量

    def scan_cache_files(self):
        """扫描缓存文件，统计进度"""
        import subprocess
        import re

        # 使用find命令获取所有pkl文件
        all_files = subprocess.check_output(
            f"find {self.cache_dir} -name '*.pkl' 2>/dev/null",
            shell=True
        ).decode().strip().split('\n')

        total_files = len([f for f in all_files if f])

        stats = {
            'total_files': total_files,
            'by_year': defaultdict(int),
            'by_stock': defaultdict(int),
            'total_records': 0,
            'empty_files': 0,
            'corrupted_files': 0
        }

        # 按年份统计有数据的股票（去重）
        year_pattern = re.compile(r'stock_hist_([^_]+)_(\d{8})_(\d{8})')

        for f in all_files:
            if not f:
                continue

            # 解析文件名: stock_hist_CODE_START_END_qfq.pkl
            match = year_pattern.search(f)
            if match:
                code = match.group(1)
                start_date = match.group(2)
                end_date = match.group(3)

                start_year = int(start_date[:4])
                end_year = int(end_date[:4])

                # 标记该股票在这些年份有数据（使用set去重）
                for year in range(start_year, end_year + 1):
                    if year in self.target_years:
                        # 使用frozenset确保每只股票每年只计数一次
                        stats['by_year'][str(year)] = len(set([code]))  # 这里逻辑需要改

        # 正确的按年份统计：先收集所有(stock_code, year)对，再去重计数
        year_stocks = {str(year): set() for year in self.target_years}

        for f in all_files:
            if not f:
                continue

            match = year_pattern.search(f)
            if match:
                code = match.group(1)
                start_date = match.group(2)
                end_date = match.group(3)

                start_year = int(start_date[:4])
                end_year = int(end_date[:4])

                for year in range(start_year, end_year + 1):
                    if year in self.target_years:
                        year_stocks[str(year)].add(code)

        # 更新统计结果
        for year in self.target_years:
            stats['by_year'][str(year)] = len(year_stocks[str(year)])

        # 随机抽样检查文件质量
        sample_size = min(100, total_files)
        if sample_size > 0:
            import random
            sample_files = random.sample(all_files, sample_size)

            for f in sample_files:
                if not f:
                    continue
                try:
                    with open(f.strip(), 'rb') as file:
                        df = pickle.load(file)
                        if df is None or len(df) == 0:
                            stats['empty_files'] += 1
                        else:
                            stats['total_records'] += len(df)
                except:
                    stats['corrupted_files'] += 1

        return stats

    def calculate_progress(self, current_stats):
        """计算进度百分比"""
        total_targets = self.target_stock_count * len(self.target_years)
        completed = current_stats['total_files']

        return {
            'percent': completed / total_targets * 100 if total_targets > 0 else 0,
            'completed': completed,
            'total': total_targets,
            'remaining': total_targets - completed
        }

    def estimate_time_remaining(self, progress):
        """预估剩余时间"""
        if self.last_report_time and 'initial_remaining' in self.initial_stats:
            elapsed = datetime.now() - self.last_report_time
            remaining_decrease = self.initial_stats['initial_remaining'] - progress['remaining']

            if remaining_decrease > 0:
                rate = remaining_decrease / elapsed.total_seconds()  # 每秒完成数
                remaining_seconds = progress['remaining'] / rate if rate > 0 else 0
                return timedelta(seconds=remaining_seconds)

        return None

    def generate_report(self, current_stats, progress, time_remaining):
        """生成进度报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'progress': progress,
            'by_year': dict(current_stats['by_year']),
            'time_remaining': str(time_remaining) if time_remaining else "未知",
            'quality': {
                'empty_files': current_stats['empty_files'],
                'corrupted_files': current_stats['corrupted_files'],
                'total_records': current_stats['total_records']
            }
        }
        return report

    def print_report(self, report):
        """打印报告到控制台"""
        report_text = f"""
{'='*80}
数据下载进度报告 - {report['timestamp'][:19]}
{'='*80}

[总体进度]
  已完成: {report['progress']['completed']}/{report['progress']['total']} ({report['progress']['percent']:.1f}%)
  剩余: {report['progress']['remaining']} 个文件
  预计剩余时间: {report['time_remaining']}

[按年份统计]
"""
        by_year = report['by_year']
        for year in sorted(self.target_years):
            count = by_year.get(str(year), 0)
            pct = count / self.target_stock_count * 100
            bar = '█' * int(pct / 2) + '░' * (50 - int(pct / 2))
            report_text += f"  {year}: {count:4d}/{self.target_stock_count} ({pct:5.1f}%) [{bar}]\n"

        quality = report['quality']
        report_text += f"""
[数据质量]
  总记录数: {quality['total_records']:,}
  空文件: {quality['empty_files']}
  损坏文件: {quality['corrupted_files']}

{'='*80}
"""
        # 强制刷新输出
        print(report_text, flush=True)

    def save_report(self, report):
        """保存报告到文件"""
        report_file = CACHE_DIR / "download_progress_report.json"

        # 读取历史报告
        history = []
        if report_file.exists():
            try:
                with open(report_file, 'r') as f:
                    history = json.load(f)
            except:
                pass

        # 添加新报告
        history.append(report)

        # 只保留最近100条
        history = history[-100:]

        with open(report_file, 'w') as f:
            json.dump(history, f, indent=2)

    def run_once(self):
        """执行一次监控检查"""
        current_stats = self.scan_cache_files()
        progress = self.calculate_progress(current_stats)
        time_remaining = self.estimate_time_remaining(progress)

        report = self.generate_report(current_stats, progress, time_remaining)

        # 打印报告
        self.print_report(report)

        # 保存报告
        self.save_report(report)

        # 更新状态
        if self.last_report_time is None:
            self.initial_stats = {
                'initial_remaining': progress['remaining'],
                'initial_time': datetime.now()
            }

        self.last_report_time = datetime.now()

        return report

    def run_continuous(self, max_hours: int = 24):
        """
        持续监控模式

        Args:
            max_hours: 最大运行小时数
        """
        # 设置无缓冲输出
        import sys
        sys.stdout.reconfigure(line_buffering=True)

        print(f"{'='*80}", flush=True)
        print(f"启动下载进度监控 (汇报间隔: {self.report_interval.total_seconds()/60:.0f}分钟)", flush=True)
        print(f"{'='*80}\n", flush=True)

        end_time = datetime.now() + timedelta(hours=max_hours)

        # 初始报告（立即执行）
        self.run_once()

        while datetime.now() < end_time:
            # 等待到下次汇报时间
            time.sleep(self.report_interval.total_seconds())

            # 生成报告
            report = self.run_once()

            # 检查是否完成
            prog = report['progress']
            if prog['percent'] >= 99.9:
                print(f"\n下载已完成！停止监控。", flush=True)
                break

    def check_stalled(self):
        """检查下载是否卡死"""
        current_stats = self.scan_cache_files()

        # 检查文件数量是否变化
        if self.initial_files:
            new_files = current_stats['total_files'] - len(self.initial_files)

            if new_files == 0:
                print(f"\n⚠ 警告: 检测到下载可能卡死（文件数量未变化）")
                print(f"  建议检查下载进程状态")

        self.initial_files = set(f.name for f in self.cache_dir.glob("stock_hist_*_qfq.pkl"))

        return current_stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据下载进度监控")
    parser.add_argument("--interval", type=int, default=30, help="汇报间隔（分钟）")
    parser.add_argument("--once", action="store_true", help="只运行一次")
    parser.add_argument("--max-hours", type=int, default=24, help="最大运行小时数")

    args = parser.parse_args()

    monitor = DownloadMonitor(report_interval_minutes=args.interval)

    if args.once:
        monitor.run_once()
    else:
        monitor.run_continuous(max_hours=args.max_hours)


if __name__ == "__main__":
    main()
