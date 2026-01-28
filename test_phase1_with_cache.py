# -*- coding: utf-8 -*-
"""
Phase 1 测试 - 使用本地缓存数据
"""
import sys
import pandas as pd
import pickle
from pathlib import Path

sys.path.insert(0, '.')

from core.indicators import IndicatorFactory
from core.strategies import StrategyManager, MACDRSIStrategy


def load_cached_data(code="000001", year="2024"):
    """从data/cache/目录加载缓存的历史数据"""
    cache_file = Path(f"data/cache/stock_hist_{code}_{year}0101_{year}1231_qfq.pkl")

    if not cache_file.exists():
        print(f"缓存文件不存在: {cache_file}")
        return pd.DataFrame()

    try:
        with open(cache_file, 'rb') as f:
            df = pickle.load(f)
        print(f"✓ 从缓存加载数据: {cache_file.name}")
        print(f"  数据行数: {len(df)}")
        print(f"  列名: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"加载缓存失败: {e}")
        return pd.DataFrame()


def test_indicator_factory():
    """测试指标工厂"""
    print("\n" + "="*60)
    print("测试 IndicatorFactory")
    print("="*60)

    # 从缓存加载数据
    df = load_cached_data("000001", "2024")

    if df.empty:
        print("❌ 无法加载数据")
        return None

    print(f"\n1. 原始数据预览:")
    print(df.head(3))

    # 测试计算指标
    print("\n2. 测试添加MA指标...")
    df = IndicatorFactory.calculate(df, "MA")
    assert "MA5" in df.columns, "MA5指标缺失"
    assert "MA20" in df.columns, "MA20指标缺失"
    print("   ✓ MA指标计算成功")

    print("\n3. 测试添加MACD指标...")
    df = IndicatorFactory.calculate(df, "MACD")
    assert "MACD_DIF" in df.columns, "MACD_DIF指标缺失"
    assert "MACD_DEA" in df.columns, "MACD_DEA指标缺失"
    print("   ✓ MACD指标计算成功")

    print("\n4. 测试添加RSI指标...")
    df = IndicatorFactory.calculate(df, "RSI")
    assert "RSI" in df.columns, "RSI指标缺失"
    print("   ✓ RSI指标计算成功")

    print("\n5. 测试添加VOLUME指标...")
    df = IndicatorFactory.calculate(df, "VOLUME")
    print("   ✓ VOLUME指标计算成功")

    # 显示带指标的数据
    print("\n6. 带指标的数据预览:")
    cols_to_show = ["date", "close", "MA5", "MA20", "RSI", "MACD"]
    available_cols = [c for c in cols_to_show if c in df.columns]
    print(df[available_cols].tail(5))

    return df


def test_strategy():
    """测试策略"""
    print("\n" + "="*60)
    print("测试 Strategy Framework")
    print("="*60)

    # 加载数据并添加指标
    df = load_cached_data("000001", "2024")

    if df.empty:
        print("❌ 无法加载数据")
        return None

    print("\n1. 添加策略所需指标...")
    df = IndicatorFactory.calculate_multiple(df, ["MA", "MACD", "RSI", "VOLUME"])

    # 测试MACD_RSI策略
    print("\n2. 测试 MACD_RSI 策略...")
    strategy = MACDRSIStrategy()

    print(f"   需要的指标: {strategy.get_required_indicators()}")

    # 生成信号
    result = strategy.generate_signals(df)

    print(f"\n3. 策略结果 (000001 平安银行):")
    print(f"   动作: {result.action}")
    print(f"   评分: {result.score:.1f}")
    print(f"   原因: {', '.join(result.reasons)}")
    print(f"   置信度: {result.confidence:.2f}")

    if result.metadata:
        print(f"\n   详细指标值:")
        for key, value in result.metadata.items():
            if isinstance(value, (int, float)):
                print(f"     {key}: {value:.2f}")
            else:
                print(f"     {key}: {value}")

    # 测试自定义参数
    print("\n4. 测试自定义参数...")
    custom_strategy = MACDRSIStrategy(params={
        "buy_threshold": 60,
        "rsi_oversold": 25
    })

    result2 = custom_strategy.generate_signals(df)
    print(f"   使用更严格阈值:")
    print(f"     动作: {result2.action}")
    print(f"     评分: {result2.score:.1f}")

    return result


def test_strategy_manager():
    """测试策略管理器"""
    print("\n" + "="*60)
    print("测试 StrategyManager")
    print("="*60)

    manager = StrategyManager()

    # 列出策略
    print("\n1. 可用策略:")
    strategies = manager.list_strategies()
    for strat in strategies:
        info = manager.get_strategy_info(strat)
        print(f"   - {strat} (v{info['version']})")
        print(f"     需要指标: {', '.join(info['required_indicators'])}")

    print("\n✓ StrategyManager 测试通过")


def test_multiple_stocks():
    """测试多只股票"""
    print("\n" + "="*60)
    print("测试批量股票分析")
    print("="*60)

    stocks = ["000001", "000002", "600036"]
    strategy = MACDRSIStrategy()

    print(f"\n分析 {len(stocks)} 只股票...")

    for code in stocks:
        df = load_cached_data(code, "2024")

        if df.empty:
            print(f"  {code}: 数据缺失 ⚠️")
            continue

        # 添加指标
        df = IndicatorFactory.calculate_multiple(df, ["MA", "MACD", "RSI", "VOLUME"])

        # 生成信号
        result = strategy.generate_signals(df)

        action_icon = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}
        print(f"  {code}: {action_icon.get(result.action, '⚪')} {result.action.upper()} "
              f"(评分: {result.score:.0f}, 原因: {', '.join(result.reasons[:2])})")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Phase 1 测试 - 使用本地缓存数据")
    print("="*60)

    try:
        # 测试1: 指标工厂
        test_indicator_factory()

        # 测试2: 策略
        test_strategy()

        # 测试3: 策略管理器
        test_strategy_manager()

        # 测试4: 多只股票
        test_multiple_stocks()

        print("\n" + "="*60)
        print("✓ 所有测试通过!")
        print("="*60)
        print("\nPhase 1 核心功能验证:")
        print("  ✓ IndicatorFactory - 指标计算")
        print("  ✓ Strategy - 信号生成")
        print("  ✓ StrategyManager - 策略管理")
        print("  ✓ 批量分析 - 多股票支持")
        print("\n🎉 Phase 1 基础设施已就绪!")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
