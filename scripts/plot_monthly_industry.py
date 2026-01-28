# -*- coding: utf-8 -*-
"""
绘制行业×月份的策略表现与行业整体涨跌幅对比
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
import urllib.request
from datetime import datetime
from collections import defaultdict

sys.path.append(str(Path(__file__).parent.parent))

from settings import BACKTEST_RESULTS_DIR

# ========== 字体设置 ==========
font_dir = Path.home() / '.matplotlib_fonts'
font_dir.mkdir(exist_ok=True)

font_url = 'https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf'
font_path = font_dir / 'SimHei.ttf'

if not font_path.exists():
    print(f"下载中文字体...")
    try:
        urllib.request.urlretrieve(font_url, font_path)
        print(f"字体已下载: {font_path}")
    except Exception as e:
        print(f"下载失败: {e}")

import matplotlib.font_manager as fm
fm.fontManager.addfont(str(font_path))

import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

import matplotlib.pyplot as plt
import seaborn as sns
from src.data.stock_loader import StockLoader

sns.set_style("whitegrid")


def get_industry_monthly_returns(industry_name, traded_stocks, months, loader):
    """
    获取行业在每个月的平均涨跌幅
    使用回测中交易过的股票来计算行业平均
    """
    import time

    monthly_returns = {}

    # 筛选出该行业的股票
    industry_stocks = [s for s in traded_stocks if s.get('industry') == industry_name]

    if not industry_stocks:
        print(f"    ✗ {industry_name} 没有交易过的股票")
        for month in months:
            monthly_returns[month] = 0
        return monthly_returns

    print(f"    使用{len(industry_stocks)}只交易过的股票计算行业平均")

    # 计算每个月的平均涨跌幅
    successful_months = 0
    for year_month in months:
        year = year_month[:4]
        month = year_month[4:6]

        # 计算该月的起始和结束日期
        if month == "01":
            start_date = year_month + "01"
            end_date = year + "0131"
        elif month == "02":
            start_date = year_month + "01"
            end_date = year + "0228"
        elif month in ["04", "06", "09", "11"]:
            start_date = year_month + "01"
            end_date = year + month + "30"
        else:
            start_date = year_month + "01"
            end_date = year + month + "31"

        # 收集该月所有股票的涨跌幅
        stock_returns = []
        for stock in industry_stocks:
            code = stock['code']
            try:
                df = loader.get_stock_history(code, start_date, end_date)
                if df is not None and not df.empty and len(df) >= 2:
                    start_price = df.iloc[0]['close']
                    end_price = df.iloc[-1]['close']
                    ret = (end_price - start_price) / start_price * 100
                    stock_returns.append(ret)
            except Exception as e:
                continue

        if stock_returns:
            monthly_returns[year_month] = np.mean(stock_returns)
            successful_months += 1
        else:
            monthly_returns[year_month] = 0

    print(f"    成功获取{successful_months}/{len(months)}个月的数据")
    return monthly_returns


def plot_monthly_industry_comparison(result_file: str, top_n=20):
    """
    绘制行业×月份的策略表现与行业整体对比
    """
    print(f"读取回测结果: {result_file}")

    # 读取数据
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取交易记录
    all_trades = []
    for year, year_data in data['years'].items():
        if 'trades' in year_data:
            for trade in year_data['trades']:
                trade['year'] = year
                all_trades.append(trade)

    print(f"总交易数: {len(all_trades)}")

    # 获取行业分类
    from akshare import stock_individual_info_em
    import time

    traded_codes = sorted(set(t['code'] for t in all_trades))
    stock_to_industry = {}

    print(f"获取股票行业分类...")
    for i, stock_code in enumerate(traded_codes):
        try:
            info_df = stock_individual_info_em(symbol=stock_code, timeout=5)
            industry_row = info_df[info_df['item'] == '行业']
            if not industry_row.empty:
                stock_to_industry[stock_code] = industry_row.iloc[0]['value']
            else:
                stock_to_industry[stock_code] = '其他'
        except:
            stock_to_industry[stock_code] = '其他'

        if (i + 1) % 50 == 0:
            print(f"  进度: {i+1}/{len(traded_codes)}")
        time.sleep(0.05)

    # 更新交易记录
    for trade in all_trades:
        trade['industry'] = stock_to_industry.get(trade['code'], '其他')

    # 创建DataFrame
    df = pd.DataFrame(all_trades)

    # 只保留卖出交易
    sell_df = df[df['action'] == 'sell'].copy()

    # 提取月份
    sell_df['month'] = sell_df['date'].apply(lambda x: x[:6])  # YYYYMM

    # 按行业×月份统计策略收益
    industry_month_profit = sell_df.groupby(['industry', 'month'])['profit_pct'].sum().reset_index()

    # 统计每个行业的总交易次数
    industry_total_count = sell_df.groupby('industry').size().reset_index(name='total_count')

    # 选择交易次数最多的top_n个行业（总交易次数>=5）
    qualified_industries = industry_total_count[industry_total_count['total_count'] >= 5]
    top_industries = qualified_industries.nlargest(top_n, 'total_count')['industry'].tolist()

    print(f"\n选择交易最频繁的{len(top_industries)}个行业:")
    for ind in top_industries[:5]:
        count = industry_total_count[industry_total_count['industry'] == ind]['total_count'].values[0]
        print(f"  - {ind}: {count}笔交易")

    # 过滤数据
    industry_month_profit = industry_month_profit[industry_month_profit['industry'].isin(top_industries)]

    # 获取所有月份
    all_months = sorted(set(sell_df['month'].unique()))
    print(f"时间范围: {all_months[0]} ~ {all_months[-1]}")

    # 构建完整的月份序列
    loader = StockLoader()

    # 为每个行业创建完整的时间序列
    industry_data = {}

    print(f"\n获取行业整体涨跌幅（这可能需要几分钟）...")

    for idx, industry in enumerate(top_industries):
        print(f"  [{idx+1}/{len(top_industries)}] {industry}...")

        # 策略月度收益
        strategy_returns = {}
        industry_df = industry_month_profit[industry_month_profit['industry'] == industry]
        for _, row in industry_df.iterrows():
            strategy_returns[row['month']] = row['profit_pct']

        # 填充缺失月份为0
        for month in all_months:
            if month not in strategy_returns:
                strategy_returns[month] = 0

        # 获取行业整体涨跌幅（使用交易过的股票计算）
        industry_returns = get_industry_monthly_returns(industry, all_trades, all_months, loader)

        # 填充缺失的行业数据
        for month in all_months:
            if month not in industry_returns:
                # 尝试使用相邻月份或设为0
                industry_returns[month] = 0

        industry_data[industry] = {
            'strategy': strategy_returns,
            'industry': industry_returns
        }

    # 创建图表 - 每个行业一行，有两个子图
    n_industries = len(top_industries)
    n_cols = 2
    n_rows = (n_industries + 1) // 2

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 4 * n_rows))
    if n_rows == 1:
        axes = axes.reshape(1, -1)
    axes = axes.flatten()

    for idx, industry in enumerate(top_industries):
        ax = axes[idx]

        data = industry_data[industry]
        x = range(len(all_months))

        # 策略收益
        strategy_values = [data['strategy'][m] for m in all_months]
        # 累计策略收益
        strategy_cumsum = np.cumsum(strategy_values)
        # 行业整体收益
        industry_values = [data['industry'][m] for m in all_months]
        # 累计行业收益
        industry_cumsum = np.cumsum(industry_values)

        # 绘制月度收益对比（柱状图）
        x_pos = np.arange(len(all_months))
        width = 0.35

        bars1 = ax.bar(x_pos - width/2, strategy_values, width, label='策略月收益', color='#2ecc59', alpha=0.7)
        bars2 = ax.bar(x_pos + width/2, industry_values, width, label='行业月收益', color='#3498db', alpha=0.7)

        # 绘制累计收益对比（折线图）
        ax2 = ax.twinx()
        line1 = ax2.plot(x, strategy_cumsum, marker='o', linewidth=2, label='策略累计', color='#27ae60', markersize=3)
        line2 = ax2.plot(x, industry_cumsum, marker='s', linewidth=2, label='行业累计', color='#2980b9', markersize=3)

        # 零线
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)

        # 计算统计信息
        total_strategy = strategy_cumsum[-1] if len(strategy_cumsum) > 0 else 0
        total_industry = industry_cumsum[-1] if len(industry_cumsum) > 0 else 0
        win_months = sum(1 for s, i in zip(strategy_values, industry_values) if s > i)
        excess_return = total_strategy - total_industry

        # 标题
        title = f'{industry}\n'
        title += f'策略总计:{total_strategy:.1f}% 行业总计:{total_industry:.1f}% 超额:{excess_return:.1f}%\n'
        title += f'跑赢月份:{win_months}/{len(all_months)}'
        ax.set_title(title, fontsize=10, fontweight='bold', fontfamily='SimHei')

        # X轴 - 每年显示一个标记
        year_ticks = []
        year_labels = []
        for i, month in enumerate(all_months):
            if month.endswith('01'):  # 每年1月
                year_ticks.append(i)
                year_labels.append(month[:4])

        ax.set_xticks(year_ticks)
        ax.set_xticklabels(year_labels, fontfamily='SimHei', fontsize=8)

        # Y轴标签
        ax.set_ylabel('月收益(%)', fontfamily='SimHei', fontsize=9)
        ax2.set_ylabel('累计收益(%)', fontfamily='SimHei', fontsize=9)

        # 图例
        bars = [bars1, bars2]
        lines = line1 + line2
        labels = [b.get_label() for b in bars] + [l.get_label() for l in lines]
        ax.legend(bars + lines, labels, loc='upper left', fontsize=7, prop={'family': 'SimHei'})

        ax.grid(True, alpha=0.3, axis='y')

    # 隐藏多余的子图
    for idx in range(len(top_industries), len(axes)):
        axes[idx].axis('off')

    plt.suptitle(f'行业策略表现 vs 行业整体表现对比 ({all_months[0][:4]}-{all_months[-1][:4]})',
                fontsize=14, fontweight='bold', fontfamily='SimHei', y=0.995)

    plt.tight_layout()

    # 保存图表
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = BACKTEST_RESULTS_DIR / f"industry_vs_benchmark_{timestamp}.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n图表已保存: {output_file}")

    # 生成分析报告
    print(f"\n{'='*80}")
    print("行业策略 vs 行业整体分析报告")
    print(f"{'='*80}")

    analysis = []
    for industry in top_industries:
        data = industry_data[industry]
        strategy_values = [data['strategy'][m] for m in all_months]
        industry_values = [data['industry'][m] for m in all_months]

        strategy_total = np.sum(strategy_values)
        industry_total = np.sum(industry_values)
        excess = strategy_total - industry_total

        # 跑赢行业指数的月份数
        win_months = sum(1 for s, i in zip(strategy_values, industry_values) if s > i)
        win_rate = win_months / len(all_months) * 100

        # 策略月度胜率（盈利月份）
        profit_months = sum(1 for s in strategy_values if s > 0)
        profit_rate = profit_months / len(all_months) * 100

        # 评级
        if excess > 50 and win_rate >= 60:
            rating = '⭐⭐⭐ 显著超额'
        elif excess > 20 and win_rate >= 50:
            rating = '⭐⭐ 稳定超额'
        elif excess > 0:
            rating = '⭐ 轻微超额'
        elif excess > -20:
            rating = '~ 接近指数'
        elif excess > -50:
            rating = '✗ 略逊于指数'
        else:
            rating = '✗✗ 显著跑输'

        analysis.append({
            'industry': industry,
            'strategy_total': strategy_total,
            'industry_total': industry_total,
            'excess_return': excess,
            'win_rate_vs_index': win_rate,
            'profit_rate': profit_rate,
            'rating': rating
        })

    analysis_df = pd.DataFrame(analysis)
    analysis_df = analysis_df.sort_values('excess_return', ascending=False)

    print(f"\n{'行业板块':<15} {'策略总计':>10} {'行业总计':>10} {'超额收益':>10} {'跑赢月份':>10} {'评级':<12}")
    print(f"{'-'*80}")
    for _, row in analysis_df.iterrows():
        print(f"{row['industry']:<15} {row['strategy_total']:>9.1f}% "
              f"{row['industry_total']:>9.1f}% {row['excess_return']:>9.1f}% "
              f"{row['win_rate_vs_index']:>9.1f}% {row['rating']:<12}")

    # 保存分析报告
    report_file = BACKTEST_RESULTS_DIR / f"industry_vs_benchmark_report_{timestamp}.csv"
    analysis_df.to_csv(report_file, index=False, encoding='utf-8')
    print(f"\n分析报告已保存: {report_file}")

    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="绘制行业×月份对比分析图表")
    parser.add_argument("--result-file", type=str,
                       default="data/backtest_results/full_backtest_2023_2025_20260121_093915.json",
                       help="回测结果文件路径")
    parser.add_argument("--top-n", type=int, default=20,
                       help="显示交易最频繁的N个行业")

    args = parser.parse_args()

    plot_monthly_industry_comparison(args.result_file, args.top_n)
