# -*- coding: utf-8 -*-
"""
完整回测脚本 - 涨停回调策略
支持2014-2025全市场数据，剔除ST股票
提供年度、月度、板块、概念分类统计
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from src.strategy.limit_up_pullback import LimitUpPullbackStrategy
from src.backtest.engine import BacktestEngine
from settings import BACKTEST_RESULTS_DIR


def get_stock_categories(all_stocks_df, loader):
    """获取股票分类信息（板块、概念）"""
    print("获取股票分类信息...")

    categories = {}

    # 暂时跳过网络请求，直接设置为'其他'
    for i, (_, stock) in enumerate(all_stocks_df.iterrows()):
        code = stock['code']
        categories[code] = {'category': '其他', 'concepts': []}

    # TODO: 以下是原有的网络请求获取分类的代码，暂时注释掉以提高速度
    # # 使用东财概念板块获取分类
    # concepts = [
    #     '人工智能', '新能源车', '半导体', '锂电池', '光伏',
    #     '医药', '白酒', '军工', '券商', '银行',
    #     '房地产', '钢铁', '煤炭', '有色金属', '石油',
    #     '电力', '公用事业', '传媒', '计算机', '通信',
    #     '电子', '汽车', '化工', '机械', '建筑'
    # ]
    #
    # concept_to_category = {
    #     '人工智能': '科技',
    #     '半导体': '科技',
    #     '计算机': '科技',
    #     '通信': '科技',
    #     '电子': '科技',
    #     '新能源车': '新能源',
    #     '锂电池': '新能源',
    #     '光伏': '新能源',
    #     '电力': '新能源',
    #     '医药': '消费',
    #     '白酒': '消费',
    #     '汽车': '消费',
    #     '军工': '国防',
    #     '券商': '金融',
    #     '银行': '金融',
    #     '房地产': '地产',
    #     '钢铁': '周期',
    #     '煤炭': '周期',
    #     '有色金属': '周期',
    #     '石油': '周期',
    #     '化工': '周期',
    #     '机械': '工业',
    #     '建筑': '工业',
    #     '传媒': '传媒',
    # }
    #
    # for i, (_, stock) in enumerate(all_stocks_df.iterrows()):
    #     code = stock['code']
    #     categories[code] = {'category': '其他', 'concepts': []}
    #
    # # 获取每个概念的成分股
    # for concept in concepts:
    #     try:
    #         cons = loader.get_sector_stocks(concept)
    #         category = concept_to_category.get(concept, '其他')
    #
    #         for code in cons:
    #             if code in categories:
    #                 if categories[code]['category'] == '其他':
    #                     categories[code]['category'] = category
    #                 categories[code]['concepts'].append(concept)
    #     except Exception:
    #         pass

    print(f"    分类完成: {len(categories)} 只股票")
    return categories


def run_full_backtest(
    start_year: int = 2014,
    end_year: int = 2025,
    filter_st: bool = True,
    use_cache: bool = True
):
    """
    运行完整回测

    Args:
        start_year: 开始年份
        end_year: 结束年份
        filter_st: 是否过滤ST股票
        use_cache: 是否使用缓存
    """
    print("=" * 80)
    print(f"完整回测 - 涨停回调策略 ({start_year}-{end_year}, 剔除ST)")
    print("=" * 80)

    # 1. 准备年度列表
    years = []
    for year in range(start_year, end_year + 1):
        years.append((str(year), f"{year}0101", f"{year}1231"))

    # 2. 加载数据
    print(f"\n[1] 加载股票数据...")
    loader = StockLoader()

    # 获取股票列表
    all_stocks = loader.get_stock_list()
    print(f"    总股票数: {len(all_stocks)}")

    # 过滤ST股票
    if filter_st:
        all_stocks = loader.filter_st_stocks(all_stocks)
        print(f"    剔除ST后: {len(all_stocks)}")

    # 获取股票分类
    stock_categories = get_stock_categories(all_stocks, loader)

    # 3. 加载历史数据（多加载一年用于计算指标）
    print(f"\n[2] 加载历史数据...")
    data_start_date = f"{start_year - 1}0101"
    data_end_date = f"{end_year}1231"

    stock_history = loader.load_multiple_stocks(
        stock_list=all_stocks,
        start_date=data_start_date,
        end_date=data_end_date,
        max_stocks=None,  # 全部股票
        progress_callback=lambda i, total, code: None
    )

    print(f"    成功加载: {len(stock_history)} 只股票")

    # 4. 准备分类信息（只包含有历史数据的股票）
    filtered_categories = {}
    for code in stock_history.keys():
        if code in stock_categories:
            filtered_categories[code] = stock_categories[code]

    # 5. 按年度回测 - 每年独立运行，初始资本10万
    print(f"\n[3] 按年度回测...")
    yearly_results = {}

    for year_name, year_start, year_end in years:
        print(f"\n{'='*70}")
        print(f"回测年度: {year_name}")
        print(f"{'='*70}")

        # 每年独立运行，初始资本都是10万
        initial_capital = 100000
        strategy = LimitUpPullbackStrategy()
        engine = BacktestEngine(strategy, initial_capital=initial_capital)

        # 添加进度回调
        def progress_callback(current, total, date):
            if current % 50 == 0 or current == total - 1:
                print(f"  进度: {current}/{total} ({current/total*100:.1f}%) - 日期: {date}")
            sys.stdout.flush()

        results = engine.run(
            stock_history=stock_history,
            start_date=year_start,
            end_date=year_end,
            stock_categories=filtered_categories,
            progress_callback=progress_callback
        )

        yearly_results[year_name] = results

        print(f"\n{year_name}年度结果:")
        print(f"  初始资本: {initial_capital:,.0f} 元")
        print(f"  最终资本: {results['final_capital']:,.0f} 元")
        print(f"  收益率: {results['total_return']:.2f}%")
        print(f"  交易次数: {results['total_trades']}")
        print(f"  胜率: {results['win_rate']:.2f}%")
        print(f"  最大回撤: {results['max_drawdown']:.2f}%")

    # 6. 生成详细统计报告
    print(f"\n[4] 生成统计报告...")

    # 汇总年度统计
    print(f"\n{'='*80}")
    print("年度回测汇总 (每年独立运行10万本金)")
    print(f"{'='*80}")
    print(f"{'年度':<8} {'初始资本':>12} {'最终资本':>12} {'收益率':>10} {'交易次数':>10} {'胜率':>10} {'最大回撤':>12}")
    print(f"{'-'*80}")

    # 计算平均收益率
    avg_return = 0
    profitable_years = 0
    total_years = len(years)

    for year_name, _, _ in years:
        r = yearly_results[year_name]
        print(f"{year_name:<8} {100000:>10,.0f}  {r['final_capital']:>10,.0f}  {r['total_return']:>8.2f}%     {r['total_trades']:>10} {r['win_rate']:>9.1f}%   {r['max_drawdown']:>10.2f}%")
        avg_return += r['total_return']
        if r['total_return'] > 0:
            profitable_years += 1

    avg_return = avg_return / total_years
    print(f"{'-'*80}")
    print(f"{'平均':<8} {'':>12} {'':>12} {avg_return:>8.2f}%")
    print(f"盈利年份: {profitable_years}/{total_years} ({profitable_years/total_years*100:.1f}%)")

    # 按板块/概念统计
    print(f"\n{'='*80}")
    print("按板块/概念统计")
    print(f"{'='*80}")

    category_summary = defaultdict(lambda: {
        'trades': [],
        'returns': [],
        'win_rates': []
    })

    for year_name, results in yearly_results.items():
        for cat, stats in results.get('category_stats', {}).items():
            if stats['total_trades'] > 0:
                category_summary[cat]['trades'].append(stats['total_trades'])
                category_summary[cat]['returns'].append(stats['total_return'])
                category_summary[cat]['win_rates'].append(stats['win_rate'])

    # 打印交易次数最多的前15个板块
    top_categories = sorted(
        category_summary.items(),
        key=lambda x: sum(x[1]['trades']),
        reverse=True
    )[:15]

    print(f"\n{'板块/概念':<20} {'总交易次数':>12} {'平均胜率':>12} {'总收益':>12}")
    print(f"{'-'*60}")

    for cat, data in top_categories:
        total_trades = sum(data['trades'])
        avg_win_rate = sum(data['win_rates']) / len(data['win_rates']) if data['win_rates'] else 0
        total_return = sum(data['returns']) if data['returns'] else 0
        print(f"{cat:<20} {total_trades:>10}   {avg_win_rate:>10.1f}%   {total_return:>10.2f}%")

    # 7. 保存结果
    print(f"\n[5] 保存结果...")
    BACKTEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 保存年度汇总
    summary = {
        'backtest_mode': 'independent_yearly',  # 每年独立运行
        'backtest_period': f'{start_year}-01-01 to {end_year}-12-31',
        'stocks_tested': len(stock_history),
        'yearly_initial_capital': 100000,
        'average_return': avg_return,
        'profitable_years': profitable_years,
        'total_years': total_years,
        'years': {}
    }

    for year_name, results in yearly_results.items():
        year_data = {
            'initial_capital': 100000,  # 每年都是10万
            'final_capital': results['final_capital'],
            'total_return': results['total_return'],
            'total_trades': results['total_trades'],
            'win_rate': results['win_rate'],
            'max_drawdown': results['max_drawdown'],
        }

        # 添加板块统计信息
        if 'category_stats' in results and results['category_stats']:
            year_data['category_stats'] = results['category_stats']

        # 保存详细交易记录（用于后续按板块统计）
        if 'trades_df' in results and not results['trades_df'].empty:
            # 只保存关键字段
            trades_df = results['trades_df'][['date', 'code', 'name', 'action', 'price', 'profit_pct', 'category']]
            year_data['trades'] = trades_df.to_dict('records')

        summary['years'][year_name] = year_data

    summary_file = BACKTEST_RESULTS_DIR / f"full_backtest_{start_year}_{end_year}_{timestamp}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"    结果已保存: {summary_file}")

    print(f"\n{'='*80}")
    print("回测完成！")
    print(f"{'='*80}")

    return yearly_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="完整回测 - 涨停回调策略")
    parser.add_argument("--start-year", type=int, default=2014, help="开始年份")
    parser.add_argument("--end-year", type=int, default=2025, help="结束年份")
    parser.add_argument("--no-filter-st", action="store_true", help="不过滤ST股票")
    parser.add_argument("--no-cache", action="store_true", help="不使用缓存")

    args = parser.parse_args()

    run_full_backtest(
        start_year=args.start_year,
        end_year=args.end_year,
        filter_st=not args.no_filter_st,
        use_cache=not args.no_cache
    )
