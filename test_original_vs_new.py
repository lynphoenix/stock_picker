# -*- coding: utf-8 -*-
"""
原有策略 vs 新策略对比测试

对比你原来的 SignalEngine 策略和我新写的策略
"""
import sys
import pickle
from pathlib import Path
import pandas as pd

sys.path.insert(0, '.')

from core.strategies import (
    OriginalSignalStrategy,  # 你的原有策略
    MACDRSIStrategy,         # 我新写的类似策略
    MACrossoverStrategy,
    BollingerStrategy,
    MomentumStrategy,
    MultiFactorStrategy,
)
from core.backtest import BacktestEngine
from core.data import DataManager


def patch_data_manager():
    """修改DataManager使其从本地缓存读取"""
    from core.data import DataManager

    original_get_data = DataManager.get_data

    def patched_get_data(self, code, mode="realtime", start_date=None, end_date=None, use_cache=True):
        """从缓存读取数据"""
        if start_date and end_date:
            year = start_date[:4]
            cache_file = Path(f"data/cache/stock_hist_{code}_{year}0101_{year}1231_qfq.pkl")

            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    df = pickle.load(f)
                if not df.empty:
                    df = df[(df['date'] >= pd.to_datetime(start_date)) &
                            (df['date'] <= pd.to_datetime(end_date))]
                return df

        return pd.DataFrame()

    DataManager.get_data = patched_get_data
    print("✓ DataManager已打补丁，使用本地缓存\n")


def test_strategy(strategy, name, stock_pool, start_date, end_date):
    """测试单个策略"""
    engine = BacktestEngine(
        initial_capital=100000,
        risk_config={
            "max_positions": 3,
            "position_size": 0.30,
            "stop_loss": -0.08,
            "trailing_stop": 0.04,
            "take_profit_1": 0.08,
            "take_profit_2": 0.15,
        }
    )

    result = engine.run(
        strategy=strategy,
        stock_pool=stock_pool,
        start_date=start_date,
        end_date=end_date,
        check_interval=3
    )

    return result


def main():
    """主测试函数"""
    print("="*80)
    print("原有策略 vs 新策略 - 对比测试")
    print("="*80)

    # 打补丁
    patch_data_manager()

    # 测试参数
    stock_pool = ["000001", "000002", "600036"]
    start_date = "20240101"
    end_date = "20241231"

    print(f"股票池: {stock_pool}")
    print(f"时间范围: {start_date} ~ {end_date}")
    print(f"初始资金: 100,000 元\n")

    # 测试策略列表
    strategies_to_test = [
        (OriginalSignalStrategy(), "原有策略 (SignalEngine)"),
        (MACDRSIStrategy(params={"buy_threshold": 50}), "新策略 (MACD+RSI, 阈值50)"),
        (MACDRSIStrategy(params={"buy_threshold": 45}), "新策略 (MACD+RSI, 阈值45)"),
        (MACrossoverStrategy(), "新策略 (双均线)"),
        (BollingerStrategy(), "新策略 (布林带)"),
        (MomentumStrategy(), "新策略 (动量)"),
        (MultiFactorStrategy(), "新策略 (多因子)"),
    ]

    results = {}

    for strategy, name in strategies_to_test:
        print("\n" + "="*80)
        print(f"测试: {name}")
        print("="*80)

        result = test_strategy(strategy, name, stock_pool, start_date, end_date)

        results[name] = result

        # 打印结果
        print(f"\n{name} - 回测结果")
        print(f"{'='*80}")
        print(f"总收益率: {result.total_return:>10.2f}%")
        print(f"交易次数: {result.total_trades:>10} 次")
        print(f"胜率:     {result.win_rate:>10.1f}%")
        print(f"最大回撤: {result.max_drawdown:>10.2f}%")
        print(f"盈亏比:   {result.profit_factor:>10.2f}")

    # 汇总对比
    print(f"\n{'='*80}")
    print(f"策略对比汇总")
    print(f"{'='*80}")
    print(f"{'策略名称':<40} {'收益率':<10} {'交易':<8} {'胜率':<10} {'回撤':<10} {'盈亏比':<10}")
    print(f"{'-'*80}")

    for name, result in results.items():
        print(f"{name:<40} "
              f"{result.total_return:>8.2f}% "
              f"{result.total_trades:>6} "
              f"{result.win_rate:>8.1f}% "
              f"{result.max_drawdown:>8.2f}% "
              f"{result.profit_factor:>8.2f}")

    # 重点对比：原有 vs 新 MACD+RSI
    print(f"\n{'='*80}")
    print("🔍 原有策略 vs 新策略（相似逻辑）对比")
    print(f"{'='*80}")

    original = results.get("原有策略 (SignalEngine)")
    new_50 = results.get("新策略 (MACD+RSI, 阈值50)")
    new_45 = results.get("新策略 (MACD+RSI, 阈值45)")

    if original and new_50:
        print(f"\n指标对比:")
        print(f"{'指标':<20} {'原有策略':<15} {'新策略(阈值50)':<15} {'新策略(阈值45)':<15}")
        print(f"{'-'*65}")
        print(f"{'收益率':<20} {original.total_return:>13.2f}% {new_50.total_return:>13.2f}% {new_45.total_return:>13.2f}%")
        print(f"{'交易次数':<20} {original.total_trades:>13} {new_50.total_trades:>13} {new_45.total_trades:>13}")
        print(f"{'胜率':<20} {original.win_rate:>13.1f}% {new_50.win_rate:>13.1f}% {new_45.win_rate:>13.1f}%")
        print(f"{'最大回撤':<20} {original.max_drawdown:>13.2f}% {new_50.max_drawdown:>13.2f}% {new_45.max_drawdown:>13.2f}%")
        print(f"{'盈亏比':<20} {original.profit_factor:>13.2f} {new_50.profit_factor:>13.2f} {new_45.profit_factor:>13.2f}")

    # 找出最佳策略
    print(f"\n{'='*80}")
    print("🏆 综合评价")
    print(f"{'='*80}")

    best_return = max(results.items(), key=lambda x: x[1].total_return)
    best_winrate = max(results.items(), key=lambda x: x[1].win_rate)
    best_drawdown = min(results.items(), key=lambda x: x[1].max_drawdown)

    print(f"最高收益: {best_return[0][:30]} ({best_return[1].total_return:+.2f}%)")
    print(f"最高胜率: {best_winrate[0][:30]} ({best_winrate[1].win_rate:.1f}%)")
    print(f"最小回撤: {best_drawdown[0][:30]} ({best_drawdown[1].max_drawdown:.2f}%)")

    print(f"\n{'='*80}")
    print("✓ 测试完成！")
    print(f"{'='*80}")

    print("\n💡 结论:")
    print("  1. 你的原有策略已经成功转换为新架构")
    print("  2. 可以与其他策略一起回测对比")
    print("  3. 所有策略共用同一套回测引擎")
    print("  4. 可以根据实际表现选择或组合策略")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
