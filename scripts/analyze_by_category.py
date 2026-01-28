# -*- coding: utf-8 -*-
"""
按板块分析回测结果
"""

import sys
import os
from pathlib import Path
import json
import pandas as pd
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from src.strategy.limit_up_pullback import LimitUpPullbackStrategy
from src.backtest.engine import BacktestEngine
from settings import BACKTEST_RESULTS_DIR


def analyze_by_sector(
    start_year: int = 2014,
    end_year: int = 2025,
    sectors: list = None
):
    """
    按板块回测并分析

    Args:
        start_year: 开始年份
        end_year: 结束年份
        sectors: 板块列表
    """
    if sectors is None:
        sectors = [
            '人工智能', '新能源车', '半导体', '锂电池', '光伏',
            '医药', '白酒', '军工', '券商', '银行',
            '房地产', '钢铁', '煤炭', '有色金属', '石油',
            '电力', '公用事业', '传媒', '计算机', '通信',
            '电子', '汽车', '化工', '机械', '建筑'
        ]

    print(f"{'='*80}")
    print(f"按板块回测分析 ({start_year}-{end_year})")
    print(f"{'='*80}")

    loader = StockLoader()

    # 准备年度列表
    years = []
    for year in range(start_year, end_year + 1):
        years.append((str(year), f"{year}0101", f"{year}1231"))

    # 数据起止日期（多加载一年用于计算指标）
    data_start_date = f"{start_year - 1}0101"
    data_end_date = f"{end_year}1231"

    # 获取股票列表并过滤ST
    print(f"\n[1] 加载股票数据...")
    all_stocks = loader.get_stock_list()
    print(f"    总股票数: {len(all_stocks)}")
    all_stocks = loader.filter_st_stocks(all_stocks)
    print(f"    剔除ST后: {len(all_stocks)}")

    # 获取板块成分股
    print(f"\n[2] 获取板块成分股...")
    sector_stocks = {}
    for sector in sectors:
        try:
            stocks = loader.get_sector_stocks(sector)
            # 过滤ST股票
            stocks = [s for s in stocks if s in all_stocks['code'].values]
            sector_stocks[sector] = stocks
            print(f"    {sector}: {len(stocks)} 只")
        except Exception as e:
            print(f"    {sector}: 获取失败 - {e}")
            sector_stocks[sector] = []

    # 加载历史数据
    print(f"\n[3] 加载历史数据...")
    stock_history = loader.load_multiple_stocks(
        stock_list=all_stocks,
        start_date=data_start_date,
        end_date=data_end_date,
        max_stocks=None,
        progress_callback=lambda i, total, code: None
    )
    print(f"    成功加载: {len(stock_history)} 只股票")

    # 按板块和年度回测
    print(f"\n[4] 按板块回测...")

    # 存储结果: {板块: {年份: results}}
    sector_results = defaultdict(dict)

    for sector in sectors:
        print(f"\n{'='*70}")
        print(f"板块: {sector}")
        print(f"{'='*70}")

        stocks_in_sector = sector_stocks.get(sector, [])
        if not stocks_in_sector:
            print(f"  跳过（无成分股）")
            continue

        # 筛选该板块的历史数据
        sector_history = {
            code: hist for code, hist in stock_history.items()
            if code in stocks_in_sector
        }

        if not sector_history:
            print(f"  跳过（无历史数据）")
            continue

        print(f"  有效股票: {len(sector_history)}")

        # 按年度回测
        for year_name, year_start, year_end in years:
            # 每年独立运行10万本金
            strategy = LimitUpPullbackStrategy()
            engine = BacktestEngine(strategy, initial_capital=100000)

            results = engine.run(
                stock_history=sector_history,
                start_date=year_start,
                end_date=year_end,
                stock_categories=None,
                progress_callback=None
            )

            sector_results[sector][year_name] = results

            print(f"  {year_name}: 收益率={results['total_return']:>7.2f}%, "
                  f"交易={results['total_trades']:>3}, "
                  f"胜率={results['win_rate']:>5.1f}%")

    # 生成汇总报告
    print(f"\n{'='*80}")
    print("按板块年度分析")
    print(f"{'='*80}")

    # 按板块×年度的表格
    print(f"\n{'板块':<12} ", end="")
    for year_name, _, _ in years:
        print(f"{year_name:>10} ", end="")
    print("平均")
    print(f"{'-'*80}")

    for sector in sectors:
        if sector not in sector_results:
            continue

        print(f"{sector:<12} ", end="")

        total_return = 0
        count = 0

        for year_name, _, _ in years:
            if year_name in sector_results[sector]:
                r = sector_results[sector][year_name]
                ret = r['total_return']
                print(f"{ret:>9.2f}% ", end="")
                total_return += ret
                count += 1
            else:
                print(f"{'---':>9} ", end="")

        avg_return = total_return / count if count > 0 else 0
        print(f"{avg_return:>9.2f}%")

    # 按板块汇总
    print(f"\n{'='*80}")
    print("板块汇总 (2014-2025)")
    print(f"{'='*80}")

    sector_summary = []
    for sector, years_data in sector_results.items():
        total_return = 0
        total_trades = 0
        total_win = 0
        profitable_years = 0
        count = 0

        for year_name, results in years_data.items():
            total_return += results['total_return']
            total_trades += results['total_trades']
            total_win += results['win_rate'] * results['total_trades']
            if results['total_return'] > 0:
                profitable_years += 1
            count += 1

        avg_return = total_return / count if count > 0 else 0
        avg_trades = total_trades / count if count > 0 else 0
        avg_win_rate = total_win / total_trades if total_trades > 0 else 0

        sector_summary.append({
            'sector': sector,
            'avg_return': avg_return,
            'total_return': total_return,
            'avg_trades': avg_trades,
            'avg_win_rate': avg_win_rate,
            'profitable_years': profitable_years,
            'total_years': count
        })

    # 按平均收益率排序
    sector_summary.sort(key=lambda x: x['avg_return'], reverse=True)

    print(f"\n{'板块':<12} {'平均收益率':>12} {'总收益率':>12} {'年均交易':>12} {'平均胜率':>12} {'盈利年份':>12}")
    print(f"{'-'*80}")
    for s in sector_summary:
        print(f"{s['sector']:<12} {s['avg_return']:>10.2f}% "
              f"{s['total_return']:>10.2f}% {s['avg_trades']:>10.1f} "
              f"{s['avg_win_rate']:>10.1f}% {s['profitable_years']:>3}/{s['total_years']:<3}")

    # 保存结果为CSV格式
    print(f"\n[5] 保存结果...")
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存板块汇总为CSV
    summary_file = BACKTEST_RESULTS_DIR / f"sector_analysis_{start_year}_{end_year}_{timestamp}.csv"
    summary_df = pd.DataFrame(sector_summary)
    summary_df.to_csv(summary_file, index=False, encoding='utf-8')
    print(f"    结果已保存: {summary_file}")

    # 保存年度明细为CSV
    detail_file = BACKTEST_RESULTS_DIR / f"sector_detail_{start_year}_{end_year}_{timestamp}.csv"
    detail_rows = []
    for sector, years_data in sector_results.items():
        for year, results in years_data.items():
            detail_rows.append({
                '板块': sector,
                '年份': year,
                '收益率': results['total_return'],
                '交易次数': results['total_trades'],
                '胜率': results['win_rate'],
                '最大回撤': results['max_drawdown']
            })
    detail_df = pd.DataFrame(detail_rows)
    detail_df.to_csv(detail_file, index=False, encoding='utf-8')
    print(f"    明细已保存: {detail_file}")

    return sector_results, sector_summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="按板块回测分析")
    parser.add_argument("--start-year", type=int, default=2014, help="开始年份")
    parser.add_argument("--end-year", type=int, default=2025, help="结束年份")
    parser.add_argument("--sectors", nargs="+", help="指定板块列表")

    args = parser.parse_args()

    analyze_by_sector(
        start_year=args.start_year,
        end_year=args.end_year,
        sectors=args.sectors
    )
