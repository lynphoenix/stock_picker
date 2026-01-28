# -*- coding: utf-8 -*-
"""
Phase 1 离线测试（使用模拟数据）
适用于无法访问AKShare API的环境
"""
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from core.indicators import IndicatorFactory
from core.strategies import StrategyManager, MACDRSIStrategy


def create_mock_data(days=120):
    """创建模拟K线数据"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # 生成随机价格数据
    np.random.seed(42)
    close_prices = 10 + np.cumsum(np.random.randn(days) * 0.1)

    df = pd.DataFrame({
        'date': dates,
        'open': close_prices + np.random.randn(days) * 0.05,
        'high': close_prices + abs(np.random.randn(days)) * 0.1,
        'low': close_prices - abs(np.random.randn(days)) * 0.1,
        'close': close_prices,
        'volume': np.random.randint(1000000, 10000000, days)
    })

    return df


def test_indicator_factory():
    """测试指标工厂"""
    print("\n" + "="*60)
    print("测试 IndicatorFactory")
    print("="*60)

    # 创建模拟数据
    df = create_mock_data()
    print(f"\n1. 创建模拟数据: {len(df)} 行")

    # 测试计算MA
    print("\n2. 测试计算MA指标...")
    df = IndicatorFactory.calculate(df, "MA")
    assert "MA5" in df.columns, "MA5指标缺失"
    assert "MA20" in df.columns, "MA20指标缺失"
    print("   ✓ MA指标计算成功")

    # 测试计算MACD
    print("\n3. 测试计算MACD指标...")
    df = IndicatorFactory.calculate(df, "MACD")
    assert "MACD_DIF" in df.columns, "MACD_DIF指标缺失"
    assert "MACD_DEA" in df.columns, "MACD_DEA指标缺失"
    print("   ✓ MACD指标计算成功")

    # 测试计算RSI
    print("\n4. 测试计算RSI指标...")
    df = IndicatorFactory.calculate(df, "RSI")
    assert "RSI" in df.columns, "RSI指标缺失"
    print("   ✓ RSI指标计算成功")

    # 显示最新数据
    print("\n5. 最新数据预览:")
    print(df[["date", "close", "MA5", "MA20", "RSI", "MACD"]].tail(3))

    return df


def test_strategy():
    """测试策略"""
    print("\n" + "="*60)
    print("测试 Strategy Framework")
    print("="*60)

    # 创建带指标的数据
    df = create_mock_data()
    df = IndicatorFactory.calculate_multiple(df, ["MA", "MACD", "RSI", "VOLUME"])

    # 测试MACD_RSI策略
    print("\n1. 测试 MACD_RSI 策略...")
    strategy = MACDRSIStrategy()

    print(f"   需要的指标: {strategy.get_required_indicators()}")

    # 生成信号
    result = strategy.generate_signals(df)

    print(f"\n2. 策略结果:")
    print(f"   动作: {result.action}")
    print(f"   评分: {result.score:.1f}")
    print(f"   原因: {', '.join(result.reasons)}")
    print(f"   置信度: {result.confidence:.2f}")
    print(f"   元数据: {result.metadata}")

    # 测试自定义参数
    print("\n3. 测试自定义参数...")
    custom_strategy = MACDRSIStrategy(params={
        "buy_threshold": 60,
        "rsi_oversold": 25
    })

    result2 = custom_strategy.generate_signals(df)
    print(f"   自定义参数后动作: {result2.action}")
    print(f"   自定义参数后评分: {result2.score:.1f}")

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
        print(f"   - {strat}")

    # 获取策略信息
    print("\n2. MACD_RSI 策略信息:")
    info = manager.get_strategy_info("MACD_RSI")
    print(f"   版本: {info['version']}")
    print(f"   需要指标: {info['required_indicators']}")
    print(f"   参数数量: {len(info['params'])}")

    print("\n✓ StrategyManager 测试通过")


def main():
    """运行所有离线测试"""
    print("\n" + "="*60)
    print("Phase 1 离线功能测试（使用模拟数据）")
    print("="*60)

    try:
        # 测试1: 指标工厂
        test_indicator_factory()

        # 测试2: 策略
        test_strategy()

        # 测试3: 策略管理器
        test_strategy_manager()

        print("\n" + "="*60)
        print("✓ 所有离线测试通过!")
        print("="*60)
        print("\n说明:")
        print("- IndicatorFactory 指标计算 ✓")
        print("- Strategy 信号生成 ✓")
        print("- StrategyManager 策略管理 ✓")
        print("\n注: DataManager测试需要网络连接AKShare API")
        print("    在实际生产环境中可正常使用")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
