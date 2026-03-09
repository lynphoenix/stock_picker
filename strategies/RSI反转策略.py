"""RSI反转策略 - RSI Reversal Strategy"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class RSIReversalStrategy:
    """Strategy that buys when RSI < 30 (oversold) and sells when RSI > 70 (overbought)."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.oversold_threshold = self.params.get('oversold_threshold', 30)
        self.overbought_threshold = self.params.get('overbought_threshold', 70)
        self.positions: List[str] = []
        self.trades: List[Dict] = []

    def calculate_rsi(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            data: Price data series
            period: RSI calculation period
            
        Returns:
            RSI values as pandas Series
        """
        # Calculate price changes
        delta = data.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        
        # Calculate average gains and losses using exponential moving average
        avg_gains = gains.ewm(com=period - 1, min_periods=period).mean()
        avg_losses = losses.ewm(com=period - 1, min_periods=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on RSI levels.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with timestamp and signal columns
        """
        # Validate input data
        if len(data) < self.rsi_period + 1:
            raise ValueError(f"Insufficient data: need at least {self.rsi_period + 1} rows")
        
        required_columns = ['timestamp', 'close']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Data must contain columns: {required_columns}")
        
        df = data.copy()
        
        # Calculate RSI
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        
        # Initialize signal column
        df['signal'] = 0
        
        # Buy signal when RSI crosses below oversold threshold (RSI < 30)
        df.loc[
            (df['rsi'] < self.oversold_threshold) &
            (df['rsi'].shift(1) >= self.oversold_threshold),
            'signal'
        ] = 1
        
        # Sell signal when RSI crosses above overbought threshold (RSI > 70)
        df.loc[
            (df['rsi'] > self.overbought_threshold) &
            (df['rsi'].shift(1) <= self.overbought_threshold),
            'signal'
        ] = -1
        
        return df[['timestamp', 'signal']]

    def get_name(self) -> str:
        """Return strategy name."""
        return f"RSI_Reversal_{self.rsi_period}_{self.oversold_threshold}_{self.overbought_threshold}"

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            data: DataFrame with OHLCV data
            initial_capital: Starting capital
            
        Returns:
            Dictionary with backtest metrics
        """
        signals = self.generate_signals(data)
        df = data.copy()
        df = df.merge(signals, on='timestamp', how='left')
        df['signal'] = df['signal'].fillna(0)
        
        # Initialize backtest variables
        capital = initial_capital
        position = 0  # 0: no position, 1: long position
        shares = 0
        equity_curve = []
        trades = []
        
        for idx, row in df.iterrows():
            # Buy signal and no current position
            if row['signal'] == 1 and position == 0:
                shares = capital / row['close']
                position = 1
                trades.append({
                    'type': 'buy',
                    'timestamp': row['timestamp'],
                    'price': row['close'],
                    'shares': shares
                })
            
            # Sell signal and currently holding position
            elif row['signal'] == -1 and position == 1:
                capital = shares * row['close']
                position = 0
                trades.append({
                    'type': 'sell',
                    'timestamp': row['timestamp'],
                    'price': row['close'],
                    'shares': shares
                })
                shares = 0
            
            # Calculate current equity
            if position == 1:
                current_equity = shares * row['close']
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
        
        # Calculate metrics
        equity_series = pd.Series(equity_curve)
        returns = equity_series.pct_change().dropna()
        
        total_return = (equity_curve[-1] - initial_capital) / initial_capital
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if len(returns) > 0 and returns.std() != 0 else 0.0
        
        # Calculate max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0.0
        
        # Calculate win rate
        buy_trades = [t for t in trades if t['type'] == 'buy']
        sell_trades = [t for t in trades if t['type'] == 'sell']
        
        winning_trades = 0
        holding_periods = []
        
        for i in range(min(len(buy_trades), len(sell_trades))):
            profit = sell_trades[i]['price'] - buy_trades[i]['price']
            if profit > 0:
                winning_trades += 1
            
            # Calculate holding period in days
            if isinstance(buy_trades[i]['timestamp'], pd.Timestamp) and isinstance(sell_trades[i]['timestamp'], pd.Timestamp):
                holding_period = (sell_trades[i]['timestamp'] - buy_trades[i]['timestamp']).days
                holding_periods.append(holding_period)
        
        total_completed_trades = min(len(buy_trades), len(sell_trades))
        win_rate = winning_trades / total_completed_trades if total_completed_trades > 0 else 0.0
        
        self.trades = trades
        
        return {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'trades_count': len(trades),
            'holding_periods': holding_periods
        }
