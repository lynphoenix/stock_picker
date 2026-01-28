# -*- coding: utf-8 -*-
"""
Phase 1 功能测试
"""
import sys
sys.path.insert(0, '.')

from core.data import DataManager
from core.indicators import IndicatorFactory
from core.strategies import StrategyManager


def test_data_manager():
    """测试数据管理器"""
    print("\n" + "="*60)
    print("测试 DataManager")
    print("="*60)

    dm = DataManager()

    # 测试获取实时数据
    print("\n1. 测试获取实时数据 (平安银行 000001)...")
    df = dm.get_data("000001", mode="realtime")
    print(f"   获取数据: {len(df)} 行")
    print(f"   列名: {list(df.columns)}")

    # 测试添加指标
    print("\n2. 测试添加技术指标...")
    df = dm.add_indicators(df, ["MA", "MACD", "RSI"])
    print(f"   添加指标后列名: {list(df.columns)}")
    print(f"   最新数据:")
    print(df[["close", "MA5", "MA20", "RSI", "MACD"]].tail(3))

    return df


def test_indicator_factory():
    """测试指标工厂"""
    print("\n" + "="*60)
    print("测试 IndicatorFactory")
    print("="*60)

    # 列出所有指标
    print("\n1. 可用指标:")
    indicators = IndicatorFactory.list_indicators()
    for ind in indicators:
        print(f"   - {ind}")


def test_strategy_manager():
    """测试策略管理器"""
    print("\n" + "="*60)
    print("测试 StrategyManager")
    print("="*60)

    manager = StrategyManager()

    # 列出所有策略
    print("\n1. 可用策略:")
    strategies = manager.list_strategies()
    for strat in strategies:
        print(f"   - {strat}")
        info = manager.get_strategy_info(strat)
        print(f"     需要指标: {info['required_indicators']}")
        print(f"     参数: {info['params']}")

    # 测试运行策略
    print("\n2. 测试 MACD_RSI 策略 (平安银行 000001)...")
    result = manager.run_strategy("MACD_RSI", "000001", mode="realtime")

    print(f"   动作: {result.action}")
    print(f"   评分: {result.score:.1f}")
    print(f"   原因: {', '.join(result.reasons)}")
    print(f"   置信度: {result.confidence:.2f}")
    print(f"   元数据: {result.metadata}")

    # 测试批量运行
    print("\n3. 测试批量运行 (000001, 000002)...")
    results = manager.batch_run("MACD_RSI", ["000001", "000002"])

    for code, result in results.items():
        print(f"   {code}: {result.action} (评分: {result.score:.1f})")


def test_custom_strategy():
    """测试自定义策略参数"""
    print("\n" + "="*60)
    print("测试自定义策略参数")
    print("="*60)

    from core.strategies import MACDRSIStrategy

    # 创建自定义参数的策略
    custom_strategy = MACDRSIStrategy(params={
        "buy_threshold": 60,  # 提高买入阈值
        "rsi_oversold": 25,   # 更严格的超卖条件
    })

    print(f"\n策略名称: {custom_strategy.name}")
    print(f"自定义参数: {custom_strategy.get_params()}")

    # 手动测试
    manager = StrategyManager()
    manager.register(custom_strategy)  # 注册会覆盖同名策略

    result = manager.run_strategy("MACD_RSI", "000001", mode="realtime")
    print(f"\n使用自定义参数:")
    print(f"   动作: {result.action}")
    print(f"   评分: {result.score:.1f}")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Phase 1 功能测试")
    print("="*60)

    try:
        # 测试1: 数据管理器
        test_data_manager()

        # 测试2: 指标工厂
        test_indicator_factory()

        # 测试3: 策略管理器
        test_strategy_manager()

        # 测试4: 自定义策略
        test_custom_strategy()

        print("\n" + "="*60)
        print("✓ 所有测试通过!")
        print("="*60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
