"""测试策略 - MA5/MA20 Cross Strategy

当MA5上穿MA20时买入，下穿时卖出
Buy when MA5 crosses above MA20, sell when crosses below
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class TestStrategy:
    """Strategy that buys when MA5 crosses above MA20, sells when it crosses below."""

    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize strategy with parameters.
        
        Args:
            params: Dictionary with optional parameters
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
        Generate trading signals based on MA5 and MA20 crossover.

        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        Returns:
            DataFrame with columns ['timestamp', 'signal'] where signal is:
                1 (buy), -1 (sell), 0 (hold)
        """
        # Validate input data
        required_columns = ['timestamp', 'close']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Data must contain columns: {required_columns}")
        
        # Check if we have enough data
        if len(data) < self.slow_period:
            raise ValueError(
                f"Insufficient data: need at least {self.slow_period} rows, got {len(data)}"
            )
        
        df = data.copy()
        
        # Calculate moving averages
        df['ma5'] = df['close'].rolling(window=self.fast_period, min_periods=self.fast_period).mean()
        df['ma20'] = df['close'].rolling(window=self.slow_period, min_periods=self.slow_period).mean()
        
        # Initialize signal column
        df['signal'] = 0
        
        # Detect crossover: MA5 crosses above MA20 -> Buy signal (1)
        crossover_up = (
            (df['ma5'] > df['ma20']) &
            (df['ma5'].shift(1) <= df['ma20'].shift(1))
        )
        df.loc[crossover_up, 'signal'] = 1
        
        # Detect crossunder: MA5 crosses below MA20 -> Sell signal (-1)
        crossover_down = (
            (df['ma5'] < df['ma20']) &
            (df['ma5'].shift(1) >= df['ma20'].shift(1))
        )
        df.loc[crossover_down, 'signal'] = -1
        
        # Return only timestamp and signal columns
        result = df[['timestamp', 'signal']].copy()
        
        # Fill NaN values with 0 (hold signal)
        result['signal'] = result['signal'].fillna(0).astype(int)
        
        return result

    def get_name(self) -> str:
        """Return strategy name."""
        return f"TestStrategy_MA{self.fast_period}_MA{self.slow_period}"

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """
        Run backtest on historical data.

        Args:
            data: DataFrame with OHLCV data
            initial_capital: Starting capital (default: 100000)

        Returns:
            Dictionary with backtest metrics including:
                - total_return: Total return percentage
                - sharpe_ratio: Sharpe ratio
                - max_drawdown: Maximum drawdown percentage
                - win_rate: Percentage of winning trades
                - trades_count: Total number of trades
                - holding_periods: List of holding periods in days
        """
        # Generate signals
        signals = self.generate_signals(data)
        
        # Merge signals with price data
        df = data.copy()
        df = df.merge(signals, on='timestamp', how='left')
        df['signal'] = df['signal'].fillna(0)
        
        # Initialize tracking variables
        capital = initial_capital
        position = 0  # 0: no position, 1: long position
        entry_price = 0
        trades = []
        equity_curve = [initial_capital]
        holding_periods = []
        
        # Simulate trading
        for i in range(len(df)):
            current_price = df.iloc[i]['close']
            signal = df.iloc[i]['signal']
            
            # Buy signal and no position
            if signal == 1 and position == 0:
                position = 1
                entry_price = current_price
                entry_date = df.iloc[i]['timestamp']
                shares = capital / current_price
                
            # Sell signal and have position
            elif signal == -1 and position == 1:
                position = 0
                exit_price = current_price
                exit_date = df.iloc[i]['timestamp']
                
                # Calculate P&L
                pnl = shares * (exit_price - entry_price)
                capital += pnl
                
                # Record trade
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'return': (exit_price - entry_price) / entry_price
                })
                
                # Calculate holding period
                if isinstance(entry_date, pd.Timestamp) and isinstance(exit_date, pd.Timestamp):
                    holding_periods.append((exit_date - entry_date).days)
            
            # Update equity curve
            if position == 1:
                current_equity = shares * current_price
            else:
                current_equity = capital
            equity_curve.append(current_equity)
        
        # Calculate metrics
        total_return = ((capital - initial_capital) / initial_capital) * 100
        
        # Calculate Sharpe ratio
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() != 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate max drawdown
        equity_series = pd.Series(equity_curve)
        cumulative_max = equity_series.cummax()
        drawdown = (equity_series - cumulative_max) / cumulative_max * 100
        max_drawdown = drawdown.min()
        
        # Calculate win rate
        if trades:
            winning_trades = sum(1 for t in trades if t['pnl'] > 0)
            win_rate = (winning_trades / len(trades)) * 100
        else:
            win_rate = 0
        
        self.trades = trades
        
        return {
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'win_rate': round(win_rate, 2),
            'trades_count': len(trades),
            'holding_periods': holding_periods,
            'final_capital': round(capital, 2),
            'equity_curve': equity_curve
        }
