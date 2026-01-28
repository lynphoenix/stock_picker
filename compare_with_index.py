# -*- coding: utf-8 -*-
"""
对比本策略与大盘（上证指数）的涨跌幅
按年度和按月度分别对比
"""

import pandas as pd
import numpy as np
import akshare as ak
import json
import os
from datetime import datetime


def get_index_data():
    """获取上证指数数据"""
    print("获取上证指数数据...")
    index_data = ak.stock_zh_index_daily(symbol='sh000001')
    index_data['date'] = pd.to_datetime(index_data['date'])

    # 筛选2018-2025年的数据
    filtered = index_data[
        (index_data['date'] >= '2018-01-01') &
        (index_data['date'] <= '2025-12-31')
    ].copy()
    filtered = filtered.sort_values('date').reset_index(drop=True)

    # 计算涨跌幅
    filtered['涨跌幅'] = filtered['close'].pct_change() * 100

    return filtered


def load_strategy_results():
    """加载策略回测结果"""
    print("加载策略回测结果...")
    results_file = "data/backtest_results/multi_year_summary_2019_2025.json"

    if not os.path.exists(results_file):
        print(f"错误: 结果文件不存在: {results_file}")
        return None

    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    return results


def calculate_yearly_returns(index_data):
    """计算上证指数年度收益率"""
    yearly_returns = {}

    for year in range(2019, 2026):
        year_start = f"{year}-01-01"
        year_end = f"{year}-12-31"

        # 获取年初和年末收盘价
        year_data = index_data[
            (index_data['date'] >= year_start) &
            (index_data['date'] <= year_end)
        ]

        if len(year_data) > 0:
            year_open = year_data.iloc[0]['close']
            year_close = year_data.iloc[-1]['close']
            yearly_return = (year_close - year_open) / year_open * 100
            yearly_returns[year] = {
                'open': year_open,
                'close': year_close,
                'return': yearly_return
            }

    return yearly_returns


def calculate_monthly_returns(index_data):
    """计算上证指数月度收益率"""
    monthly_returns = {}

    for year in range(2019, 2026):
        for month in range(1, 13):
            month_start = f"{year}-{month:02d}-01"

            # 计算月末日期
            if month == 12:
                month_end = f"{year+1}-01-01"
            else:
                month_end = f"{year}-{month+1:02d}-01"

            # 获取本月数据
            month_data = index_data[
                (index_data['date'] >= month_start) &
                (index_data['date'] < month_end)
            ]

            if len(month_data) > 0:
                month_open = month_data.iloc[0]['close']
                month_close = month_data.iloc[-1]['close']
                month_return = (month_close - month_open) / month_open * 100

                key = f"{year}-{month:02d}"
                monthly_returns[key] = {
                    'open': month_open,
                    'close': month_close,
                    'return': month_return
                }

    return monthly_returns


def print_yearly_comparison(strategy_results, index_yearly):
    """打印年度对比"""
    print("\n" + "=" * 80)
    print("年度收益率对比 - 策略 vs 上证指数")
    print("=" * 80)
    print(f"{'年份':<8} {'策略收益率':>15} {'上证指数收益率':>15} {'超额收益':>15} {'对比':>10}")
    print("-" * 80)

    for year in range(2019, 2026):
        year_str = str(year)
        strategy_return = strategy_results['years'][year_str]['total_return']
        index_return = index_yearly[year]['return']
        excess_return = strategy_return - index_return

        # 判断谁表现更好
        if excess_return > 0:
            comparison = "★★策略胜"
        elif excess_return < 0:
            comparison = "★★大盘胜"
        else:
            comparison = "★持平"

        print(f"{year:<8} {strategy_return:>13.2f}%     {index_return:>13.2f}%     {excess_return:>13.2f}%   {comparison}")

    # 总体对比
    print("-" * 80)
    strategy_total = strategy_results['total_return']
    index_total = sum([r['return'] for r in index_yearly.values()])
    excess_total = strategy_total - index_total
    comparison_total = "★★策略胜" if excess_total > 0 else "★★大盘胜"
    print(f"{'总计':<8} {strategy_total:>13.2f}%     {index_total:>13.2f}%     {excess_total:>13.2f}%   {comparison_total}")
    print("=" * 80)


def print_monthly_comparison(index_monthly):
    """打印月度对比（仅上证指数，因为策略没有月度数据）"""
    print("\n" + "=" * 100)
    print("上证指数月度收益率 (2019-2025)")
    print("=" * 100)

    # 按年份分组打印
    for year in range(2019, 2026):
        print(f"\n{year}年:")
        print(f"{'月份':<8} {'开盘点位':>12} {'收盘点位':>12} {'涨跌幅':>12} {'涨跌情况':>10}")
        print("-" * 60)

        year_months = {k: v for k, v in index_monthly.items() if k.startswith(f"{year}-")}

        for month in range(1, 13):
            key = f"{year}-{month:02d}"
            if key in year_months:
                data = year_months[key]
                trend = "上涨" if data['return'] > 0 else "下跌" if data['return'] < 0 else "持平"
                print(f"{key:<8} {data['open']:>10.2f}     {data['close']:>10.2f}     {data['return']:>10.2f}%    {trend}")

    print("\n" + "=" * 100)


def print_bull_bear_analysis(strategy_results, index_yearly):
    """牛熊市分析"""
    print("\n" + "=" * 80)
    print("牛熊市表现分析")
    print("=" * 80)

    bull_years = []
    bear_years = []

    for year in range(2019, 2026):
        year_str = str(year)
        index_return = index_yearly[year]['return']

        if index_return > 0:
            bull_years.append(year)
        else:
            bear_years.append(year)

    print(f"\n牛市年份（大盘上涨）: {', '.join(map(str, bull_years))}")
    print(f"{'年份':<8} {'策略收益率':>15} {'上证指数收益率':>15} {'超额收益':>15}")
    print("-" * 60)

    for year in bull_years:
        year_str = str(year)
        strategy_return = strategy_results['years'][year_str]['total_return']
        index_return = index_yearly[year]['return']
        excess_return = strategy_return - index_return
        print(f"{year:<8} {strategy_return:>13.2f}%     {index_return:>13.2f}%     {excess_return:>13.2f}%")

    print(f"\n熊市年份（大盘下跌）: {', '.join(map(str, bear_years))}")
    print(f"{'年份':<8} {'策略收益率':>15} {'上证指数收益率':>15} {'超额收益':>15}")
    print("-" * 60)

    for year in bear_years:
        year_str = str(year)
        strategy_return = strategy_results['years'][year_str]['total_return']
        index_return = index_yearly[year]['return']
        excess_return = strategy_return - index_return
        print(f"{year:<8} {strategy_return:>13.2f}%     {index_return:>13.2f}%     {excess_return:>13.2f}%")

    print("=" * 80)


def main():
    """主函数"""
    print("=" * 80)
    print("策略 vs 上证指数 收益率对比分析")
    print("=" * 80)

    # 获取数据
    index_data = get_index_data()
    strategy_results = load_strategy_results()

    if strategy_results is None:
        return

    # 计算收益率
    index_yearly = calculate_yearly_returns(index_data)
    index_monthly = calculate_monthly_returns(index_data)

    # 打印对比结果
    print_yearly_comparison(strategy_results, index_yearly)
    print_bull_bear_analysis(strategy_results, index_yearly)
    print_monthly_comparison(index_monthly)

    # 保存对比结果
    print("\n保存对比结果...")
    comparison_results = {
        'yearly_comparison': {},
        'monthly_comparison': index_monthly,
    }

    for year in range(2019, 2026):
        year_str = str(year)
        comparison_results['yearly_comparison'][year_str] = {
            'strategy_return': strategy_results['years'][year_str]['total_return'],
            'index_return': index_yearly[year]['return'],
            'excess_return': strategy_results['years'][year_str]['total_return'] - index_yearly[year]['return']
        }

    output_dir = "data/backtest_results"
    os.makedirs(output_dir, exist_ok=True)
    comparison_file = os.path.join(output_dir, "strategy_vs_index_2019_2025.json")

    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, ensure_ascii=False, indent=2)

    print(f"对比结果已保存: {comparison_file}")
    print("\n分析完成！")


if __name__ == "__main__":
    main()
