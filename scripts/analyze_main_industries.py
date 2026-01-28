# -*- coding: utf-8 -*-
"""
按主要行业板块回测分析
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


def analyze_main_industries(
    start_year: int = 2019,
    end_year: int = 2025
):
    """分析主要行业板块"""

    # 定义主要行业板块（手动选择有代表性的）
    main_industries = [
        '半导体', '电子元件', '计算机设备', '软件开发', '通信设备',
        '医药商业', '化学制药', '医疗器械', '生物制品',
        '汽车整车', '汽车零部件',
        '航空机场', '航天航空', '军工',
        '证券', '银行', '保险',
        '房地产开发', '装修建材',
        '电力行业', '煤炭行业', '石油行业', '有色金属',
        '食品饮料', '酿酒行业', '商业百货',
        '化学原料', '化学制品', '化纤行业',
        '工程机械', '专用设备', '通用设备',
        '文化传媒', '游戏', '教育'
    ]

    print(f"分析 {len(main_industries)} 个主要行业板块 ({start_year}-{end_year})")

    loader = StockLoader()

    # 准备年度列表
    years = []
    for year in range(start_year, end_year + 1):
        years.append((str(year), f"{year}0101", f"{year}1231"))

    # 数据起止日期
    data_start_date = f"{start_year - 1}0101"
    data_end_date = f"{end_year}1231"

    # 获取股票列表并过滤ST
    print(f"\n[1] 加载股票数据...")
    all_stocks = loader.get_stock_list()
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

    # 获取行业成分股
    print(f"\n[3] 获取行业成分股...")
    industry_stocks = {}
    for i, industry in enumerate(main_industries):
        try:
            stocks = loader.get_sector_stocks(industry)
            stocks = [s for s in stocks if s in all_stocks['code'].values]
            if stocks:
                industry_stocks[industry] = stocks
                print(f"  [{i+1:2d}/{len(main_industries)}] {industry}: {len(stocks)} 只")
        except Exception as e:
            print(f"  [{i+1:2d}/{len(main_industries)}] {industry}: 获取失败")
            industry_stocks[industry] = []

    # 按行业回测
    print(f"\n[4] 按行业回测...")
    industry_results = defaultdict(dict)

    for idx, industry in enumerate(main_industries):
        stocks_in_industry = industry_stocks.get(industry, [])
        if not stocks_in_industry:
            continue

        industry_history = {
            code: hist for code, hist in stock_history.items()
            if code in stocks_in_industry
        }

        if not industry_history:
            continue

        # 按年度回测
        year_returns = []
        for year_name, year_start, year_end in years:
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

        avg_return = sum(year_returns) / len(year_returns)
        profitable_years = sum(1 for r in year_returns if r > 0)

        print(f"  [{idx+1:2d}/{len(main_industries)}] {industry}: "
              f"平均={avg_return:>7.2f}%, 盈利={profitable_years}/{len(year_returns)}")

    # 计算整体市场表现
    print(f"\n[5] 计算整体市场基准...")
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

    market_avg = sum(market_year_returns) / len(market_year_returns)
    market_profitable = sum(1 for r in market_year_returns if r > 0)

    # 生成报告
    print(f"\n{'='*80}")
    print("整体市场基准 vs 行业板块对比")
    print(f"{'='*80}")
    print(f"\n整体市场: 平均={market_avg:.2f}%, 盈利年份={market_profitable}/{len(market_year_returns)}")

    print(f"\n{'='*80}")
    print("行业板块排名")
    print(f"{'='*80}")

    industry_summary = []
    for industry, years_data in industry_results.items():
        year_returns = []
        for year_name, results in years_data.items():
            year_returns.append(results['total_return'])

        avg = sum(year_returns) / len(year_returns)
        profitable = sum(1 for r in year_returns if r > 0)
        excess = avg - market_avg  # 超额收益

        industry_summary.append({
            'industry': industry,
            'avg_return': avg,
            'excess_return': excess,
            'profitable_years': profitable,
            'total_years': len(year_returns)
        })

    industry_summary.sort(key=lambda x: x['avg_return'], reverse=True)

    print(f"\n{'排名':<4} {'行业板块':<15} {'平均收益率':>12} {'超额收益':>12} {'盈利':>8}")
    print(f"{'-'*60}")
    for i, s in enumerate(industry_summary, 1):
        print(f"{i:<4} {s['industry']:<15} {s['avg_return']:>10.2f}% "
              f"{s['excess_return']:>10.2f}% {s['profitable_years']:>4}/{s['total_years']}")

    # 显示Top 5的年度详情
    print(f"\n{'='*80}")
    print("表现最好行业的年度详情 (Top 5)")
    print(f"{'='*80}")

    print(f"\n{'行业板块':<15} ", end="")
    for year_name, _, _ in years:
        print(f"{year_name:>9} ", end="")
    print("平均")

    for s in industry_summary[:5]:
        print(f"{s['industry']:<15} ", end="")
        for year_name, _, _ in years:
            if year_name in industry_results[s['industry']]:
                r = industry_results[s['industry']][year_name]
                print(f"{r['total_return']:>8.2f}% ", end="")
            else:
                print(f"{'--':>8} ", end="")
        avg = s['avg_return']
        print(f"{avg:>8.2f}%")

    # 保存结果
    print(f"\n[6] 保存结果...")
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存汇总
    summary_file = BACKTEST_RESULTS_DIR / f"industry_summary_{start_year}_{end_year}_{timestamp}.csv"
    pd.DataFrame(industry_summary).to_csv(summary_file, index=False, encoding='utf-8')
    print(f"    汇总: {summary_file}")

    # 保存年度明细
    detail_rows = []
    for industry, years_data in industry_results.items():
        for year, results in years_data.items():
            detail_rows.append({
                '行业板块': industry,
                '年份': year,
                '收益率': results['total_return'],
                '交易次数': results['total_trades'],
                '胜率': results['win_rate']
            })
    detail_file = BACKTEST_RESULTS_DIR / f"industry_detail_{start_year}_{end_year}_{timestamp}.csv"
    pd.DataFrame(detail_rows).to_csv(detail_file, index=False, encoding='utf-8')
    print(f"    明细: {detail_file}")

    # 保存市场基准
    market_rows = []
    for year, results in market_results.items():
        market_rows.append({
            '年份': year,
            '收益率': results['total_return'],
            '交易次数': results['total_trades'],
            '胜率': results['win_rate']
        })
    market_file = BACKTEST_RESULTS_DIR / f"market_baseline_{start_year}_{end_year}_{timestamp}.csv"
    pd.DataFrame(market_rows).to_csv(market_file, index=False, encoding='utf-8')
    print(f"    市场基准: {market_file}")

    return industry_results, industry_summary, market_results


if __name__ == "__main__":
    analyze_main_industries(2019, 2025)
