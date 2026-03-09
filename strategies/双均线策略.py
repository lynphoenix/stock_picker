"""双均线策略 - Dual Moving Average Crossover Strategy

当MA5上穿MA20时买入，下穿时卖出
When MA5 crosses above MA20, buy; when it crosses below, sell.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class DualMAStrategy:
    """
    双均线交叉策略
    
    Strategy that generates buy signals when the 5-period moving average crosses above
    the 20-period moving average, and sell signals when it crosses below.
    """

    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize strategy with parameters.
        
        Args:
            params: Dictionary with optional parameters:
                - fast_period: Fast MA period (default: 5)
                - slow_period: Slow MA period (default: 20)
        """
        self.params = params or {}
        self.fast_period = self.params.get('fast_period', 5)
        self.slow_period = self.params.get('slow_period', 20)
        self.positions: List[str] = []
        self.trades: List[Dict] = []

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on dual moving average crossover.
        
        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        Returns:
            DataFrame with columns ['timestamp', 'signal'] where:
                - signal = 1: Buy signal (MA5 crosses above MA20)
                - signal = -1: Sell signal (MA5 crosses below MA20)
                - signal = 0: Hold (no action)
        """
        # Validate input data
        required_columns = ['timestamp', 'close']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Data must contain columns: {required_columns}")
        
        if len(data) < self.slow_period:
            raise ValueError(f"Insufficient data: need at least {self.slow_period} rows")
        
        df = data.copy()
        
        # Calculate moving averages
        df['ma5'] = df['close'].rolling(window=self.fast_period, min_periods=self.fast_period).mean()
        df['ma20'] = df['close'].rolling(window=self.slow_period, min_periods=self.slow_period).mean()
        
        # Initialize signal column
        df['signal'] = 0
        
        # Detect crossover conditions
        # Buy signal: MA5 crosses above MA20 (golden cross)
        ma5_above = df['ma5'] > df['ma20']
        ma5_below_prev = df['ma5'].shift(1) <= df['ma20'].shift(1)
        golden_cross = ma5_above & ma5_below_prev
        
        # Sell signal: MA5 crosses below MA20 (death cross)
        ma5_below = df['ma5'] < df['ma20']
        ma5_above_prev = df['ma5'].shift(1) >= df['ma20'].shift(1)
        death_cross = ma5_below & ma5_above_prev
        
        # Assign signals
        df.loc[golden_cross, 'signal'] = 1   # Buy
        df.loc[death_cross, 'signal'] = -1   # Sell
        
        # Return only timestamp and signal columns
        result = df[['timestamp', 'signal']].copy()
        
        # Ensure no NaN values in signal column
        result['signal'] = result['signal'].fillna(0).astype(int)
        
        return result

    def get_name(self) -> str:
        """
        Return strategy name.
        
        Returns:
            String identifier for the strategy
        """
        return f"DualMA_{self.fast_period}_{self.slow_period}"

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            data: DataFrame with OHLCV data
            initial_capital: Starting capital in dollars
        
        Returns:
            Dictionary with backtest metrics including:
                - total_return: Overall return percentage
                - sharpe_ratio: Risk-adjusted return metric
                - max_drawdown: Maximum peak-to-trough decline
                - win_rate: Percentage of profitable trades
                - trades_count: Total number of trades executed
                - holding_periods: List of holding period lengths
        """
        signals = self.generate_signals(data)
        
        # Merge signals with price data
        df = data.copy()
        df = df.merge(signals, on='timestamp', how='left')
        df['signal'] = df['signal'].fillna(0)
        
        # Initialize tracking variables
        capital = initial_capital
        position = 0  # 0 = no position, 1 = long position
        entry_price = 0
        trades = []
        equity_curve = [initial_capital]
        
        # Simulate trading
        for i in range(len(df)):
            signal = df.iloc[i]['signal']
            price = df.iloc[i]['close']
            timestamp = df.iloc[i]['timestamp']
            
            # Execute buy signal
            if signal == 1 and position == 0:
                position = 1
                entry_price = price
                shares = capital / price
                self.trades.append({
                    'entry_time': timestamp,
                    'entry_price': entry_price,
                    'type': 'buy'
                })
            
            # Execute sell signal
            elif signal == -1 and position == 1:
                exit_price = price
                pnl = (exit_price - entry_price) / entry_price
                capital *= (1 + pnl)
                
                self.trades.append({
                    'exit_time': timestamp,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'type': 'sell'
                })
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return': pnl * 100
                })
                
                position = 0
            
            # Update equity curve
            if position == 1:
                current_value = capital * (price / entry_price)
            else:
                current_value = capital
            equity_curve.append(current_value)
        
        # Calculate metrics
        total_return = ((capital - initial_capital) / initial_capital) * 100
        
        # Calculate Sharpe ratio
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate maximum drawdown
        equity_series = pd.Series(equity_curve)
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        max_drawdown = drawdown.min()
        
        # Calculate win rate
        if trades:
            winning_trades = sum(1 for t in trades if t['pnl'] > 0)
            win_rate = (winning_trades / len(trades)) * 100
        else:
            win_rate = 0
        
        # Calculate holding periods (simplified)
        holding_periods = [i for i in range(len(trades))]
        
        return {
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'win_rate': round(win_rate, 2),
            'trades_count': len(trades),
            'holding_periods': holding_periods,
            'final_capital': round(capital, 2)
        }
