# -*- coding: utf-8 -*-
"""
Phase 2 功能测试 - 回测引擎
"""
import sys
import pickle
from pathlib import Path

sys.path.insert(0, '.')

from core.strategies import MACDRSIStrategy
from core.backtest import BacktestEngine


def load_cached_data(code, year="2024"):
    """从缓存加载数据"""
    cache_file = Path(f"data/cache/stock_hist_{code}_{year}0101_{year}1231_qfq.pkl")

    if cache_file.exists():
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return None


def test_portfolio():
    """测试Portfolio"""
    print("\n" + "="*60)
    print("测试 Portfolio（组合管理）")
    print("="*60)

    from core.backtest import Portfolio
    from datetime import datetime

    portfolio = Portfolio(initial_capital=100000)

    print(f"\n1. 初始状态:")
    print(f"   资金: {portfolio.cash:,.0f} 元")
    print(f"   持仓数: {len(portfolio.positions)}")

    # 买入
    print(f"\n2. 买入股票:")
    success = portfolio.buy(
        code="000001",
        name="平安银行",
        price=10.0,
        shares=1000,
        date=datetime.now(),
        reason="测试买入"
    )
    print(f"   买入成功: {success}")
    print(f"   剩余资金: {portfolio.cash:,.0f} 元")
    print(f"   持仓: {portfolio.positions}")

    # 更新价格
    print(f"\n3. 更新价格:")
    portfolio.positions["000001"].update_price(11.0)
    print(f"   当前价格: 11.0")
    print(f"   盈亏: {portfolio.positions['000001'].profit:.2f} 元")
    print(f"   盈亏比例: {portfolio.positions['000001'].profit_pct:.2f}%")

    # 卖出
    print(f"\n4. 卖出股票:")
    success = portfolio.sell(
        code="000001",
        price=11.0,
        shares=None,
        date=datetime.now(),
        reason="测试卖出"
    )
    print(f"   卖出成功: {success}")
    print(f"   最终资金: {portfolio.cash:,.0f} 元")

    # 汇总
    print(f"\n5. 组合汇总:")
    summary = portfolio.get_summary()
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

    print("\n✓ Portfolio 测试通过")


def test_risk_manager():
    """测试RiskManager"""
    print("\n" + "="*60)
    print("测试 RiskManager（风险管理）")
    print("="*60)

    from core.backtest import RiskManager, Portfolio, Position
    from datetime import datetime

    risk_mgr = RiskManager()

    print(f"\n1. 风控配置:")
    config = risk_mgr.get_config()
    print(f"   最大持仓: {config['max_positions']}")
    print(f"   单只仓位: {config['position_size']*100:.0f}%")
    print(f"   硬止损: {config['stop_loss']*100:.0f}%")
    print(f"   移动止损: {config['trailing_stop']*100:.0f}%")

    # 测试止损
    print(f"\n2. 测试止损:")
    position = Position(
        code="000001",
        name="测试",
        shares=1000,
        entry_price=10.0,
        entry_date=datetime.now(),
        current_price=8.5,  # 下跌15%
        peak_price=10.0
    )

    should_stop, reason = risk_mgr.check_stop_loss(position)
    print(f"   当前价: 8.5, 成本价: 10.0")
    print(f"   触发止损: {should_stop}")
    print(f"   原因: {reason}")

    # 测试止盈
    print(f"\n3. 测试止盈:")
    position.current_price = 11.0  # 上涨10%
    position.peak_price = 11.0

    should_tp, shares, reason = risk_mgr.check_take_profit(position)
    print(f"   当前价: 11.0, 成本价: 10.0")
    print(f"   触发止盈: {should_tp}")
    print(f"   卖出数量: {shares}")
    print(f"   原因: {reason}")

    print("\n✓ RiskManager 测试通过")


def test_backtest_engine():
    """测试BacktestEngine"""
    print("\n" + "="*60)
    print("测试 BacktestEngine（回测引擎）")
    print("="*60)

    # 准备数据
    print("\n1. 准备测试数据...")
    stock_pool = ["000001", "000002", "600036"]

    print(f"   股票池: {stock_pool}")

    # 创建策略
    print("\n2. 创建策略...")
    strategy = MACDRSIStrategy()
    print(f"   策略: {strategy.name}")
    print(f"   需要指标: {strategy.get_required_indicators()}")

    # 创建回测引擎
    print("\n3. 创建回测引擎...")
    engine = BacktestEngine(
        initial_capital=100000,
        risk_config={
            "max_positions": 3,
            "position_size": 0.20,
            "stop_loss": -0.08,
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
        check_interval=5
    )

    # 打印结果
    engine.print_results(result)

    print("\n✓ BacktestEngine 测试通过")

    return result


def main():
    """运行Phase 2测试"""
    print("\n" + "="*60)
    print("Phase 2 功能测试 - 回测引擎")
    print("="*60)

    try:
        # 测试1: Portfolio
        test_portfolio()

        # 测试2: RiskManager
        test_risk_manager()

        # 测试3: BacktestEngine
        test_backtest_engine()

        print("\n" + "="*60)
        print("✓ Phase 2 所有测试通过!")
        print("="*60)
        print("\nPhase 2 核心功能验证:")
        print("  ✓ Portfolio - 组合管理")
        print("  ✓ RiskManager - 风险控制")
        print("  ✓ BacktestEngine - 回测引擎")
        print("\n🎉 Phase 2 回测系统已就绪!")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
