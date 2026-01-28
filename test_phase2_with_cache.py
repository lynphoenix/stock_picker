# -*- coding: utf-8 -*-
"""
Phase 2 测试 - 使用本地缓存数据
"""
import sys
import pickle
from pathlib import Path
import pandas as pd

sys.path.insert(0, '.')

from core.strategies import MACDRSIStrategy
from core.backtest import BacktestEngine, Portfolio, RiskManager
from core.indicators import IndicatorFactory


# 猴子补丁：让DataManager使用本地缓存
def patch_data_manager():
    """修改DataManager使其从本地缓存读取"""
    from core.data import DataManager

    original_get_data = DataManager.get_data

    def patched_get_data(self, code, mode="realtime", start_date=None, end_date=None, use_cache=True):
        """从缓存读取数据"""
        # 提取年份
        if start_date and end_date:
            year = start_date[:4]
            cache_file = Path(f"data/cache/stock_hist_{code}_{year}0101_{year}1231_qfq.pkl")

            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    df = pickle.load(f)
                # 过滤日期范围
                if not df.empty:
                    df = df[(df['date'] >= pd.to_datetime(start_date)) &
                            (df['date'] <= pd.to_datetime(end_date))]
                return df

        return pd.DataFrame()

    DataManager.get_data = patched_get_data
    print("✓ DataManager已打补丁，使用本地缓存")


def test_backtest_with_cache():
    """使用缓存数据测试回测"""
    print("\n" + "="*60)
    print("Phase 2 回测测试 - 使用本地缓存")
    print("="*60)

    # 打补丁
    patch_data_manager()

    # 准备数据
    print("\n1. 准备测试数据...")
    stock_pool = ["000001", "000002", "600036"]
    print(f"   股票池: {stock_pool}")

    # 创建策略
    print("\n2. 创建策略...")
    strategy = MACDRSIStrategy(params={
        "buy_threshold": 45,  # 降低买入阈值，增加交易机会
    })
    print(f"   策略: {strategy.name}")
    print(f"   买入阈值: 45分（降低以增加交易）")

    # 创建回测引擎
    print("\n3. 创建回测引擎...")
    engine = BacktestEngine(
        initial_capital=100000,
        risk_config={
            "max_positions": 3,
            "position_size": 0.30,  # 每只30%
            "stop_loss": -0.08,     # -8%止损
            "trailing_stop": 0.04,  # 4%移动止损
            "take_profit_1": 0.08,  # +8%止盈1
            "take_profit_2": 0.15,  # +15%止盈2
        }
    )
    print(f"   初始资金: 100,000 元")
    print(f"   风控配置: {engine.risk_manager}")

    # 运行回测
    print("\n4. 运行回测...")
    result = engine.run(
        strategy=strategy,
        stock_pool=stock_pool,
        start_date="20240101",
        end_date="20241231",
        check_interval=3  # 每3天检查一次
    )

    # 打印结果
    engine.print_results(result)

    # 额外分析
    if not result.trades_df.empty:
        print(f"\n{'='*60}")
        print("交易分析")
        print(f"{'='*60}")

        sell_trades = result.trades_df[result.trades_df['action'] == 'sell']
        if not sell_trades.empty:
            win_trades = sell_trades[sell_trades['profit_pct'] > 0]
            loss_trades = sell_trades[sell_trades['profit_pct'] <= 0]

            print(f"\n盈利交易 ({len(win_trades)}笔):")
            if not win_trades.empty:
                print(f"  平均盈利: {win_trades['profit_pct'].mean():.2f}%")
                print(f"  最大盈利: {win_trades['profit_pct'].max():.2f}%")

            print(f"\n亏损交易 ({len(loss_trades)}笔):")
            if not loss_trades.empty:
                print(f"  平均亏损: {loss_trades['profit_pct'].mean():.2f}%")
                print(f"  最大亏损: {loss_trades['profit_pct'].min():.2f}%")

    return result


def main():
    """运行测试"""
    print("\n" + "="*60)
    print("Phase 2 完整回测测试")
    print("="*60)

    try:
        result = test_backtest_with_cache()

        print("\n" + "="*60)
        print("✓ Phase 2 回测测试完成!")
        print("="*60)

        if result.total_trades > 0:
            print(f"\n📊 回测总结:")
            print(f"  收益率: {result.total_return:+.2f}%")
            print(f"  交易次数: {result.total_trades}笔")
            print(f"  胜率: {result.win_rate:.1f}%")
            print(f"  最大回撤: {result.max_drawdown:.2f}%")
            print(f"\n🎉 回测引擎运行正常!")
        else:
            print(f"\n⚠️  未产生交易（可能需要调整策略参数）")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
