"""RSI策略 - RSI Overbought/Oversold Strategy"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class RSIStrategy:
    """Strategy that buys when RSI below 30 (oversold), sells when RSI above 70 (overbought)."""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        self.rsi_period = self.params.get('rsi_period', 14)
        self.oversold_threshold = self.params.get('oversold_threshold', 30)
        self.overbought_threshold = self.params.get('overbought_threshold', 70)
        self.positions: List[str] = []
        self.trades: List[Dict] = []

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            data: Price series (typically close prices)
            period: RSI period (default 14)
            
        Returns:
            RSI values as pd.Series
        """
        # Calculate price changes
        delta = data.diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss using exponential moving average
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()
        
        # Calculate relative strength
        rs = avg_gain / avg_loss
        
        # Calculate RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on RSI.
        
        Buy when RSI crosses below oversold threshold (30).
        Sell when RSI crosses above overbought threshold (70).
        """
        df = data.copy()
        
        # Calculate RSI
        df['rsi'] = self.calculate_rsi(df['close'], period=self.rsi_period)
        
        # Initialize signal column
        df['signal'] = 0
        
        # Buy signal: RSI crosses below oversold threshold
        df.loc[
            (df['rsi'] < self.oversold_threshold) & 
            (df['rsi'].shift(1) >= self.oversold_threshold),
            'signal'
        ] = 1
        
        # Sell signal: RSI crosses above overbought threshold
        df.loc[
            (df['rsi'] > self.overbought_threshold) & 
            (df['rsi'].shift(1) <= self.overbought_threshold),
            'signal'
        ] = -1
        
        return df[['timestamp', 'signal']]

    def get_name(self) -> str:
        """Return strategy name."""
        return f"RSI_{self.rsi_period}_{self.oversold_threshold}_{self.overbought_threshold}"

    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """
        Run backtest on historical data.
        
        Args:
            data: DataFrame with OHLCV data
            initial_capital: Starting capital
            
        Returns:
            Dictionary with backtest metrics
        """
        df = data.copy()
        
        # Calculate RSI and signals
        df['rsi'] = self.calculate_rsi(df['close'], period=self.rsi_period)
        df['signal'] = 0
        
        # Generate signals
        df.loc[
            (df['rsi'] < self.oversold_threshold) & 
            (df['rsi'].shift(1) >= self.oversold_threshold),
            'signal'
        ] = 1
        
        df.loc[
            (df['rsi'] > self.overbought_threshold) & 
            (df['rsi'].shift(1) <= self.overbought_threshold),
            'signal'
        ] = -1
        
        # Track positions and calculate returns
        df['position'] = 0
        current_position = 0
        
        for i in range(len(df)):
            if df['signal'].iloc[i] == 1 and current_position == 0:
                current_position = 1
            elif df['signal'].iloc[i] == -1 and current_position == 1:
                current_position = 0
            df.loc[df.index[i], 'position'] = current_position
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['position'].shift(1) * df['returns']
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        
        # Calculate metrics
        total_return = df['cumulative_returns'].iloc[-1] - 1 if len(df) > 0 else 0.0
        
        # Sharpe ratio (assuming 252 trading days per year)
        returns_std = df['strategy_returns'].std()
        sharpe_ratio = (df['strategy_returns'].mean() / returns_std * np.sqrt(252)) if returns_std != 0 else 0.0
        
        # Maximum drawdown
        cumulative = df['cumulative_returns']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0.0
        
        # Count trades
        trades_count = (df['signal'] != 0).sum()
        
        # Win rate
        winning_trades = (df[df['signal'] == -1]['strategy_returns'] > 0).sum()
        total_trades = (df['signal'] == -1).sum()
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Holding periods
        holding_periods = []
        entry_idx = None
        for i in range(len(df)):
            if df['signal'].iloc[i] == 1:
                entry_idx = i
            elif df['signal'].iloc[i] == -1 and entry_idx is not None:
                holding_periods.append(i - entry_idx)
                entry_idx = None
        
        return {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'trades_count': int(trades_count),
            'holding_periods': holding_periods
        }
