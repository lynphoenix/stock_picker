# -*- coding: utf-8 -*-
"""
绘制回测结果的可视化图表
"""

import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
import urllib.request

sys.path.append(str(Path(__file__).parent.parent))

from settings import BACKTEST_RESULTS_DIR

# ========== 字体设置 ==========
# 字体缓存目录
font_dir = Path.home() / '.matplotlib_fonts'
font_dir.mkdir(exist_ok=True)

# 下载中文字体（SimHei黑体）
font_url = 'https://github.com/StellarCN/scp_zh/raw/master/fonts/SimHei.ttf'
font_path = font_dir / 'SimHei.ttf'

if not font_path.exists():
    print(f"下载中文字体...")
    try:
        urllib.request.urlretrieve(font_url, font_path)
        print(f"字体已下载: {font_path}")
    except Exception as e:
        print(f"下载失败: {e}")

# 导入matplotlib并设置字体
import matplotlib.font_manager as fm
fm.fontManager.addfont(str(font_path))

import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

import matplotlib.pyplot as plt
import seaborn as sns

# 设置样式
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)


def plot_sector_analysis(result_file: str):
    """
    绘制行业板块分析图表
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

    # 只保留卖出交易（计算收益）
    sell_df = df[df['action'] == 'sell'].copy()

    # 按行业和年度分组统计
    industry_year = sell_df.groupby(['industry', 'year'])['profit_pct'].sum().reset_index()
    industry_year_counts = sell_df.groupby(['industry', 'year']).size().reset_index(name='trades')

    # 创建透视表
    pivot_profit = industry_year.pivot(index='industry', columns='year', values='profit_pct').fillna(0)
    pivot_counts = industry_year_counts.pivot(index='industry', columns='year', values='trades').fillna(0)

    # 只保留交易次数>=3的行业
    valid_industries = pivot_counts.sum(axis=1) >= 3
    pivot_profit = pivot_profit[valid_industries]
    pivot_counts = pivot_counts[valid_industries]

    # 按总收益排序
    pivot_profit['总收益'] = pivot_profit.sum(axis=1)
    pivot_profit = pivot_profit.sort_values('总收益', ascending=False)
    pivot_profit = pivot_profit.drop('总收益', axis=1)

    # 过滤：只显示总收益>0或<-10的行业
    pivot_profit = pivot_profit[(pivot_profit.sum(axis=1) > 0) | (pivot_profit.sum(axis=1) < -10)]

    # 创建图表
    fig = plt.figure(figsize=(20, 12))

    # 设置全局字体
    for ax in fig.get_axes():
        pass  # axes还没创建

    # 1. 行业×年度热力图
    ax1 = plt.subplot(2, 2, 1)
    sns.heatmap(pivot_profit, annot=True, fmt='.1f', cmap='RdYlGn',
                center=0, linewidths=0.5, cbar_kws={'label': '收益率(%)'}, ax=ax1,
                annot_kws={'family': 'SimHei'})
    ax1.set_title('行业板块年度收益热力图 (%)', fontsize=14, fontweight='bold', fontfamily='SimHei')
    ax1.set_xlabel('', fontfamily='SimHei')
    ax1.set_ylabel('', fontfamily='SimHei')
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=0, fontfamily='SimHei')
    ax1.set_yticklabels(ax1.get_yticklabels(), fontfamily='SimHei')

    # 2. 每年TOP10行业柱状图
    ax2 = plt.subplot(2, 2, 2)
    years = pivot_profit.columns.tolist()
    x = np.arange(len(pivot_profit.index[:15]))
    width = 0.25

    for i, year in enumerate(years):
        values = pivot_profit[year].head(15).values
        ax2.bar(x + i * width, values, width, label=year, alpha=0.8)

    ax2.set_title('各年度TOP15行业收益对比', fontsize=14, fontweight='bold', fontfamily='SimHei')
    ax2.set_xlabel('行业板块', fontsize=12, fontfamily='SimHei')
    ax2.set_ylabel('收益率 (%)', fontsize=12, fontfamily='SimHei')
    ax2.set_xticks(x + width)
    ax2.set_xticklabels(pivot_profit.index[:15], rotation=45, ha='right', fontfamily='SimHei')
    ax2.legend(title='年份', prop={'family': 'SimHei'})
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.grid(axis='y', alpha=0.3)

    # 3. 总收益TOP15/TOP10对比
    ax3 = plt.subplot(2, 2, 3)
    top_15 = pivot_profit.head(15)
    bottom_10 = pivot_profit.tail(10)

    colors = ['#2ecc59' if x > 0 else '#e74c3c' for x in top_15.sum(axis=1).values]
    ax3.barh(range(len(top_15)), top_15.sum(axis=1).values, color=colors, alpha=0.8)
    ax3.set_yticks(range(len(top_15)))
    ax3.set_yticklabels(top_15.index, fontfamily='SimHei')
    ax3.set_title('最佳表现行业（总收益）', fontsize=14, fontweight='bold', fontfamily='SimHei')
    ax3.set_xlabel('总收益率 (%)', fontsize=12, fontfamily='SimHei')
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax3.grid(axis='x', alpha=0.3)

    # 添加数值标签
    for i, v in enumerate(top_15.sum(axis=1).values):
        ax3.text(v + (3 if v > 0 else -3), i, f'{v:.1f}%',
                va='center', ha='left' if v > 0 else 'right', fontsize=9, fontfamily='SimHei')

    # 4. 年度汇总对比
    ax4 = plt.subplot(2, 2, 4)
    yearly_summary = []
    for year in years:
        year_data = {
            'year': year,
            '正收益行业数': (pivot_profit[year] > 0).sum(),
            '负收益行业数': (pivot_profit[year] < 0).sum(),
            '平均收益': pivot_profit[year].mean(),
            '最佳行业': pivot_profit[year].idxmax(),
            '最佳收益': pivot_profit[year].max(),
            '最差行业': pivot_profit[year].idxmin(),
            '最差收益': pivot_profit[year].min()
        }
        yearly_summary.append(year_data)

    summary_df = pd.DataFrame(yearly_summary)

    # 绘制正负收益行业数
    x_pos = np.arange(len(years))
    ax4.bar(x_pos - 0.2, summary_df['正收益行业数'], 0.4,
            label='正收益行业', color='#2ecc59', alpha=0.8)
    ax4.bar(x_pos + 0.2, summary_df['负收益行业数'], 0.4,
            label='负收益行业', color='#e74c3c', alpha=0.8)

    ax4.set_title('各年度盈亏行业分布', fontsize=14, fontweight='bold', fontfamily='SimHei')
    ax4.set_xlabel('年份', fontsize=12, fontfamily='SimHei')
    ax4.set_ylabel('行业数量', fontsize=12, fontfamily='SimHei')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(years, fontfamily='SimHei')
    ax4.legend(prop={'family': 'SimHei'})
    ax4.grid(axis='y', alpha=0.3)

    # 添加数值标签
    for i, (pos, neg) in enumerate(zip(summary_df['正收益行业数'], summary_df['负收益行业数'])):
        ax4.text(i - 0.2, pos + 0.5, str(int(pos)), ha='center', va='bottom', fontsize=10, fontfamily='SimHei')
        ax4.text(i + 0.2, neg + 0.5, str(int(neg)), ha='center', va='bottom', fontsize=10, fontfamily='SimHei')

    plt.tight_layout()

    # 保存图表
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = BACKTEST_RESULTS_DIR / f"sector_analysis_{timestamp}.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n图表已保存: {output_file}")

    # 打印年度汇总表
    print(f"\n{'='*80}")
    print("年度汇总统计")
    print(f"{'='*80}")
    print(summary_df.to_string(index=False))

    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="绘制行业分析图表")
    parser.add_argument("--result-file", type=str,
                       default="data/backtest_results/full_backtest_2023_2025_20260121_093915.json",
                       help="回测结果文件路径")

    args = parser.parse_args()

    plot_sector_analysis(args.result_file)
