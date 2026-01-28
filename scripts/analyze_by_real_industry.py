# -*- coding: utf-8 -*-
"""
按行业板块回测分析 (使用akshare实际板块名称)
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


def analyze_by_industry(
    start_year: int = 2019,
    end_year: int = 2025
):
    """
    按行业板块回测并分析

    Args:
        start_year: 开始年份
        end_year: 结束年份
    """
    # 获取实际可用的行业板块
    loader = StockLoader()
    try:
        from akshare import stock_board_industry_name_em
        industries_df = stock_board_industry_name_em()
        industries = industries_df['板块名称'].tolist()
        print(f"找到 {len(industries)} 个行业板块")
    except Exception as e:
        print(f"获取行业板块失败: {e}")
        return

    print(f"{'='*80}")
    print(f"按行业板块回测分析 ({start_year}-{end_year})")
    print(f"{'='*80}")

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

    # 加载历史数据
    print(f"\n[2] 加载历史数据...")
    stock_history = loader.load_multiple_stocks(
        stock_list=all_stocks,
        start_date=data_start_date,
        end_date=data_end_date,
        max_stocks=None,
        progress_callback=lambda i, total, code: None
    )
    print(f"    成功加载: {len(stock_history)} 只股票")

    # 获取每个行业的成分股
    print(f"\n[3] 获取行业成分股...")
    industry_stocks = {}
    for i, industry in enumerate(industries):
        try:
            stocks = loader.get_sector_stocks(industry)
            # 过滤ST股票
            stocks = [s for s in stocks if s in all_stocks['code'].values]
            if stocks:
                industry_stocks[industry] = stocks
                print(f"  [{i+1:3d}/{len(industries)}] {industry}: {len(stocks)} 只")
        except Exception as e:
            # 跳过获取失败的板块
            industry_stocks[industry] = []

    print(f"\n    有效行业: {len([v for v in industry_stocks.values() if v])}/{len(industries)}")

    # 按行业回测
    print(f"\n[4] 按行业回测...")

    # 存储结果: {行业: {年份: results}}
    industry_results = defaultdict(dict)

    for idx, industry in enumerate(industries):
        stocks_in_industry = industry_stocks.get(industry, [])
        if not stocks_in_industry:
            continue

        # 筛选该行业的历史数据
        industry_history = {
            code: hist for code, hist in stock_history.items()
            if code in stocks_in_industry
        }

        if not industry_history:
            continue

        # 按年度回测
        year_returns = []
        for year_name, year_start, year_end in years:
            # 每年独立运行10万本金
            strategy = LimitUpPullbackStrategy()
            engine = BacktestEngine(strategy, initial_capital=100000)

            results = engine.run(
                stock_history=industry_history,
                start_date=year_start,
                end_date=year_end,
                stock_categories=None,
                progress_callback=None
            )

            industry_results[industry][year_name] = results
            year_returns.append(results['total_return'])

        avg_return = sum(year_returns) / len(year_returns) if year_returns else 0
        profitable_years = sum(1 for r in year_returns if r > 0)

        print(f"  [{idx+1:3d}/{len(industustries)}] {industry}: "
              f"平均={avg_return:>7.2f}%, 盈利年份={profitable_years}/{len(year_returns)}")

    # 同时计算整体市场表现作为对比
    print(f"\n[5] 计算整体市场表现...")
    market_results = {}
    market_year_returns = []
    for year_name, year_start, year_end in years:
        strategy = LimitUpPullbackStrategy()
        engine = BacktestEngine(strategy, initial_capital=100000)

        results = engine.run(
            stock_history=stock_history,
            start_date=year_start,
            end_date=year_end,
            stock_categories=None,
            progress_callback=None
        )

        market_results[year_name] = results
        market_year_returns.append(results['total_return'])

    market_avg_return = sum(market_year_returns) / len(market_year_returns)
    market_profitable_years = sum(1 for r in market_year_returns if r > 0)

    # 生成汇总报告
    print(f"\n{'='*80}")
    print("行业板块 vs 整体市场对比分析")
    print(f"{'='*80}")

    # 整体市场表现
    print(f"\n整体市场表现 ({start_year}-{end_year}):")
    print(f"  平均收益率: {market_avg_return:.2f}%")
    print(f"  盈利年份: {market_profitable_years}/{len(market_year_returns)}")
    print(f"\n  年度详细:")
    for year_name, results in market_results.items():
        print(f"    {year_name}: {results['total_return']:>7.2f}%, "
              f"交易={results['total_trades']:>3}, "
              f"胜率={results['win_rate']:>5.1f}%")

    # 按行业排名
    print(f"\n{'='*80}")
    print("行业板块收益率排名 (Top 20)")
    print(f"{'='*80}")

    industry_summary = []
    for industry, years_data in industry_results.items():
        year_returns = []
        for year_name, results in years_data.items():
            year_returns.append(results['total_return'])

        avg_return = sum(year_returns) / len(year_returns) if year_returns else 0
        profitable_years = sum(1 for r in year_returns if r > 0)

        # 计算与整体市场的超额收益
        excess_return = avg_return - market_avg_return

        industry_summary.append({
            'industry': industry,
            'avg_return': avg_return,
            'excess_return': excess_return,
            'total_return': sum(year_returns),
            'profitable_years': profitable_years,
            'total_years': len(year_returns)
        })

    # 按平均收益率排序
    industry_summary.sort(key=lambda x: x['avg_return'], reverse=True)

    print(f"\n{'排名':<4} {'行业板块':<20} {'平均收益率':>12} {'超额收益':>12} {'盈利年份':>12}")
    print(f"{'-'*80}")
    for i, s in enumerate(industry_summary[:20], 1):
        print(f"{i:<4} {s['industry']:<20} {s['avg_return']:>10.2f}% "
              f"{s['excess_return']:>10.2f}% {s['profitable_years']:>4}/{s['total_years']:<4}")

    # 表现最好的行业详细年度表现
    print(f"\n{'='*80}")
    print("表现最好行业的年度详情 (Top 10)")
    print(f"{'='*80}")

    print(f"\n{'行业板块':<15} ", end="")
    for year_name, _, _ in years:
        print(f"{year_name:>10} ", end="")
    print("平均")
    print(f"{'-'*80}")

    for i, s in enumerate(industry_summary[:10], 1):
        print(f"{s['industry']:<15} ", end="")
        avg_sum = 0
        count = 0
        for year_name, _, _ in years:
            if year_name in industry_results[s['industry']]:
                r = industry_results[s['industry']][year_name]
                ret = r['total_return']
                print(f"{ret:>9.2f}% ", end="")
                avg_sum += ret
                count += 1
            else:
                print(f"{'---':>9} ", end="")
        avg = avg_sum / count if count > 0 else 0
        print(f"{avg:>9.2f}%")

    # 保存结果
    print(f"\n[6] 保存结果...")
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存汇总
    summary_file = BACKTEST_RESULTS_DIR / f"industry_analysis_{start_year}_{end_year}_{timestamp}.csv"
    summary_df = pd.DataFrame(industry_summary)
    summary_df.to_csv(summary_file, index=False, encoding='utf-8')
    print(f"    汇总已保存: {summary_file}")

    # 保存年度明细
    detail_file = BACKTEST_RESULTS_DIR / f"industry_detail_{start_year}_{end_year}_{timestamp}.csv"
    detail_rows = []
    for industry, years_data in industry_results.items():
        for year, results in years_data.items():
            detail_rows.append({
                '行业板块': industry,
                '年份': year,
                '收益率': results['total_return'],
                '交易次数': results['total_trades'],
                '胜率': results['win_rate'],
                '最大回撤': results['max_drawdown']
            })
    detail_df = pd.DataFrame(detail_rows)
    detail_df.to_csv(detail_file, index=False, encoding='utf-8')
    print(f"    明细已保存: {detail_file}")

    # 保存整体市场数据
    market_file = BACKTEST_RESULTS_DIR / f"market_baseline_{start_year}_{end_year}_{timestamp}.csv"
    market_rows = []
    for year, results in market_results.items():
        market_rows.append({
            '年份': year,
            '收益率': results['total_return'],
            '交易次数': results['total_trades'],
            '胜率': results['win_rate'],
            '最大回撤': results['max_drawdown']
        })
    market_df = pd.DataFrame(market_rows)
    market_df.to_csv(market_file, index=False, encoding='utf-8')
    print(f"    市场基准已保存: {market_file}")

    print(f"\n{'='*80}")
    print("分析完成！")
    print(f"{'='*80}")

    return industry_results, industry_summary, market_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="按行业板块回测分析")
    parser.add_argument("--start-year", type=int, default=2019, help="开始年份")
    parser.add_argument("--end-year", type=int, default=2025, help="结束年份")

    args = parser.parse_args()

    analyze_by_industry(
        start_year=args.start_year,
        end_year=args.end_year
    )
