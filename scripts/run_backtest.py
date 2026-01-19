# -*- coding: utf-8 -*-
"""
回测运行脚本 - 使用新的模块化架构
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from src.strategy.limit_up_pullback import LimitUpPullbackStrategy
from src.backtest.engine import BacktestEngine
from settings import BACKTEST_RESULTS_DIR


def run_backtest(
    start_date: str = "20250101",
    end_date: str = "20251231",
    max_stocks: int = None,
    filter_st: bool = True
):
    """
    运行回测

    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        max_stocks: 最大股票数量（None表示全部）
        filter_st: 是否过滤ST股票
    """
    print("=" * 70)
    print(f"涨停回调策略回测 ({start_date} - {end_date})")
    print("=" * 70)

    # 1. 加载数据
    print("\n[1] 加载股票数据...")
    loader = StockLoader()

    # 获取股票列表
    all_stocks = loader.get_stock_list()
    print(f"    总股票数: {len(all_stocks)}")

    # 过滤ST股票
    if filter_st:
        all_stocks = loader.filter_st_stocks(all_stocks)
        print(f"    剔除ST后: {len(all_stocks)}")

    # 加载历史数据
    print(f"\n[2] 加载历史数据...")
    stock_history = loader.load_multiple_stocks(
        stock_list=all_stocks,
        start_date="20240101",  # 多加载一年用于计算指标
        end_date=end_date,
        max_stocks=max_stocks,
        progress_callback=lambda i, total, code: print(f"    进度: {i}/{total}") if i % 500 == 0 else None
    )
    print(f"    成功加载: {len(stock_history)} 只股票")

    # 2. 创建策略和回测引擎
    print(f"\n[3] 运行回测...")
    strategy = LimitUpPullbackStrategy()
    engine = BacktestEngine(strategy, initial_capital=100000)

    # 3. 执行回测
    results = engine.run(
        stock_history=stock_history,
        start_date=start_date,
        end_date=end_date,
        progress_callback=lambda i, total, date: None
    )

    # 4. 输出结果
    print(f"\n{'='*70}")
    print("回测结果")
    print(f"{'='*70}")
    print(f"  初始资金: {100000:,.2f} 元")
    print(f"  最终资金: {results['final_capital']:,.2f} 元")
    print(f"  收益率: {results['total_return']:.2f}%")
    print(f"  交易次数: {results['total_trades']}")
    print(f"  胜率: {results['win_rate']:.2f}%")
    print(f"  最大回撤: {results['max_drawdown']:.2f}%")
    print(f"  平均盈利: {results['avg_profit']:.2f}%")
    print(f"  平均亏损: {results['avg_loss']:.2f}%")

    # 5. 保存结果
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = BACKTEST_RESULTS_DIR / f"backtest_{start_date}_{end_date}_{timestamp}.json"

    summary = {
        'strategy': strategy.get_info(),
        'period': {'start': start_date, 'end': end_date},
        'stocks_tested': len(stock_history),
        'results': {
            'initial_capital': 100000,
            'final_capital': results['final_capital'],
            'total_return': results['total_return'],
            'total_trades': results['total_trades'],
            'win_rate': results['win_rate'],
            'max_drawdown': results['max_drawdown'],
            'avg_profit': results['avg_profit'],
            'avg_loss': results['avg_loss'],
        },
        'category_stats': results['category_stats']
    }

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_file}")

    return results


def run_multi_year_backtest(
    years: list = None,
    max_stocks: int = None,
    filter_st: bool = True
):
    """
    运行多年度回测

    Args:
        years: 年度列表 [(year_name, start, end), ...]
        max_stocks: 最大股票数量
        filter_st: 是否过滤ST股票
    """
    if years is None:
        years = [
            ('2023', '20230101', '20231231'),
            ('2024', '20240101', '20241231'),
            ('2025', '20250101', '20251231'),
        ]

    print("=" * 70)
    print(f"多年度回测 - 涨停回调策略")
    print("=" * 70)

    # 1. 加载数据（一次性加载所有年份的数据）
    print("\n[1] 加载股票数据...")
    loader = StockLoader()

    all_stocks = loader.get_stock_list()
    print(f"    总股票数: {len(all_stocks)}")

    if filter_st:
        all_stocks = loader.filter_st_stocks(all_stocks)
        print(f"    剔除ST后: {len(all_stocks)}")

    # 计算日期范围
    start_date = years[0][1]
    end_date = years[-1][2]

    print(f"\n[2] 加载历史数据 ({start_date} - {end_date})...")
    stock_history = loader.load_multiple_stocks(
        stock_list=all_stocks,
        start_date="20220101",  # 多加载一年用于计算指标
        end_date=end_date,
        max_stocks=max_stocks,
        progress_callback=lambda i, total, code: print(f"    进度: {i}/{total}") if i % 500 == 0 else None
    )
    print(f"    成功加载: {len(stock_history)} 只股票")

    # 2. 按年度回测
    print(f"\n[3] 按年度回测...")
    yearly_results = {}
    current_cash = 100000

    for year_name, year_start, year_end in years:
        print(f"\n{'-'*50}")
        print(f"回测年度: {year_name}")
        print(f"{'-'*50}")

        strategy = LimitUpPullbackStrategy()
        engine = BacktestEngine(strategy, initial_capital=current_cash)

        results = engine.run(
            stock_history=stock_history,
            start_date=year_start,
            end_date=year_end
        )

        current_cash = results['final_capital']
        yearly_results[year_name] = results

        print(f"\n{year_name}年度结果:")
        print(f"  收益率: {results['total_return']:.2f}%")
        print(f"  交易次数: {results['total_trades']}")
        print(f"  胜率: {results['win_rate']:.2f}%")
        print(f"  最大回撤: {results['max_drawdown']:.2f}%")

    # 3. 汇总结果
    print(f"\n{'='*70}")
    print("年度回测汇总")
    print(f"{'='*70}")
    print(f"{'年度':<8} {'收益率':>12} {'交易次数':>10} {'胜率':>10} {'最大回撤':>12}")
    print(f"{'-'*70}")

    for year_name, _, _ in years:
        r = yearly_results[year_name]
        print(f"{year_name:<8} {r['total_return']:>10.2f}%     {r['total_trades']:>10} {r['win_rate']:>9.1f}%   {r['max_drawdown']:>10.2f}%")

    total_return = (current_cash - 100000) / 100000 * 100
    print(f"{'-'*70}")
    print(f"{'总计':<8} {total_return:>10.2f}%")

    # 4. 保存结果
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = BACKTEST_RESULTS_DIR / f"multi_year_backtest_{timestamp}.json"

    summary = {
        'backtest_period': f"{years[0][0]}-{years[-1][0]}",
        'stocks_tested': len(stock_history),
        'initial_capital': 100000,
        'final_capital': current_cash,
        'total_return': total_return,
        'years': {}
    }

    for year_name, results in yearly_results.items():
        summary['years'][year_name] = {
            'initial_capital': results['trades_df'].empty and 100000 or 100000,  # 简化
            'final_capital': results['final_capital'],
            'total_return': results['total_return'],
            'total_trades': results['total_trades'],
            'win_rate': results['win_rate'],
            'max_drawdown': results['max_drawdown'],
        }

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_file}")

    return yearly_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="涨停回调策略回测")
    parser.add_argument("--start", type=str, default="20250101", help="开始日期 (YYYYMMDD)")
    parser.add_argument("--end", type=str, default="20251231", help="结束日期 (YYYYMMDD)")
    parser.add_argument("--max-stocks", type=int, default=None, help="最大股票数量")
    parser.add_argument("--multi-year", action="store_true", help="运行多年度回测")
    parser.add_argument("--no-filter-st", action="store_true", help="不过滤ST股票")

    args = parser.parse_args()

    if args.multi_year:
        run_multi_year_backtest(
            max_stocks=args.max_stocks,
            filter_st=not args.no_filter_st
        )
    else:
        run_backtest(
            start_date=args.start,
            end_date=args.end,
            max_stocks=args.max_stocks,
            filter_st=not args.no_filter_st
        )
