# -*- coding: utf-8 -*-
"""
A股选股系统 - 主程序入口

使用方法:
1. 命令行模式: python main.py --test
2. Web界面: streamlit run ui/app.py
3. 直接运行: python main.py
"""
import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_fetcher import DataFetcher
from src.fundamentals import FundamentalFilter
from src.sector_heat import SectorHeat
from src.signal_engine import SignalEngine
from src.notifier import Notifier
import config


def update_stock_pools():
    """更新股票池"""
    print("=== 更新股票池 ===")
    fetcher = DataFetcher()

    pools = fetcher.get_all_target_sectors_stocks()

    for category, stocks in pools.items():
        print(f"{category}: {len(stocks)} 只股票")

    fetcher.save_stock_pools(pools)
    print(f"\n股票池已保存到 {os.path.join(config.DATA_DIR, 'stock_pools.json')}")

    return pools


def run_stock_selection():
    """运行选股流程"""
    print("\n=== 开始选股 ===")

    # 1. 加载股票池
    fetcher = DataFetcher()
    pools = fetcher.load_stock_pools()

    if not pools:
        print("股票池为空，正在更新...")
        pools = update_stock_pools()

    # 2. 基本面筛选
    print("\n--- 基本面筛选 ---")
    filter_obj = FundamentalFilter()
    engine = SignalEngine()

    all_stocks = []
    for category, codes in pools.items():
        print(f"筛选 {category} 板块...")
        filtered_df = filter_obj.filter_by_fundamentals(codes[:30], category)  # 限制数量

        if not filtered_df.empty:
            for _, row in filtered_df.head(10).iterrows():
                all_stocks.append({
                    "code": row["code"],
                    "name": row["name"],
                    "sector": category,
                })

            print(f"  符合条件: {len(filtered_df)} 只")

    # 3. 技术分析与信号生成
    print(f"\n--- 技术分析 ({len(all_stocks)} 只股票) ---")
    results = engine.analyze_stocks(all_stocks)

    # 4. 输出结果
    print("\n=== 选股结果 ===")
    print_signals_summary(results)

    return results


def print_signals_summary(results: dict):
    """打印信号汇总"""
    buy_list = results.get("buy", [])
    sell_list = results.get("sell", [])

    print(f"\n【买入信号】{len(buy_list)} 只")
    for stock in buy_list[:15]:
        reasons = " | ".join(stock.get("reasons", []))
        print(
            f"  {stock['name']}({stock['code']}) "
            f"¥{stock['price']:.2f} "
            f"强度:{stock['signal_strength']} "
            f"({reasons})"
        )

    print(f"\n【卖出信号】{len(sell_list)} 只")
    for stock in sell_list[:15]:
        reasons = " | ".join(stock.get("reasons", []))
        print(
            f"  {stock['name']}({stock['code']}) "
            f"¥{stock['price']:.2f} "
            f"强度:{stock['signal_strength']} "
            f"({reasons})"
        )

    # 持有信号数量
    hold_list = results.get("hold", [])
    print(f"\n【持有/观望】{len(hold_list)} 只")


def send_notification(results: dict):
    """发送微信通知"""
    notifier = Notifier()

    buy_list = results.get("buy", [])
    sell_list = results.get("sell", [])

    if not buy_list and not sell_list:
        print("无买卖信号，跳过通知")
        return

    print("\n=== 发送微信通知 ===")
    summary = "A股智能选股系统今日选股结果"
    success = notifier.send_stock_signals(buy_list, sell_list, summary)

    if success:
        print("通知发送成功！")
    else:
        print("通知发送失败，请检查配置")


def show_sector_heat():
    """显示板块热度"""
    print("\n=== 板块热度排名 ===")
    heat = SectorHeat()
    ranking = heat.get_sector_heat_ranking()

    if not ranking.empty:
        # 只显示目标板块
        target_sectors = []
        for category, sectors in config.TARGET_SECTORS.items():
            target_sectors.extend(sectors)

        ranking_filtered = ranking[ranking["name"].isin(target_sectors)]

        if not ranking_filtered.empty:
            for _, row in ranking_filtered.head(10).iterrows():
                print(
                    f"  {row['name']:12s} {row['category']:8s} "
                    f"涨跌:{row['change_pct']:>6.2f}% "
                    f"热度:{row['heat_score']:.1f}"
                )
        else:
            print("暂无板块数据")
    else:
        print("无法获取板块热度")


def main():
    parser = argparse.ArgumentParser(description="A股选股系统")
    parser.add_argument("--test", action="store_true", help="测试模式 - 测试各模块功能")
    parser.add_argument("--update-pools", action="store_true", help="更新股票池")
    parser.add_argument("--heat", action="store_true", help="查看板块热度")
    parser.add_argument("--notify", action="store_true", help="选股后发送微信通知")
    parser.add_argument("--web", action="store_true", help="启动Web界面")

    args = parser.parse_args()

    print("╔════════════════════════════════════════╗")
    print("║      A股智能选股系统 v0.1.0            ║")
    print("╚════════════════════════════════════════╝")

    if args.test:
        print("\n=== 测试模式 ===")
        print("1. 测试数据获取...")
        fetcher = DataFetcher()
        df = fetcher.get_stock_list()
        print(f"   获取股票列表: {len(df)} 只")

        print("\n2. 测试板块成分股...")
        stocks = fetcher.get_sector_stocks("人工智能")
        print(f"   人工智能板块: {len(stocks)} 只")

        print("\n3. 测试板块热度...")
        heat = SectorHeat()
        ranking = heat.get_sector_heat_ranking()
        print(f"   获取板块热度: {len(ranking)} 个板块")

        print("\n4. 测试通知...")
        notifier = Notifier()
        notifier.send_test_message()

        print("\n✓ 测试完成")

    elif args.update_pools:
        update_stock_pools()

    elif args.heat:
        show_sector_heat()

    elif args.web:
        import subprocess
        print("\n=== 启动Web界面 ===")
        print("请在浏览器中打开: http://localhost:8501")
        print("按 Ctrl+C 停止\n")
        subprocess.run(["streamlit", "run", "ui/app.py"])

    else:
        # 默认：完整选股流程
        update_stock_pools()
        show_sector_heat()
        results = run_stock_selection()

        if args.notify:
            send_notification(results)

    print("\n执行完成！")


if __name__ == "__main__":
    main()
