# -*- coding: utf-8 -*-
"""
对比本策略与大盘（上证指数）的月度涨跌幅
"""

import pandas as pd
import numpy as np
import akshare as ak
import json
import os
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_fetcher import DataFetcher


def get_index_monthly_returns():
    """获取上证指数月度收益率"""
    print("获取上证指数数据...")
    index_data = ak.stock_zh_index_daily(symbol='sh000001')
    index_data['date'] = pd.to_datetime(index_data['date'])

    # 筛选2019-2025年的数据
    filtered = index_data[
        (index_data['date'] >= '2019-01-01') &
        (index_data['date'] <= '2025-12-31')
    ].copy()
    filtered = filtered.sort_values('date').reset_index(drop=True)

    # 按月分组计算收益率
    filtered['year_month'] = filtered['date'].dt.to_period('M')
    monthly_returns = {}

    for ym, group in filtered.groupby('year_month'):
        month_open = group.iloc[0]['close']
        month_close = group.iloc[-1]['close']
        month_return = (month_close - month_open) / month_open * 100
        monthly_returns[str(ym)] = month_return

    return monthly_returns


def run_backtest_with_monthly_data():
    """运行回测并保存月度数据"""
    print("运行回测并计算月度收益...")

    fetcher = DataFetcher()

    # 回测参数
    years = [
        ('2019', '20190101', '20191231'),
        ('2020', '20200101', '20201231'),
        ('2021', '20210101', '20211231'),
        ('2022', '20220101', '20221231'),
        ('2023', '20230101', '20231231'),
        ('2024', '20240101', '20241231'),
        ('2025', '20250101', '20251231'),
    ]

    # 获取股票列表
    print("获取股票列表...")
    all_stocks = fetcher.get_stock_list()
    max_stocks = min(len(all_stocks), 2000)
    sample_stocks = all_stocks.head(max_stocks)

    # 准备历史数据
    print(f"获取历史行情数据...")
    stock_history = {}

    for i, (_, stock) in enumerate(sample_stocks.iterrows()):
        code = stock['code']
        name = stock['name']

        try:
            hist = fetcher.get_stock_history(
                symbol=code,
                start_date="20180101",
                end_date="20251231",
                adjust="qfq"
            )

            if hist is not None and not hist.empty:
                hist['code'] = code
                hist['name'] = name
                hist['涨跌幅'] = hist['close'].pct_change() * 100
                stock_history[code] = hist

        except Exception as e:
            continue

        if (i + 1) % 500 == 0:
            print(f"    进度: {i+1}/{len(sample_stocks)}")

    print(f"成功获取: {len(stock_history)} 只股票")

    # 导入回测类
    from backtest_multi_year import MultiYearBacktest

    # 存储月度数据
    all_monthly_returns = {}
    current_cash = 100000

    for year_name, start_date, end_date in years:
        print(f"\\n回测年度: {year_name}")

        backtest = MultiYearBacktest()
        results = backtest.run_single_year(
            stock_history=stock_history,
            start_date=start_date,
            end_date=end_date,
            initial_cash=current_cash
        )

        current_cash = results['final_capital']

        # 计算月度收益率
        daily_values = results.get('daily_values_df', pd.DataFrame())
        if not daily_values.empty:
            daily_values['date'] = pd.to_datetime(daily_values['date'])
            daily_values['year_month'] = daily_values['date'].dt.to_period('M')

            monthly_data = {}
            for ym, group in daily_values.groupby('year_month'):
                if len(group) > 0:
                    month_start_value = group.iloc[0]['value']
                    month_end_value = group.iloc[-1]['value']
                    month_return = (month_end_value - month_start_value) / month_start_value * 100
                    key = f"{ym.year}-{ym.month:02d}"
                    monthly_data[key] = month_return

            all_monthly_returns.update(monthly_data)

    return all_monthly_returns


def load_or_compute_monthly_returns():
    """加载或计算策略月度收益率"""
    cache_file = "data/backtest_results/strategy_monthly_returns_2019_2025.json"

    if os.path.exists(cache_file):
        print("加载已缓存的策略月度收益率...")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # 计算并缓存
    monthly_returns = run_backtest_with_monthly_data()

    os.makedirs("data/backtest_results", exist_ok=True)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(monthly_returns, f, ensure_ascii=False, indent=2)

    return monthly_returns


def print_monthly_comparison(strategy_monthly, index_monthly):
    """打印月度对比"""
    print("\n" + "=" * 100)
    print("月度收益率对比 - 策略 vs 上证指数 (2019-2025)")
    print("=" * 100)

    for year in range(2019, 2026):
        print(f"\n{'='*100}")
        print(f"{year}年")
        print(f"{'='*100}")
        print(f"{'月份':<10} {'策略收益率':>15} {'上证指数收益率':>15} {'超额收益':>15} {'对比':>10}")
        print("-" * 100)

        year_win = 0
        year_lose = 0

        for month in range(1, 13):
            key = f"{year}-{month:02d}"

            strategy_return = strategy_monthly.get(key, 0)
            index_return = index_monthly.get(key, 0)
            excess_return = strategy_return - index_return

            if excess_return > 0:
                comparison = "策略胜"
                year_win += 1
            elif excess_return < 0:
                comparison = "大盘胜"
                year_lose += 1
            else:
                comparison = "持平"

            print(f"{key:<10} {strategy_return:>13.2f}%     {index_return:>13.2f}%     {excess_return:>13.2f}%   {comparison}")

        print("-" * 100)
        print(f"年度统计: 策略胜 {year_win} 个月, 大盘胜 {year_lose} 个月")


def print_summary_statistics(strategy_monthly, index_monthly):
    """打印汇总统计"""
    print("\n" + "=" * 80)
    print("月度收益率统计摘要")
    print("=" * 80)

    # 计算统计数据
    strategy_returns = list(strategy_monthly.values())
    index_returns = [index_monthly.get(k, 0) for k in strategy_monthly.keys()]

    # 计算胜率
    win_months = sum(1 for k in strategy_monthly.keys()
                      if strategy_monthly[k] > index_monthly.get(k, 0))
    total_months = len(strategy_monthly)

    # 计算正收益月份
    strategy_positive = sum(1 for r in strategy_returns if r > 0)
    index_positive = sum(1 for r in index_returns if r > 0)

    # 计算平均月度收益
    avg_strategy = np.mean(strategy_returns)
    avg_index = np.mean(index_returns)

    # 计算最大月度涨跌
    max_strategy = max(strategy_returns)
    min_strategy = min(strategy_returns)
    max_index = max(index_returns)
    min_index = min(index_returns)

    print(f"\n总月份数: {total_months}")
    print(f"策略跑赢月份: {win_months} ({win_months/total_months*100:.1f}%)")
    print(f"大盘跑赢月份: {total_months - win_months} ({(total_months-win_months)/total_months*100:.1f}%)")

    print(f"\n正收益月份:")
    print(f"  策略: {strategy_positive} 个月 ({strategy_positive/total_months*100:.1f}%)")
    print(f"  大盘: {index_positive} 个月 ({index_positive/total_months*100:.1f}%)")

    print(f"\n平均月度收益率:")
    print(f"  策略: {avg_strategy:.2f}%")
    print(f"  大盘: {avg_index:.2f}%")

    print(f"\n最大单月涨幅:")
    print(f"  策略: {max_strategy:.2f}%")
    print(f"  大盘: {max_index:.2f}%")

    print(f"\n最大单月跌幅:")
    print(f"  策略: {min_strategy:.2f}%")
    print(f"  大盘: {min_index:.2f}%")

    print("=" * 80)


def main():
    """主函数"""
    print("=" * 100)
    print("策略 vs 上证指数 月度收益率对比分析")
    print("=" * 100)

    # 获取数据
    index_monthly = get_index_monthly_returns()
    strategy_monthly = load_or_compute_monthly_returns()

    # 打印对比结果
    print_monthly_comparison(strategy_monthly, index_monthly)
    print_summary_statistics(strategy_monthly, index_monthly)

    # 保存对比结果
    print("\n保存月度对比结果...")
    comparison_results = {}
    for key in strategy_monthly.keys():
        comparison_results[key] = {
            'strategy_return': strategy_monthly[key],
            'index_return': index_monthly.get(key, 0),
            'excess_return': strategy_monthly[key] - index_monthly.get(key, 0)
        }

    output_dir = "data/backtest_results"
    os.makedirs(output_dir, exist_ok=True)
    comparison_file = os.path.join(output_dir, "monthly_comparison_2019_2025.json")

    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_results, f, ensure_ascii=False, indent=2)

    print(f"月度对比结果已保存: {comparison_file}")
    print("\n分析完成！")


if __name__ == "__main__":
    main()
