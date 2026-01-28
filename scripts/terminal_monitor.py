# -*- coding: utf-8 -*-
"""
终端实时监控 - 直接在屏幕显示进度报告
"""

import sys
from pathlib import Path
import time
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import pickle

sys.path.append(str(Path(__file__).parent.parent))

from settings import CACHE_DIR


def scan_progress():
    """扫描当前进度"""
    import re

    all_files = subprocess.check_output(
        f"find {CACHE_DIR} -name '*.pkl' 2>/dev/null",
        shell=True
    ).decode().strip().split('\n')

    total_files = len([f for f in all_files if f])

    # 按年份统计有数据的股票
    target_years = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    year_pattern = re.compile(r'stock_hist_([^_]+)_(\d{8})_(\d{8})')
    year_stocks = {str(year): set() for year in target_years}

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
                if year in target_years:
                    year_stocks[str(year)].add(code)

    return {
        'total_files': total_files,
        'by_year': {year: len(year_stocks[year]) for year in year_stocks}
    }


def clear_screen():
    """清屏"""
    print("\033[2J\033[H", end="")


def print_report(progress):
    """打印进度报告"""
    print(f"\n{'='*80}")
    print(f"数据下载进度 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    print("[按年份统计]")
    target_stock_count = 5370
    for year in [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]:
        count = progress['by_year'].get(str(year), 0)
        pct = count / target_stock_count * 100
        bar_len = int(pct / 2)
        bar = '█' * bar_len + '░' * (50 - bar_len)
        print(f"  {year}: {count:4d}/{target_stock_count} ({pct:5.1f}%) [{bar}]")

    # 计算总体进度
    total_possible = target_stock_count * 11  # 11年
    total_have = sum(progress['by_year'].values())
    overall_pct = total_have / total_possible * 100

    print(f"\n[总体进度] {overall_pct:.1f}%")
    print(f"{'='*80}\n")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="终端实时监控")
    parser.add_argument("--interval", type=int, default=10, help="刷新间隔（分钟）")
    parser.add_argument("--once", action="store_true", help="只显示一次")

    args = parser.parse_args()

    if args.once:
        progress = scan_progress()
        print_report(progress)
    else:
        print(f"启动实时监控（每{args.interval}分钟刷新）")
        print("按 Ctrl+C 停止\n")

        try:
            while True:
                progress = scan_progress()
                print_report(progress)
                time.sleep(args.interval * 60)  # 转换为秒
        except KeyboardInterrupt:
            print("\n监控已停止")


if __name__ == "__main__":
    main()
