# -*- coding: utf-8 -*-
"""
从回测结果中按板块统计
"""

import sys
import os
from pathlib import Path
import json
import pandas as pd
import time
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from settings import BACKTEST_RESULTS_DIR


def analyze_results_by_sector(result_file: str):
    """
    从回测结果文件中按板块统计
    """
    print(f"{'='*80}")
    print(f"按板块统计回测结果")
    print(f"{'='*80}")

    # 读取结果文件
    print(f"\n[1] 读取回测结果: {result_file}")
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 检查是否有交易记录
    has_trades = False
    for year, year_data in data['years'].items():
        if 'trades' in year_data and year_data['trades']:
            has_trades = True
            break

    if not has_trades:
        print("    该结果文件中没有交易记录")
        print("    需要重新运行回测并保存交易记录")
        return

    print(f"    找到交易记录")

    # 提取所有交易
    print(f"\n[2] 提取交易记录...")
    all_trades = []
    for year, year_data in data['years'].items():
        if 'trades' in year_data:
            for trade in year_data['trades']:
                trade['year'] = year
                all_trades.append(trade)

    print(f"    总交易数: {len(all_trades)}")

    # 获取行业分类
    print(f"\n[3] 获取股票行业分类...")

    loader = StockLoader()

    # 获取每只交易股票的行业 - 使用更高效的API
    stock_to_industry = {}
    traded_codes = sorted(set(t['code'] for t in all_trades))  # 排序保证可重复性

    print(f"    查询 {len(traded_codes)} 只股票的行业...")
    print(f"    使用 stock_individual_info_em API 直接获取...")

    from akshare import stock_individual_info_em

    for i, stock_code in enumerate(traded_codes):
        try:
            # 直接获取股票信息，包含行业字段
            info_df = stock_individual_info_em(symbol=stock_code, timeout=5)

            # 提取行业信息（在第7行，索引为7）
            industry_row = info_df[info_df['item'] == '行业']
            if not industry_row.empty:
                industry = industry_row.iloc[0]['value']
                stock_to_industry[stock_code] = industry
            else:
                stock_to_industry[stock_code] = '其他'

        except Exception as e:
            stock_to_industry[stock_code] = '其他'

        # 打印进度
        if (i + 1) % 50 == 0:
            classified = len([s for s in stock_to_industry.values() if s != '其他'])
            print(f"      进度: {i+1}/{len(traded_codes)} (已分类: {classified})")

        # 短暂延迟避免API限流
        time.sleep(0.1)

    classified = len([s for s in stock_to_industry.values() if s != '其他'])
    print(f"    完成: 已分类 {len(stock_to_industry)} 只股票 (非其他: {classified})")

    # 更新交易记录中的行业
    for trade in all_trades:
        trade['industry'] = stock_to_industry.get(trade['code'], '其他')

    # 按行业和年度统计
    print(f"\n[4] 按行业统计...")

    # 行业×年度统计
    industry_year_stats = defaultdict(lambda: {
        'buy_trades': 0,
        'sell_trades': 0,
        'total_profit': 0,
        'trades': []
    })

    for trade in all_trades:
        key = (trade['industry'], trade['year'])
        industry_year_stats[key]['trades'].append(trade)

    # 计算统计数据
    print(f"\n{'='*80}")
    print("行业板块年度表现")
    print(f"{'='*80}")

    # 获取所有年份
    years = sorted(set(t['year'] for t in all_trades))

    # 获取所有行业
    industries = sorted(set(t['industry'] for t in all_trades))

    # 打印表格
    print(f"\n{'行业板块':<15} ", end="")
    for year in years:
        print(f"{year:>10} ", end="")
    print("平均")

    print(f"{'-'*80}")

    for industry in industries:
        print(f"{industry:<15} ", end="")
        year_profits = []

        for year in years:
            key = (industry, year)
            if key in industry_year_stats and industry_year_stats[key]['trades']:
                trades = industry_year_stats[key]['trades']
                # 计算该行业该年度的总收益
                sell_trades = [t for t in trades if t['action'] == 'sell']
                if sell_trades:
                    total_profit = sum(t['profit_pct'] for t in sell_trades)
                    print(f"{total_profit:>9.2f}% ", end="")
                    year_profits.append(total_profit)
                else:
                    print(f"{'--':>9} ", end="")
                    year_profits.append(0)
            else:
                print(f"{'--':>9} ", end="")
                year_profits.append(0)

        avg = sum(year_profits) / len(year_profits) if year_profits else 0
        print(f"{avg:>9.2f}%")

    # 按行业汇总
    print(f"\n{'='*80}")
    print("行业板块汇总")
    print(f"{'='*80}")

    industry_summary = []
    for industry in industries:
        all_industry_trades = [t for t in all_trades if t['industry'] == industry]
        sell_trades = [t for t in all_industry_trades if t['action'] == 'sell']

        if not sell_trades:
            continue

        total_profit = sum(t['profit_pct'] for t in sell_trades)
        avg_profit = total_profit / len(sell_trades)
        win_trades = len([t for t in sell_trades if t['profit_pct'] > 0])

        industry_summary.append({
            'industry': industry,
            'total_trades': len(sell_trades),
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'win_trades': win_trades,
            'win_rate': win_trades / len(sell_trades) * 100
        })

    # 按总收益率排序
    industry_summary.sort(key=lambda x: x['total_profit'], reverse=True)

    print(f"\n{'行业板块':<15} {'交易次数':>10} {'总收益':>12} {'平均收益':>12} {'胜率':>10}")
    print(f"{'-'*70}")

    for s in industry_summary:
        print(f"{s['industry']:<15} {s['total_trades']:>10} {s['total_profit']:>10.2f}% "
              f"{s['avg_profit']:>10.2f}% {s['win_rate']:>9.1f}%")

    # 保存结果
    print(f"\n[5] 保存结果...")

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存行业统计
    summary_file = BACKTEST_RESULTS_DIR / f"sector_stats_{timestamp}.csv"
    pd.DataFrame(industry_summary).to_csv(summary_file, index=False, encoding='utf-8')
    print(f"    行业汇总: {summary_file}")

    # 保存行业×年度明细
    detail_rows = []
    for (industry, year), stats in industry_year_stats.items():
        sell_trades = [t for t in stats['trades'] if t['action'] == 'sell']
        if sell_trades:
            total_profit = sum(t['profit_pct'] for t in sell_trades)
            detail_rows.append({
                '行业板块': industry,
                '年份': year,
                '交易次数': len(sell_trades),
                '总收益': total_profit
            })

    detail_file = BACKTEST_RESULTS_DIR / f"sector_year_detail_{timestamp}.csv"
    pd.DataFrame(detail_rows).to_csv(detail_file, index=False, encoding='utf-8')
    print(f"    年度明细: {detail_file}")

    print(f"\n{'='*80}")
    print("分析完成！")
    print(f"{'='*80}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="从结果中按板块统计")
    parser.add_argument("--result-file", type=str, required=True, help="回测结果文件路径")

    args = parser.parse_args()

    analyze_results_by_sector(args.result_file)
