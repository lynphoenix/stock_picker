"""量比策略 - Volume Ratio and Moving Average Breakthrough Strategy

前一个交易日量比大于5%小于10%，涨幅大于5%，股价自下而上击穿20日均线
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class VolumeRatioMABreakthroughStrategy:
    """
    策略逻辑：
    1. 前一个交易日量比大于5%小于10% (相对于前5日平均成交量)
    2. 前一个交易日涨幅大于5%
    3. 当日股价自下而上击穿20日均线
    
    买入信号：同时满足以上三个条件
    卖出信号：股价跌破20日均线
    """

    def __init__(self, params: Optional[Dict] = None):
        """
        初始化策略参数
        
        Args:
            params: 策略参数字典，包含：
                - ma_period: 均线周期，默认20
                - volume_lookback: 量比计算的回溯期，默认5
                - volume_ratio_min: 最小量比，默认1.05 (5%)
                - volume_ratio_max: 最大量比，默认1.10 (10%)
                - price_change_min: 最小涨幅，默认0.05 (5%)
        """
        self.params = params or {}
        self.ma_period = self.params.get('ma_period', 20)
        self.volume_lookback = self.params.get('volume_lookback', 5)
        self.volume_ratio_min = self.params.get('volume_ratio_min', 1.05)
        self.volume_ratio_max = self.params.get('volume_ratio_max', 1.10)
        self.price_change_min = self.params.get('price_change_min', 0.05)
        self.positions: List[str] = []
        self.trades: List[Dict] = []

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        Returns:
            DataFrame with columns ['timestamp', 'signal'] where signal is 1 (buy), -1 (sell), 0 (hold)
        """
        df = data.copy()
        
        # 确保数据按时间排序
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 初始化信号列
        df['signal'] = 0
        
        # 计算20日均线
        df['ma20'] = df['close'].rolling(window=self.ma_period).mean()
        
        # 计算前5日平均成交量
        df['avg_volume'] = df['volume'].rolling(window=self.volume_lookback).mean()
        
        # 计算量比 (当日成交量 / 前5日平均成交量)
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        
        # 计算日涨幅 (收盘价 - 开盘价) / 开盘价
        df['price_change'] = (df['close'] - df['open']) / df['open']
        
        # 检测价格是否从下方突破20日均线
        # 前一日收盘价低于均线，当日收盘价高于均线
        df['breakthrough'] = (
            (df['close'] > df['ma20']) & 
            (df['close'].shift(1) <= df['ma20'].shift(1))
        )
        
        # 获取前一日的量比和涨幅
        df['prev_volume_ratio'] = df['volume_ratio'].shift(1)
        df['prev_price_change'] = df['price_change'].shift(1)
        
        # 买入信号条件：
        # 1. 前一日量比在5%-10%之间
        # 2. 前一日涨幅大于5%
        # 3. 当日突破20日均线
        buy_condition = (
            (df['prev_volume_ratio'] >= self.volume_ratio_min) &
            (df['prev_volume_ratio'] <= self.volume_ratio_max) &
            (df['prev_price_change'] >= self.price_change_min) &
            (df['breakthrough'] == True)
        )
        
        df.loc[buy_condition, 'signal'] = 1
        
        # 卖出信号条件：
        # 价格从上方跌破20日均线
        sell_condition = (
            (df['close'] < df['ma20']) & 
            (df['close'].shift(1) >= df['ma20'].shift(1))
        )
        
        df.loc[sell_condition, 'signal'] = -1
        
        # 返回时间戳和信号
        result = df[['timestamp', 'signal']].copy()
        
        return result

    def get_name(self) -> str:
        """返回策略名称"""
        return f"VolumeRatioMA_{self.ma_period}_VR{int(self.volume_ratio_min*100)}-{int(self.volume_ratio_max*100)}_PC{int(self.price_change_min*100)}"

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """
        回测策略
        
        Args:
            data: DataFrame with OHLCV data
            initial_capital: 初始资金
        
        Returns:
            Dictionary with backtest metrics
        """
        signals = self.generate_signals(data)
        df = data.copy()
        df = df.merge(signals, on='timestamp', how='left')
        df['signal'] = df['signal'].fillna(0)
        
        # 初始化回测变量
        capital = initial_capital
        position = 0  # 持仓数量
        trades = []
        equity_curve = []
        
        for idx, row in df.iterrows():
            # 记录当前权益
            current_equity = capital + position * row['close']
            equity_curve.append(current_equity)
            
            # 买入信号
            if row['signal'] == 1 and position == 0:
                # 全仓买入
                position = capital / row['close']
                capital = 0
                trades.append({
                    'type': 'buy',
                    'timestamp': row['timestamp'],
                    'price': row['close'],
                    'quantity': position
                })
            
            # 卖出信号
            elif row['signal'] == -1 and position > 0:
                # 全部卖出
                capital = position * row['close']
                trades.append({
                    'type': 'sell',
                    'timestamp': row['timestamp'],
                    'price': row['close'],
                    'quantity': position,
                    'pnl': capital - initial_capital
                })
                position = 0
        
        # 计算回测指标
        final_equity = capital + position * df.iloc[-1]['close']
        total_return = (final_equity - initial_capital) / initial_capital
        
        # 计算夏普比率
        equity_series = pd.Series(equity_curve)
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = 0.0
        if len(returns) > 0 and returns.std() != 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        
        # 计算最大回撤
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax
        max_drawdown = drawdown.min()
        
        # 计算胜率
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        win_rate = len(winning_trades) / len(trades) if len(trades) > 0 else 0.0
        
        # 计算持仓周期
        holding_periods = []
        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades):
                buy_idx = df[df['timestamp'] == trades[i]['timestamp']].index[0]
                sell_idx = df[df['timestamp'] == trades[i + 1]['timestamp']].index[0]
                holding_periods.append(sell_idx - buy_idx)
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trades_count': len(trades),
            'holding_periods': holding_periods,
            'final_equity': final_equity,
            'trades': trades
        }
