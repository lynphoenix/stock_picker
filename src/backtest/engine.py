# -*- coding: utf-8 -*-
"""
回测引擎
核心回测逻辑
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.base import BaseStrategy
from settings import DEFAULT_INITIAL_CAPITAL, DEFAULT_MAX_POSITIONS


class BacktestEngine:
    """回测引擎"""

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = DEFAULT_INITIAL_CAPITAL,
        max_positions: int = DEFAULT_MAX_POSITIONS
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.max_positions = max_positions

        # 回测状态
        self.cash = initial_capital
        self.positions = {}  # {code: position_info}
        self.trades = []  # 交易记录
        self.daily_values = []  # 每日净值

    def reset(self):
        """重置回测状态"""
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []

    def run(
        self,
        stock_history: Dict[str, pd.DataFrame],
        start_date: str,
        end_date: str,
        stock_categories: Dict[str, Dict] = None,
        progress_callback: Callable = None
    ) -> Dict[str, Any]:
        """
        运行回测

        Args:
            stock_history: 股票历史数据 {code: DataFrame}
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            stock_categories: 股票分类信息 {code: {category: str}}
            progress_callback: 进度回调函数

        Returns:
            回测结果字典
        """
        self.reset()

        # 获取所有交易日期
        all_dates = self._get_trading_dates(stock_history, start_date, end_date)

        if not all_dates:
            return self._get_empty_results()

        # 预处理：为每只股票建立日期索引 (优化版本)
        stock_history_indexed = {}
        for code, hist in stock_history.items():
            # 使用向量化操作创建日期到行索引的映射
            dates = hist['date']
            # 确保日期是datetime类型
            if not pd.api.types.is_datetime64_any_dtype(dates):
                dates = pd.to_datetime(dates)
            # 转换为字符串格式
            date_strings = dates.dt.strftime('%Y%m%d').values
            date_to_idx = dict(zip(date_strings, hist.index))
            stock_history_indexed[code] = {
                'hist': hist,
                'date_idx': date_to_idx
            }

        # 按日期遍历
        for i, date_str in enumerate(all_dates):
            self._process_day(date_str, stock_history_indexed, stock_categories)

            if progress_callback and (i % 10 == 0 or i == len(all_dates) - 1):
                progress_callback(i, len(all_dates), date_str)
                import sys
                sys.stdout.flush()

        # 平掉剩余持仓
        self._close_remaining_positions(stock_history_indexed, all_dates[-1])

        # 计算结果
        return self._calculate_results()

    def _get_trading_dates(
        self,
        stock_history: Dict[str, pd.DataFrame],
        start_date: str,
        end_date: str
    ) -> List[str]:
        """获取所有交易日期"""
        all_dates = set()

        for code, hist in stock_history.items():
            for date in hist['date']:
                date_str = pd.to_datetime(date).strftime('%Y%m%d')
                if start_date <= date_str <= end_date:
                    all_dates.add(date_str)

        return sorted(list(all_dates))

    def _process_day(
        self,
        date_str: str,
        stock_history_indexed: Dict[str, Dict],
        stock_categories: Dict[str, Dict] = None
    ):
        """处理单个交易日"""
        date_obj = datetime.strptime(date_str, '%Y%m%d')

        # 1. 检查卖出
        self._check_sell_signals(date_str, stock_history_indexed)

        # 2. 检查买入
        if len(self.positions) < self.max_positions:
            self._check_buy_signals(
                date_str, stock_history_indexed, stock_categories
            )

        # 3. 计算当日净值
        self._record_daily_value(date_str, stock_history_indexed)

    def _check_sell_signals(
        self,
        date_str: str,
        stock_history_indexed: Dict[str, Dict]
    ):
        """检查卖出信号"""
        codes_to_sell = []

        for code, pos in self.positions.items():
            if code not in stock_history_indexed:
                continue

            stock_data = stock_history_indexed[code]
            hist = stock_data['hist']
            date_to_idx = stock_data['date_idx']

            if date_str not in date_to_idx:
                continue

            date_idx = date_to_idx[date_str]
            day_data = hist.iloc[date_idx]

            # 调用策略检查卖出信号
            should_sell, sell_shares, reason = self.strategy.check_sell_signal(
                hist, date_idx, pos
            )

            if should_sell and sell_shares > 0:
                codes_to_sell.append((code, day_data['close'], sell_shares, reason))

        # 执行卖出
        for code, price, shares, reason in codes_to_sell:
            self._execute_sell(code, price, shares, date_str, reason)

    def _check_buy_signals(
        self,
        date_str: str,
        stock_history_indexed: Dict[str, Dict],
        stock_categories: Dict[str, Dict] = None
    ):
        """检查买入信号"""
        for code in stock_history_indexed.keys():
            if len(self.positions) >= self.max_positions:
                break

            if code in self.positions:
                continue

            stock_data = stock_history_indexed[code]
            hist = stock_data['hist']
            date_to_idx = stock_data['date_idx']

            if date_str not in date_to_idx:
                continue

            date_idx = date_to_idx[date_str]
            day_data = hist.iloc[date_idx]

            # 调用策略检查买入信号
            if self.strategy.check_buy_signal(hist, date_idx, code):
                self._execute_buy(
                    code, day_data, date_str, hist, date_idx, stock_categories, stock_history_indexed
                )

    def _execute_sell(
        self,
        code: str,
        price: float,
        shares: int,
        date_str: str,
        reason: str
    ):
        """执行卖出"""
        if code not in self.positions:
            return

        pos = self.positions[code]
        profit_pct = (price - pos['entry_price']) / pos['entry_price'] * 100

        # 更新现金
        self.cash += shares * price

        # 记录交易
        trade = {
            'date': date_str,
            'code': code,
            'name': code,  # 使用股票代码作为名称
            'action': 'sell',
            'price': price,
            'shares': shares,
            'profit_pct': profit_pct,
            'reason': reason,
            'category': pos.get('category', '其他')
        }
        self.trades.append(trade)

        # 更新或删除持仓
        if shares >= pos['shares']:
            del self.positions[code]
        else:
            pos['shares'] -= shares

    def _execute_buy(
        self,
        code: str,
        day_data: pd.Series,
        date_str: str,
        hist: pd.DataFrame,
        date_idx: int,
        stock_categories: Dict[str, Dict] = None,
        stock_history_indexed: Dict[str, Dict] = None
    ):
        """执行买入"""
        buy_price = day_data['close']

        # 计算买入数量
        total_value = self.cash
        if stock_history_indexed:
            for c, p in self.positions.items():
                if c in stock_history_indexed:
                    stock_data = stock_history_indexed[c]
                    if date_str in stock_data['date_idx']:
                        idx = stock_data['date_idx'][date_str]
                        total_value += p['shares'] * stock_data['hist'].iloc[idx]['close']

        shares = self.strategy.get_position_size(self.cash, buy_price, total_value)

        if shares <= 0:
            return

        buy_amount = shares * buy_price
        if buy_amount > self.cash or buy_amount < 1000:
            return

        # 获取分类信息
        category = '其他'
        if stock_categories and code in stock_categories:
            category = stock_categories[code].get('category', '其他')

        # 扣除现金
        self.cash -= buy_amount

        # 创建持仓
        self.positions[code] = {
            'shares': shares,
            'entry_price': buy_price,
            'entry_date': date_str,
            'name': code,  # 使用股票代码作为名称
            'category': category,
            'tp30_taken': False,
            'tp50_taken': False,
        }

        # 记录交易
        trade = {
            'date': date_str,
            'code': code,
            'name': code,  # 使用股票代码作为名称
            'action': 'buy',
            'price': buy_price,
            'shares': shares,
            'reason': f'{self.strategy.name}买入信号',
            'category': category
        }
        self.trades.append(trade)

    def _record_daily_value(
        self,
        date_str: str,
        stock_history_indexed: Dict[str, Dict]
    ):
        """记录当日净值"""
        total_value = self.cash

        for code, pos in self.positions.items():
            if code in stock_history_indexed:
                stock_data = stock_history_indexed[code]
                if date_str in stock_data['date_idx']:
                    idx = stock_data['date_idx'][date_str]
                    total_value += pos['shares'] * stock_data['hist'].iloc[idx]['close']

        self.daily_values.append({
            'date': date_str,
            'value': total_value
        })

    def _close_remaining_positions(
        self,
        stock_history_indexed: Dict[str, Dict],
        final_date: str
    ):
        """平掉剩余持仓"""
        for code, pos in list(self.positions.items()):
            if code in stock_history_indexed:
                stock_data = stock_history_indexed[code]
                if final_date in stock_data['date_idx']:
                    idx = stock_data['date_idx'][final_date]
                    final_price = stock_data['hist'].iloc[idx]['close']
                    profit_pct = (final_price - pos['entry_price']) / pos['entry_price'] * 100

                    self.cash += pos['shares'] * final_price

                    trade = {
                        'date': final_date,
                        'code': code,
                        'name': code,  # 使用股票代码作为名称
                        'action': 'sell',
                        'price': final_price,
                        'shares': pos['shares'],
                        'profit_pct': profit_pct,
                        'reason': '回测结束',
                        'category': pos.get('category', '其他')
                    }
                    self.trades.append(trade)

                    del self.positions[code]

    def _calculate_results(self) -> Dict[str, Any]:
        """计算回测结果"""
        trades_df = pd.DataFrame(self.trades)

        if trades_df.empty:
            return self._get_empty_results()

        buy_trades = trades_df[trades_df['action'] == 'buy']
        sell_trades = trades_df[trades_df['action'] == 'sell']

        total_return = (self.cash - self.initial_capital) / self.initial_capital * 100

        profit_trades = sell_trades[sell_trades['profit_pct'] > 0]
        loss_trades = sell_trades[sell_trades['profit_pct'] <= 0]
        win_rate = len(profit_trades) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0

        # 计算最大回撤
        max_drawdown = 0
        if self.daily_values:
            values_df = pd.DataFrame(self.daily_values)
            values_df['cummax'] = values_df['value'].cummax()
            values_df['drawdown'] = (values_df['value'] - values_df['cummax']) / values_df['cummax'] * 100
            max_drawdown = values_df['drawdown'].min()

        # 按分类统计
        category_results = defaultdict(list)
        for _, trade in sell_trades.iterrows():
            category = trade.get('category', '其他')
            category_results[category].append(trade['profit_pct'])

        category_stats = {}
        for cat, profits in category_results.items():
            profits_array = np.array(profits)
            category_stats[cat] = {
                'total_trades': len(profits_array),
                'win_rate': (profits_array > 0).sum() / len(profits_array) * 100,
                'avg_profit': profits_array[profits_array > 0].mean() if (profits_array > 0).any() else 0,
                'avg_loss': profits_array[profits_array <= 0].mean() if (profits_array <= 0).any() else 0,
                'total_return': profits_array.sum()
            }

        return {
            'total_return': total_return,
            'final_capital': self.cash,
            'total_trades': len(buy_trades),
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'avg_profit': profit_trades['profit_pct'].mean() if len(profit_trades) > 0 else 0,
            'avg_loss': loss_trades['profit_pct'].mean() if len(loss_trades) > 0 else 0,
            'trades_df': trades_df,
            'daily_values_df': pd.DataFrame(self.daily_values) if self.daily_values else pd.DataFrame(),
            'category_stats': category_stats
        }

    def _get_empty_results(self) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'total_return': 0,
            'final_capital': self.initial_capital,
            'total_trades': 0,
            'win_rate': 0,
            'max_drawdown': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'trades_df': pd.DataFrame(),
            'daily_values_df': pd.DataFrame(),
            'category_stats': {}
        }
