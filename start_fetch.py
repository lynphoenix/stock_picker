#!/usr/bin/env python3
"""
全量数据采集脚本 - 从2020年至今
"""
import sys
import os
import asyncio

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

sys.path.insert(0, '/root/data2/lyn/stock_picker')

from core.data.auto_fetcher import AutoDataFetcher

def main():
    print("🚀 启动数据采集脚本...")
    sys.stdout.flush()

    fetcher = AutoDataFetcher()

    # 全量采集参数
    start_date = "20200101"
    end_date = "20261231"
    stock_pool = "all"  # 全市场

    print(f"📋 配置:")
    print(f"   股票池: {stock_pool}")
    print(f"   日期范围: {start_date} ~ {end_date}")
    sys.stdout.flush()

    # 获取股票列表
    stock_list = fetcher.get_stock_list(stock_pool)
    print(f"   股票数量: {len(stock_list)}")
    sys.stdout.flush()

    # 定义进度回调
    def on_progress(stats):
        print(f"📊 进度: {stats.get('total', 0)}/{stats.get('completed', 0)} 成功:{stats.get('success', 0)} 失败:{stats.get('failed', 0)} 跳过:{stats.get('skipped', 0)}")
        sys.stdout.flush()

    # 开始采集
    print("🚀 开始采集...")
    sys.stdout.flush()

    result = fetcher.fetch_daily_data_sync(
        stock_pool=stock_pool,
        start_date=start_date,
        end_date=end_date,
        max_concurrent=5,
        retry_times=3,
        on_progress=on_progress
    )

    print(f"\n✅ 采集完成!")
    print(f"   成功: {result.get('success', 0)}")
    print(f"   失败: {result.get('failed', 0)}")
    print(f"   跳过: {result.get('skipped', 0)}")
    sys.stdout.flush()

if __name__ == "__main__":
    main()
