# -*- coding: utf-8 -*-
"""
全量回测脚本 - 涨停回撤策略
回测期间: 2015-2025
"""

import sys
from pathlib import Path
import pickle
import pandas as pd
from datetime import datetime
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))

from src.backtest.engine import BacktestEngine
from src.strategy.limit_up_pullback import LimitUpPullbackStrategy
from settings import CACHE_DIR, DEFAULT_INITIAL_CAPITAL


def load_stock_data(start_year: int, end_year: int):
    """加载股票数据"""
    cache_dir = CACHE_DIR

    print(f"加载数据: {start_year}-{end_year}")

    stock_history = {}

    # 按年加载数据
    for year in range(start_year, end_year + 1):
        files = list(cache_dir.glob(f'stock_hist_*_{year}0101_{year}1231_qfq.pkl'))
        print(f"  {year}年: {len(files)}个文件")

        for f in files:
            try:
                with open(f, 'rb') as file:
                    df = pickle.load(file)
                    if df is not None and not df.empty:
                        # 确保date是datetime类型
                        df['date'] = pd.to_datetime(df['date'])
                        # 重置索引
                        df = df.reset_index(drop=True)

                        # 提取股票代码
                        code = f.stem.split('_')[2]

                        # 合并到历史数据
                        if code not in stock_history:
                            stock_history[code] = df
                        else:
                            stock_history[code] = pd.concat([stock_history[code], df], ignore_index=True)
            except Exception as e:
                pass  # 静默处理加载失败

    print(f"\\n总共加载: {len(stock_history)}只股票")
    return stock_history


def run_full_backtest():
    """运行全量回测"""

    # 回测参数
    start_year = 2015
    end_year = 2025
    start_date = f"{start_year}0101"
    end_date = f"{end_year}1231"

    print("="*80)
    print("全量回测 - 涨停回撤策略")
    print("="*80)
    print(f"回测期间: {start_date} - {end_date}")
    print(f"初始资金: {DEFAULT_INITIAL_CAPITAL:,}元")
    print()

    # 加载数据
    stock_history = load_stock_data(start_year, end_year)

    if not stock_history:
        print("错误: 没有可用的数据")
        return

    # 创建策略
    strategy = LimitUpPullbackStrategy()

    # 创建回测引擎
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=DEFAULT_INITIAL_CAPITAL,
        max_positions=5  # 最多持有5只股票
    )

    # 运行回测
    print("\\n开始回测...")
    print("-"*80)

    def progress_callback(current, total, date_str):
        if current % 50 == 0 or current == total - 1:
            print(f"进度: {current}/{total} ({current/total*100:.1f}%) - {date_str}")

    results = engine.run(
        stock_history=stock_history,
        start_date=start_date,
        end_date=end_date,
        progress_callback=progress_callback
    )

    # 输出结果
    print("\\n" + "="*80)
    print("回测结果")
    print("="*80)
    print(f"总收益率: {results['total_return']:.2f}%")
    print(f"最终资金: {results['final_capital']:,.2f}元")
    print(f"交易次数: {results['total_trades']}")
    print(f"胜率: {results['win_rate']:.2f}%")
    print(f"最大回撤: {results['max_drawdown']:.2f}%")
    print(f"平均盈利: {results['avg_profit']:.2f}%")
    print(f"平均亏损: {results['avg_loss']:.2f}%")

    # 按分类统计
    if results['category_stats']:
        print("\\n按行业统计:")
        print("-"*80)
        for category, stats in results['category_stats'].items():
            print(f"{category}:")
            print(f"  交易次数: {stats['total_trades']}")
            print(f"  胜率: {stats['win_rate']:.1f}%")
            print(f"  平均盈利: {stats['avg_profit']:.1f}%")
            print(f"  平均亏损: {stats['avg_loss']:.1f}%")

    # 保存详细结果
    output_dir = Path('data/backtest_results')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存交易记录
    if not results['trades_df'].empty:
        results['trades_df'].to_csv(output_dir / f'trades_{start_year}_{end_year}.csv', index=False, encoding='utf-8')
        print(f"\\n交易记录已保存: {output_dir}/trades_{start_year}_{end_year}.csv")

    # 保存净值曲线
    if not results['daily_values_df'].empty:
        results['daily_values_df'].to_csv(output_dir / f'daily_values_{start_year}_{end_year}.csv', index=False, encoding='utf-8')
        print(f"净值曲线已保存: {output_dir}/daily_values_{start_year}_{end_year}.csv")

    return results


if __name__ == '__main__':
    run_full_backtest()
