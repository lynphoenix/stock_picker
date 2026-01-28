# -*- coding: utf-8 -*-
"""
涨停回调策略
策略逻辑：
1. 过去10天内有过涨停（连续涨停不超过3天）
2. MACD月线金叉
3. 股价回调到MA20附近 + 放量 + 阳线 → 买入
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from .base import BaseStrategy


class LimitUpPullbackStrategy(BaseStrategy):
    """
    涨停回调策略

    策略参数：
        LIMIT_UP_DAYS: 涨停回溯天数
        MAX_CONTINUOUS_LIMIT_UP: 最大连续涨停天数（超过则不参与）
        MA_PERIOD: 均线周期
        VOLUME_RATIO: 放量倍数
        MA_TOLERANCE: 价格偏离MA的容忍度
        USE_MACD: 是否使用MACD月线金叉条件
    """

    # 策略参数
    LIMIT_UP_DAYS = 10
    MAX_CONTINUOUS_LIMIT_UP = 3
    MA_PERIOD = 20
    VOLUME_RATIO = 1.5
    MA_TOLERANCE = 0.02  # ±2%
    USE_MACD = False  # 默认不使用MACD金叉条件

    def __init__(self, name: str = "LimitUpPullback"):
        super().__init__(name)
        self.limit_up_cache = {}  # 缓存涨停检测结果

    def has_limit_up_in_period(
        self,
        hist: pd.DataFrame,
        date_idx: int,
        code: str = None
    ) -> bool:
        """
        检查过去N天内是否有过涨停（连续不超过3天）

        Args:
            hist: 历史数据
            date_idx: 当前日期索引
            code: 股票代码

        Returns:
            bool: 是否符合涨停条件
        """
        if not self.validate_data(hist, date_idx):
            return False

        if date_idx < self.LIMIT_UP_DAYS:
            return False

        # 检查缓存
        cache_key = f"{code}_{date_idx}" if code else str(date_idx)
        if cache_key in self.limit_up_cache:
            return self.limit_up_cache[cache_key]

        # 获取过去N天的数据
        recent_data = hist.iloc[date_idx - self.LIMIT_UP_DAYS:date_idx + 1]

        # 计算涨跌幅
        recent_data = recent_data.copy()
        if '涨跌幅' not in recent_data.columns:
            recent_data['涨跌幅'] = recent_data['close'].pct_change() * 100

        # 检查是否有过涨停
        has_limit_up = (recent_data['涨跌幅'] >= 9.5).any()

        if not has_limit_up:
            self.limit_up_cache[cache_key] = False
            return False

        # 检查连续涨停天数
        max_consecutive = 0
        current_consecutive = 0

        for change_pct in recent_data['涨跌幅']:
            if change_pct >= 9.5:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        result = max_consecutive < self.MAX_CONTINUOUS_LIMIT_UP
        self.limit_up_cache[cache_key] = result
        return result

    def check_macd_golden_cross(
        self,
        hist: pd.DataFrame,
        date_idx: int
    ) -> bool:
        """
        检查MACD月线金叉

        Args:
            hist: 历史数据
            date_idx: 当前日期索引

        Returns:
            bool: 是否形成金叉
        """
        if not self.validate_data(hist, date_idx):
            return False

        # 需要足够的数据转换为月线
        if date_idx < 60:  # 需要至少60个交易日
            return False

        try:
            # 获取到当前日期的数据
            current_hist = hist.iloc[:date_idx + 1].copy()

            # 将日线数据转换为月线（每月最后一个交易日）
            current_hist['year_month'] = pd.to_datetime(current_hist['date']).dt.to_period('M')
            monthly = current_hist.groupby('year_month').last().reset_index()

            # 需要至少12个月的数据
            if len(monthly) < 12:
                return False

            # 计算月线MACD
            close_prices = monthly['close'].values

            # EMA12
            ema12 = pd.Series(close_prices).ewm(span=12, adjust=False).mean()
            # EMA26
            ema26 = pd.Series(close_prices).ewm(span=26, adjust=False).mean()
            # DIF
            dif = ema12 - ema26
            # DEA
            dea = dif.ewm(span=9, adjust=False).mean()

            # 检查最近是否形成金叉
            if len(dif) < 2 or len(dea) < 2:
                return False

            # 当前DIF > DEA
            current_cross = dif.iloc[-1] > dea.iloc[-1]
            # 前一个月DIF <= DEA
            prev_cross = dif.iloc[-2] <= dea.iloc[-2]

            return current_cross and prev_cross

        except Exception:
            return False

    def check_buy_signal(
        self,
        hist: pd.DataFrame,
        date_idx: int,
        code: str = None
    ) -> bool:
        """
        检查买入信号

        条件：
        1. 过去10天有涨停（连续不超过3天）
        2. MACD月线金叉（可选，由USE_MACD控制）
        3. 股价接近MA20（±2%）
        4. 阳线
        5. 放量（>5日均量的1.5倍）

        Args:
            hist: 历史数据
            date_idx: 当前日期索引
            code: 股票代码

        Returns:
            bool: 是否产生买入信号
        """
        if not self.validate_data(hist, date_idx):
            return False

        # 检查1：涨停条件
        if not self.has_limit_up_in_period(hist, date_idx, code):
            return False

        # 检查2：MACD金叉（可选）
        if self.USE_MACD:
            if not self.check_macd_golden_cross(hist, date_idx):
                return False

        # 获取当前和前一天数据
        if date_idx < self.MA_PERIOD:
            return False

        current = hist.iloc[date_idx]

        # 计算MA20
        ma20 = hist.iloc[date_idx - self.MA_PERIOD:date_idx + 1]['close'].mean()

        # 检查3：股价接近MA20
        if abs(current['close'] - ma20) / ma20 > self.MA_TOLERANCE:
            return False

        # 检查4：阳线
        if current['close'] <= current['open']:
            return False

        # 检查5：放量
        if date_idx >= 5:
            avg_volume = hist.iloc[date_idx - 5:date_idx]['volume'].mean()
        else:
            avg_volume = hist.iloc[:date_idx]['volume'].mean()

        if current['volume'] < avg_volume * self.VOLUME_RATIO:
            return False

        return True

    def check_sell_signal(
        self,
        hist: pd.DataFrame,
        date_idx: int,
        position: Dict[str, Any]
    ) -> tuple:
        """
        检查卖出信号

        卖出条件：
        1. 跌破MA20 → 清仓
        2. 涨幅≥30%且未减仓 → 减仓1/3
        3. 涨幅≥50%且未减半 → 减仓一半

        Args:
            hist: 历史数据
            date_idx: 当前日期索引
            position: 持仓信息

        Returns:
            tuple: (should_sell, sell_shares, reason)
        """
        if not self.validate_data(hist, date_idx):
            return (False, 0, "数据无效")

        current = hist.iloc[date_idx]
        entry_price = position['entry_price']

        # 计算当前收益率
        profit_pct = (current['close'] - entry_price) / entry_price * 100

        # 计算MA20
        if date_idx >= self.MA_PERIOD:
            ma20 = hist.iloc[date_idx - self.MA_PERIOD:date_idx + 1]['close'].mean()
        else:
            ma20 = current['close']

        # 条件1：跌破MA20 → 清仓
        if current['close'] < ma20:
            return (True, position['shares'], f"跌破MA20 (当前收益: {profit_pct:.1f}%)")

        # 条件2：涨幅≥30% → 减仓1/3
        if profit_pct >= 30 and not position.get('tp30_taken', False):
            sell_shares = position['shares'] // 3
            if sell_shares > 0:
                position['tp30_taken'] = True
                return (True, sell_shares, f"涨幅{profit_pct:.1f}%减仓1/3")

        # 条件3：涨幅≥50% → 减仓一半
        if profit_pct >= 50 and not position.get('tp50_taken', False):
            sell_shares = position['shares'] // 2
            if sell_shares > 0:
                position['tp50_taken'] = True
                return (True, sell_shares, f"涨幅{profit_pct:.1f}%减仓一半")

        return (False, 0, "")

    def get_position_size(
        self,
        cash: float,
        price: float,
        total_value: float
    ) -> int:
        """计算买入数量（默认20%仓位）"""
        import math
        # 防止异常值和NaN
        try:
            if not (price > 0 and cash > 0):
                return 0
            if math.isnan(total_value) or math.isinf(total_value):
                total_value = cash  # 使用现金代替total_value
            position_value = cash * 0.2
            shares = int(position_value / price / 100) * 100
            return shares
        except:
            return 0

    def get_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = super().get_info()
        info.update({
            "parameters": {
                "limit_up_days": self.LIMIT_UP_DAYS,
                "max_continuous_limit_up": self.MAX_CONTINUOUS_LIMIT_UP,
                "ma_period": self.MA_PERIOD,
                "volume_ratio": self.VOLUME_RATIO,
                "ma_tolerance": self.MA_TOLERANCE,
                "use_macd": self.USE_MACD,
            }
        })
        return info
