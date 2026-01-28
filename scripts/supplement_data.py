# -*- coding: utf-8 -*-
"""
补充回测交易股票的2023-2025年数据
"""

import sys
from pathlib import Path
import pickle
import pandas as pd
from datetime import datetime
import time

sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from settings import CACHE_DIR


def get_traded_stocks():
    """
    从回测结果中提取交易的股票代码
    """
    import json
    from pathlib import Path

    results_dir = Path('data/backtest_results')
    result_files = list(results_dir.glob('full_backtest_*.json'))

    if not result_files:
        print("未找到回测结果文件")
        return set()

    latest = max(result_files, key=lambda f: f.stat().st_mtime)

    with open(latest, 'r') as f:
        data = json.load(f)

    all_stocks = set()
    for year, year_data in data['years'].items():
        if 'trades' in year_data:
            for trade in year_data['trades']:
                all_stocks.add(trade.get('code'))

    return all_stocks


def check_stock_data_completeness(stock_codes):
    """
    检查股票的数据完整性
    """
    cache_files = list(CACHE_DIR.glob('stock_hist_*.pkl'))

    stock_file_count = {}
    for f in cache_files:
        parts = f.stem.split('_')
        if len(parts) >= 3:
            code = parts[2]
            if code in stock_codes:
                stock_file_count[code] = stock_file_count.get(code, 0) + 1

    # 按完整性分类
    complete_stocks = []  # 有完整数据（>=35个文件）
    partial_stocks = []    # 数据不完整（<10个文件）
    missing_stocks = []   # 缺少数据

    for code in stock_codes:
        count = stock_file_count.get(code, 0)
        if count >= 35:
            complete_stocks.append(code)
        elif count < 10:
            missing_stocks.append(code)
        else:
            partial_stocks.append(code)

    return complete_stocks, partial_stocks, missing_stocks


def fetch_stock_data(stock_code, start_date, end_date, loader):
    """
    抓取单只股票的数据
    """
    try:
        df = loader.get_stock_history(stock_code, start_date, end_date, use_cache=False)
        if df is not None and not df.empty:
            # 强制写入缓存
            cache_key = f"stock_hist_{stock_code}_{start_date}_{end_date}_qfq"
            loader.cache.set(cache_key, df, "data")
            return len(df)
        return 0
    except Exception as e:
        return 0


def supplement_2023_2025_data():
    """
    补充2023-2025年数据
    """
    print(f"{'='*80}")
    print("补充回测股票2023-2025年数据")
    print(f"{'='*80}\n")

    # 1. 获取交易的股票列表
    print("[1] 获取回测中交易的股票列表...")
    traded_stocks = get_traded_stocks()
    print(f"    找到 {len(traded_stocks)} 只交易股票")

    # 2. 检查数据完整性
    print(f"\n[2] 检查数据完整性...")
    complete, partial, missing = check_stock_data_completeness(traded_stocks)
    print(f"    数据完整 (≥35文件): {len(complete)} 只")
    print(f"    数据部分完整: {len(partial)} 只")
    print(f"    缺少数据 (<10文件): {len(missing)} 只")

    # 3. 补充缺失数据
    need_update = partial + missing
    print(f"\n[3] 需要补充数据的股票: {len(need_update)}")

    if not need_update:
        print("    所有股票数据完整，无需补充")
        return

    loader = StockLoader()

    # 按年份分段抓取（2023、2024、2025）
    years = ['2023', '2024', '2025']

    success_count = 0
    failed_stocks = []

    for i, stock_code in enumerate(need_update):
        print(f"  [{i+1}/{len(need_update)}] {stock_code}...", end=" ")

        stock_success = 0
        for year in years:
            # 尝试抓取该年数据
            start_date = f"{year}0101"
            if year == '2025':
                end_date = datetime.now().strftime("%Y%m%d")
            else:
                end_date = f"{year}1231"

            try:
                count = fetch_stock_data(stock_code, start_date, end_date, loader)
                if count > 0:
                    stock_success += count
                    print(f"+{count}", end="")
                time.sleep(0.05)  # 短暂延迟
            except:
                pass

        if stock_success > 0:
            print(f" ✓ ({stock_success}条记录)")
            success_count += 1
        else:
            print(f" ✗")
            failed_stocks.append(stock_code)

        # 每50只股票暂停一下
        if (i + 1) % 50 == 0:
            print(f"\n  进度: {i+1}/{len(need_update)}, 暂停3秒...")
            time.sleep(3)

    print(f"\n[4] 结果统计:")
    print(f"    成功更新: {success_count}/{len(need_update)} 只股票")
    if failed_stocks:
        print(f"    失败股票 ({len(failed_stocks)}只): {failed_stocks[:10]}...")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="补充2023-2025年数据")
    parser.add_argument("--run", action="store_true", help="执行数据补充")

    args = parser.parse_args()

    if args.run:
        supplement_2023_2025_data()
    else:
        print("使用方法: python supplement_data.py --run")
