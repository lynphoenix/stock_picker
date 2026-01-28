# -*- coding: utf-8 -*-
"""
数据验证和补充脚本
1. 检查历史数据完整性
2. 补充2025年数据
3. 抓取主要指数数据
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, List, Tuple
import pickle

sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from src.data.cache import get_cache_manager
from settings import CACHE_DIR


def check_data_completeness():
    """
    检查历史数据完整性
    """
    print(f"{'='*80}")
    print("检查历史数据完整性")
    print(f"{'='*80}\n")

    # 统计缓存文件
    cache_files = list(CACHE_DIR.glob("stock_hist_*.pkl"))
    print(f"[1] 缓存文件总数: {len(cache_files)}")

    # 解析日期范围
    date_ranges = {}
    stock_dates = {}

    for file in cache_files:
        # 文件名格式: stock_hist_{code}_{start}_{end}_{adjust}.pkl
        parts = file.stem.split('_')
        if len(parts) >= 4:
            code = parts[2]
            start_date = parts[3]
            end_date = parts[4]

            if code not in stock_dates:
                stock_dates[code] = []
            stock_dates[code].append((start_date, end_date))

    print(f"[2] 股票数量: {len(stock_dates)}")

    # 统计日期覆盖
    print(f"\n[3] 日期范围覆盖:")
    all_ranges = set()
    for code, ranges in stock_dates.items():
        for start, end in ranges:
            all_ranges.add(f"{start}-{end}")

    sorted_ranges = sorted(list(all_ranges))
    for r in sorted_ranges:
        count = sum(1 for ranges in stock_dates.values() for s, e in ranges if f"{s}-{e}" == r)
        print(f"    {r}: {count} 只股票")

    # 检查数据缺失
    print(f"\n[4] 检查数据缺失:")

    # 目标日期范围
    target_ranges = [
        ("20130101", "20251231"),  # 2013-2015
        ("20160101", "20171231"),  # 2016-2017 (可能缺失)
        ("20180101", "20251231"),  # 2018-2025
        ("20260101", "20261231"),  # 2026年
    ]

    missing_data = {}
    sample_size = min(100, len(stock_dates))  # 检查前100只股票
    checked_stocks = list(stock_dates.keys())[:sample_size]

    for code in checked_stocks:
        ranges = stock_dates[code]
        covered_years = set()

        for start, end in ranges:
            start_year = int(start[:4])
            end_year = int(end[:4])
            for year in range(start_year, end_year + 1):
                covered_years.add(year)

        missing_years = []
        for year in range(2013, 2027):
            if year not in covered_years:
                missing_years.append(year)

        if missing_years:
            missing_data[code] = missing_years

    if missing_data:
        print(f"    随机抽检100只股票，{len(missing_data)}只有数据缺失:")
        for code, years in list(missing_data.items())[:10]:
            print(f"      {code}: 缺少 {years}")
    else:
        print(f"    抽检的100只股票数据完整")

    return stock_dates


def fetch_missing_2025_data():
    """
    补充2025年数据
    """
    print(f"\n{'='*80}")
    print("补充2025年数据")
    print(f"{'='*80}\n")

    loader = StockLoader()

    # 获取股票列表
    print("[1] 获取股票列表...")
    stock_list = loader.get_stock_list()
    print(f"    共 {len(stock_list)} 只股票")

    # 过滤掉ST股票
    stock_list = loader.filter_st_stocks(stock_list)
    print(f"    过滤ST后: {len(stock_list)} 只")

    # 2025年的日期范围
    start_date = "20250101"
    end_date = datetime.now().strftime("%Y%m%d")

    print(f"\n[2] 补充2025年数据 ({start_date} ~ {end_date})...")

    # 只更新部分股票进行测试
    test_stocks = stock_list.head(10)

    success_count = 0
    for i, (_, stock) in enumerate(test_stocks.iterrows()):
        code = stock['code']
        name = stock['name']

        print(f"  [{i+1}/{len(test_stocks)}] {code} {name}...", end=" ")

        try:
            df = loader.get_stock_history(code, start_date, end_date, use_cache=False)
            if df is not None and not df.empty:
                # 强制写入缓存
                cache_key = f"stock_hist_{code}_{start_date}_{end_date}_qfq"
                loader.cache.set(cache_key, df, "data")
                print(f"✓ {len(df)}条记录")
                success_count += 1
            else:
                print(f"✗ 无数据")
        except Exception as e:
            print(f"✗ 失败: {str(e)[:30]}")

        # 延迟避免限流
        time.sleep(0.2)

    print(f"\n[3] 成功更新: {success_count}/{len(test_stocks)}")


def fetch_index_data():
    """
    抓取主要指数数据
    """
    print(f"\n{'='*80}")
    print("抓取主要指数数据")
    print(f"{'='*80}\n")

    # 主要指数代码
    indices = {
        '000001': '上证指数',
        '399001': '深证成指',
        '399006': '创业板指',
        '000300': '沪深300',
        '000016': '上证50',
        '399905': '中证500',
    }

    loader = StockLoader()

    # 日期范围：2013年至今
    start_date = "20130101"
    end_date = datetime.now().strftime("%Y%m%d")

    print(f"[1] 抓取指数数据 ({start_date} ~ {end_date})...")

    for code, name in indices.items():
        print(f"  [{code}] {name}...", end=" ")

        try:
            df = loader.get_stock_history(code, start_date, end_date)
            if df is not None and not df.empty:
                print(f"✓ {len(df)}条记录")
                print(f"    日期范围: {df['date'].min()} ~ {df['date'].max()}")
            else:
                print(f"✗ 无数据")
        except Exception as e:
            print(f"✗ 失败: {str(e)[:50]}")

        # 延迟避免限流
        time.sleep(0.3)

    print(f"\n[2] 检查指数数据完整性...")

    # 验证指数数据
    for code, name in indices.items():
        # 检查缓存文件
        cache_files = list(CACHE_DIR.glob(f"stock_hist_{code}_*.pkl"))

        if cache_files:
            print(f"  ✓ {code} {name}: {len(cache_files)} 个缓存文件")
        else:
            print(f"  ✗ {code} {name}: 无缓存数据")


def generate_data_report():
    """
    生成数据报告
    """
    print(f"\n{'='*80}")
    print("数据完整性报告")
    print(f"{'='*80}\n")

    # 检查缓存大小
    cache_files = list(CACHE_DIR.glob("*.pkl"))
    total_size = sum(f.stat().st_size for f in cache_files) / 1024 / 1024

    print(f"[1] 缓存统计:")
    print(f"    文件数量: {len(cache_files)}")
    print(f"    总大小: {total_size:.1f} MB")

    # 按股票代码统计
    stock_codes = set()
    for f in cache_files:
        parts = f.stem.split('_')
        if len(parts) >= 3:
            stock_codes.add(parts[2])

    print(f"    股票数量: {len(stock_codes)}")
    print(f"    指数数量: {len([c for c in stock_codes if c.startswith('00') or c.startswith('39') or c.startswith('88')])}")

    # 检查2025年数据
    print(f"\n[2] 2025年数据检查:")
    files_2025 = [f for f in cache_files if '2025' in f.stem]
    print(f"    包含2025年的文件: {len(files_2025)}")

    if files_2025:
        # 检查覆盖的月份
        months_2025 = set()
        for f in files_2025:
            parts = f.stem.split('_')
            if len(parts) >= 5:
                months_2025.add(parts[4][:6])  # 提取月份

        print(f"    覆盖月份: {len(months_2025)} 个")
        print(f"    月份: {sorted(list(months_2025))}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据验证和补充")
    parser.add_argument("--check", action="store_true", help="检查数据完整性")
    parser.add_argument("--fetch-2025", action="store_true", help="补充2025年数据")
    parser.add_argument("--fetch-index", action="store_true", help="抓取指数数据")
    parser.add_argument("--report", action="store_true", help="生成数据报告")

    args = parser.parse_args()

    # 默认执行所有检查
    if not any([args.check, args.fetch_2025, args.fetch_index, args.report]):
        args.check = True
        args.report = True

    if args.check:
        check_data_completeness()

    if args.fetch_2025:
        fetch_missing_2025_data()

    if args.fetch_index:
        fetch_index_data()

    if args.report:
        generate_data_report()

    print(f"\n{'='*80}")
    print("完成!")
    print(f"{'='*80}")
