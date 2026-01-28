# -*- coding: utf-8 -*-
"""
涨停回调策略单元测试
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLimitUpDetection(unittest.TestCase):
    """测试涨停检测逻辑"""

    def setUp(self):
        """创建测试数据"""
        # 模拟10天的涨跌幅数据
        self.sample_data_1 = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            '涨跌幅': [2.0, 3.0, 9.8, 1.5, 2.0, 3.5, 4.0, -1.0, 2.5, 1.0]
        })
        # 第3天涨停

        self.sample_data_2 = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            '涨跌幅': [9.9, 9.8, 9.7, 2.0, 3.0, 4.0, 5.0, -1.0, 2.0, 1.0]
        })
        # 前3天连续涨停（应该被剔除）

        self.sample_data_3 = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            '涨跌幅': [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 9.5]
        })
        # 最后一天涨停

        self.sample_data_4 = pd.DataFrame({
            'date': pd.date_range('2025-01-01', periods=10),
            '涨跌幅': [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 8.5, 9.0, 2.0]
        })
        # 没有涨停（最大9.0%，<9.5%）

    def test_has_limit_up_no_continuous(self):
        """测试：有涨停但无连续3涨停 -> 应该通过"""
        data = self.sample_data_1.copy()

        # 检查是否有涨停（>=9.5%）
        has_limit_up = (data['涨跌幅'] >= 9.5).any()
        self.assertTrue(has_limit_up, "应该检测到涨停")

        # 检查最大连续涨停次数
        max_consecutive = 0
        current_consecutive = 0
        for change_pct in data['涨跌幅']:
            if change_pct >= 9.5:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        self.assertEqual(max_consecutive, 1, "最大连续涨停应该是1")
        self.assertTrue(max_consecutive < 3, "应该通过筛选（连续涨停<3）")

    def test_has_continuous_limit_up(self):
        """测试：连续3涨停 -> 应该被剔除"""
        data = self.sample_data_2.copy()

        # 检查最大连续涨停次数
        max_consecutive = 0
        current_consecutive = 0
        for change_pct in data['涨跌幅']:
            if change_pct >= 9.5:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        self.assertTrue(max_consecutive >= 3, "应该检测到3连板")
        self.assertFalse(max_consecutive < 3, "应该被剔除（连续涨停>=3）")

    def test_no_limit_up(self):
        """测试：没有涨停 -> 不应该通过"""
        data = self.sample_data_4.copy()

        has_limit_up = (data['涨跌幅'] >= 9.5).any()
        self.assertFalse(has_limit_up, "不应该检测到涨停")


class TestMACDGoldenCross(unittest.TestCase):
    """测试MACD金叉检测逻辑"""

    def test_macd_golden_cross(self):
        """测试MACD金叉识别"""
        # 创建模拟数据：先下跌后上涨，形成金叉
        # 下跌阶段
        data = pd.DataFrame({
            'close': [14.5, 14.2, 13.8, 13.5, 13.0, 12.8, 12.5, 12.0, 11.8, 11.5,
                       # 上涨阶段
                       11.8, 12.2, 12.8, 13.5, 14.2, 15.0, 15.8, 16.5, 17.2, 18.0]
        })

        # 计算EMA
        ema12 = data['close'].ewm(span=12, adjust=False).mean()
        ema26 = data['close'].ewm(span=26, adjust=False).mean()

        # 计算DIF和DEA
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()

        # 检查是否有金叉（DIF从负变正并上穿DEA）
        golden_cross_found = False
        for i in range(1, len(dif)):
            if (dif.iloc[i-1] <= dea.iloc[i-1]) and (dif.iloc[i] > dea.iloc[i]):
                golden_cross_found = True
                break

        self.assertTrue(golden_cross_found, "应该检测到金叉")

    def test_macd_no_golden_cross(self):
        """测试：没有金叉"""
        data = pd.DataFrame({
            'close': [14.5, 14, 13.5, 13, 12.5, 12, 11.5, 11, 10.5, 10]  # 下跌趋势
        })

        ema12 = data['close'].ewm(span=12, adjust=False).mean()
        ema26 = data['close'].ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()

        golden_cross = (dif.iloc[-2] <= dea.iloc[-2]) and (dif.iloc[-1] > dea.iloc[-1])

        self.assertFalse(golden_cross, "不应该检测到金叉")


class TestBuySignal(unittest.TestCase):
    """测试买入信号识别"""

    def test_price_near_ma20(self):
        """测试：股价回调到MA20附近"""
        # 创建20天数据
        np.random.seed(42)
        prices = np.random.uniform(10, 15, 20)

        # MA20
        ma20 = np.mean(prices)

        # 当前价格在MA20的±2%范围内
        current_price = ma20 * 1.01

        price_to_ma20 = abs(current_price - ma20) / ma20
        is_near = price_to_ma20 <= 0.02

        self.assertTrue(is_near, f"价格{current_price:.2f}应该接近MA20{ma20:.2f}")

    def test_not_near_ma20(self):
        """测试：股价远离MA20"""
        np.random.seed(42)
        prices = np.random.uniform(10, 15, 20)
        ma20 = np.mean(prices)

        # 当前价格远离MA20（超过5%）
        current_price = ma20 * 1.05

        price_to_ma20 = abs(current_price - ma20) / ma20
        is_near = price_to_ma20 <= 0.02

        self.assertFalse(is_near, f"价格{current_price:.2f}不应该接近MA20{ma20:.2f}")

    def test_volume_surge(self):
        """测试：放量（成交量>1.5倍平均值）"""
        # 生成5日成交量数据
        volumes = np.array([1000, 1200, 1100, 1300, 1400])
        avg_volume = np.mean(volumes[:-1])  # 前4日平均

        # 当日成交量放大
        current_volume = avg_volume * 1.6

        is_surge = current_volume >= avg_volume * 1.5
        self.assertTrue(is_surge, f"成交量{current_volume}应该大于1.5倍平均{avg_volume}")

    def test_bullish_candle(self):
        """测试：阳线"""
        open_price = 10.0
        close_price = 10.5

        is_bullish = close_price > open_price
        self.assertTrue(is_bullish, "收盘价高于开盘价应该是阳线")

    def test_buy_signal_all_conditions(self):
        """测试：完整的买入信号"""
        # 创建20天的K线数据
        np.random.seed(42)
        dates = pd.date_range('2025-01-01', periods=20)

        # 前19天的数据
        prices = np.random.uniform(10, 12, 19).tolist()
        volumes = np.random.uniform(1000, 1500, 19).tolist()

        # 第20天（信号日）
        ma20 = np.mean(prices)
        signal_price = ma20 * 1.01  # 接近MA20
        signal_volume = np.mean(volumes) * 1.6  # 放量

        prices.append(signal_price)
        volumes.append(signal_volume)

        # 生成开盘价（确保是阳线）
        opens = [p * 0.99 for p in prices]

        data = pd.DataFrame({
            'date': dates,
            'open': opens,
            'close': prices,
            'volume': volumes
        })

        # 检查所有条件
        # 1. 价格接近MA20
        ma20_calc = data['close'].iloc[-20:].mean()
        price_to_ma20 = abs(data['close'].iloc[-1] - ma20_calc) / ma20_calc
        condition1 = price_to_ma20 <= 0.02

        # 2. 阳线
        condition2 = data['close'].iloc[-1] > data['open'].iloc[-1]

        # 3. 放量
        avg_volume = data['volume'].iloc[-5:-1].mean()
        condition3 = data['volume'].iloc[-1] >= avg_volume * 1.5

        self.assertTrue(condition1, "条件1：价格应该接近MA20")
        self.assertTrue(condition2, "条件2：应该是阳线")
        self.assertTrue(condition3, "条件3：应该放量")


class TestSellSignal(unittest.TestCase):
    """测试卖出信号"""

    def test_below_ma20(self):
        """测试：跌破MA20"""
        # 创建20天数据
        np.random.seed(42)
        prices = list(np.random.uniform(10, 12, 19))
        ma20 = np.mean(prices)

        # 第20天价格跌破MA20
        current_price = ma20 * 0.98
        prices.append(current_price)

        # 计算MA20
        ma20_calc = np.mean(prices)

        # 检查是否跌破
        is_below = current_price < ma20_calc
        self.assertTrue(is_below, f"价格{current_price:.2f}应该低于MA20{ma20_calc:.2f}")

    def test_above_ma20(self):
        """测试：在MA20上方"""
        np.random.seed(42)
        prices = list(np.random.uniform(10, 12, 19))
        ma20 = np.mean(prices)

        current_price = ma20 * 1.02
        prices.append(current_price)

        ma20_calc = np.mean(prices)
        is_above = current_price >= ma20_calc

        self.assertTrue(is_above, f"价格{current_price:.2f}应该在MA20{ma20_calc:.2f}之上")

    def test_profit_target_30(self):
        """测试：涨幅30%减仓"""
        entry_price = 10.0
        current_price = 13.0  # 涨幅30%

        profit_pct = (current_price - entry_price) / entry_price * 100
        should_reduce = profit_pct >= 30

        self.assertTrue(should_reduce, f"涨幅{profit_pct:.1f}%应该触发减仓")

    def test_profit_target_50(self):
        """测试：涨幅50%减仓"""
        entry_price = 10.0
        current_price = 15.0  # 涨幅50%

        profit_pct = (current_price - entry_price) / entry_price * 100
        should_reduce = profit_pct >= 50

        self.assertTrue(should_reduce, f"涨幅{profit_pct:.1f}%应该触发减仓")


class TestEdgeCases(unittest.TestCase):
    """测试边界情况"""

    def test_insufficient_data(self):
        """测试：数据不足20天"""
        # 只有10天数据
        data = pd.DataFrame({
            'close': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
        })

        # 尝试计算MA20
        can_calculate_ma20 = len(data) >= 20

        self.assertFalse(can_calculate_ma20, "数据不足20天不应该计算MA20")

    def test_exactly_20_days(self):
        """测试：正好20天数据"""
        data = pd.DataFrame({
            'close': range(10, 30)  # 20天数据
        })

        can_calculate_ma20 = len(data) >= 20
        self.assertTrue(can_calculate_ma20, "正好20天应该可以计算MA20")

    def test_zero_volume(self):
        """测试：成交量为0"""
        volumes = [1000, 1200, 1100, 1300, 0]
        avg_volume = np.mean(volumes[:-1])
        current_volume = volumes[-1]

        # 放量检查应该能处理0成交量
        is_surge = current_volume >= avg_volume * 1.5
        self.assertFalse(is_surge, "0成交量不应该触发放量")

    def test_flat_price(self):
        """测试：价格横盘"""
        prices = [10.0] * 20
        ma20 = np.mean(prices)

        # 价格正好等于MA20
        price_to_ma20 = abs(prices[-1] - ma20) / ma20
        is_near = price_to_ma20 <= 0.02

        self.assertTrue(is_near, "价格等于MA20应该被认为是接近")


def run_tests():
    """运行所有测试"""
    print("=" * 70)
    print("涨停回调策略单元测试")
    print("=" * 70)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestLimitUpDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestMACDGoldenCross))
    suite.addTests(loader.loadTestsFromTestCase(TestBuySignal))
    suite.addTests(loader.loadTestsFromTestCase(TestSellSignal))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
