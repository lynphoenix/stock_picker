# -*- coding: utf-8 -*-
"""
从已有回测结果中按板块/行业统计
"""

import sys
import os
from pathlib import Path
import json
import pandas as pd
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from settings import BACKTEST_RESULTS_DIR


def analyze_from_saved_results(
    result_file: str = None,
    start_year: int = 2019,
    end_year: int = 2025
):
    """
    从已保存的回测结果中按行业统计

    Args:
        result_file: 回测结果JSON文件路径
        start_year: 开始年份
        end_year: 结束年份
    """
    print(f"{'='*80}")
    print(f"从已有回测结果分析板块表现 ({start_year}-{end_year})")
    print(f"{'='*80}")

    # 1. 读取已保存的回测结果
    print(f"\n[1] 读取回测结果...")

    if result_file is None:
        # 查找最新的结果文件
        result_files = list(BACKTEST_RESULTS_DIR.glob("full_backtest_*.json"))
        if not result_files:
            print("错误: 未找到回测结果文件")
            return
        result_file = max(result_files, key=lambda p: p.stat().st_mtime)

    print(f"    文件: {result_file}")

    with open(result_file, 'r', encoding='utf-8') as f:
        backtest_data = json.load(f)

    # 检查结果中是否有交易数据
    if 'years' not in backtest_data:
        print("错误: 结果文件中没有年度数据")
        return

    # 2. 获取股票代码列表
    print(f"\n[2] 提取交易股票代码...")

    traded_stocks = set()
    year_trades = {}  # {year: [stock_codes]}

    for year, year_data in backtest_data['years'].items():
        year_int = int(year)
        if start_year <= year_int <= end_year:
            # 检查是否有category_stats
            if 'category_stats' in year_data and year_data['category_stats']:
                # 从category_stats中提取交易股票
                for category, stats in year_data['category_stats'].items():
                    if isinstance(stats, dict) and 'total_trades' in stats and stats['total_trades'] > 0:
                        traded_stocks.add(category)  # 这里category可能是股票代码
                        year_trades[year] = year_trades.get(year, [])
            else:
                print(f"    警告: {year}年没有category_stats数据")

    print(f"    提取到 {len(traded_stocks)} 个交易记录")

    # 3. 获取股票的行业分类
    print(f"\n[3] 获取股票行业分类...")

    loader = StockLoader()

    # 获取行业列表
    try:
        from akshare import stock_board_industry_name_em
        industries_df = stock_board_industry_name_em()
        all_industries = industries_df['板块名称'].tolist()
        print(f"    可用行业: {len(all_industries)} 个")
    except Exception as e:
        print(f"    获取行业列表失败: {e}")
        all_industries = []

    # 获取股票列表
    all_stocks = loader.get_stock_list()

    # 为每个股票获取行业
    stock_to_industry = {}

    print(f"    查询 {len(traded_stocks)} 只股票的行业...")

    for i, stock_code in enumerate(traded_stocks):
        if not stock_code.startswith(('0', '3', '6')):  # 跳过非股票代码
            continue

        try:
            # 获取股票信息
            stock_info = all_stocks[all_stocks['code'] == stock_code]
            if stock_info.empty:
                continue

            stock_code_full = stock_info.iloc[0]['code']
            stock_name = stock_info.iloc[0]['name']

            # 尝试从多个行业获取成分股，找到这只股票所属的行业
            industry = None
            for ind in all_industries[:20]:  # 先查前20个行业
                try:
                    members = loader.get_sector_stocks(ind)
                    if stock_code in members:
                        industry = ind
                        break
                except:
                    continue

            stock_to_industry[stock_code] = industry or '其他'

            if (i + 1) % 100 == 0:
                print(f"      进度: {i+1}/{len(traded_stocks)}")

        except Exception as e:
            stock_to_industry[stock_code] = '其他'

    print(f"    完成: 已分类 {len(stock_to_industry)} 只股票")

    # 4. 按行业汇总统计
    print(f"\n[4] 按行业汇总统计...")

    industry_stats = defaultdict(lambda: {
        'years': [],
        'total_return': 0,
        'total_trades': 0,
        'profitable_years': 0,
        'win_rate_sum': 0,
        'win_rate_count': 0
    })

    # 这里由于没有详细的交易记录，我们只能做粗略统计
    # 使用已有的年度数据

    print(f"\n{'='*80}")
    print("注意: 当前回测结果中没有保存详细交易记录")
    print("建议: 修改回测脚本，保存每笔交易的详细信息")
    print(f"{'='*80}")

    return stock_to_industry


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="从已有结果分析板块表现")
    parser.add_argument("--result-file", type=str, help="回测结果文件路径")
    parser.add_argument("--start-year", type=int, default=2019, help="开始年份")
    parser.add_argument("--end-year", type=int, default=2025, help="结束年份")

    args = parser.parse_args()

    analyze_from_saved_results(
        result_file=args.result_file,
        start_year=args.start_year,
        end_year=args.end_year
    )
