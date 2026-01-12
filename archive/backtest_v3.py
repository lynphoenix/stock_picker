# -*- coding: utf-8 -*-
"""
Backtest Module V3 - Further Optimized Strategy
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_fetcher import DataFetcher
from src.fundamentals import FundamentalFilter
from src.technical import TechnicalIndicators
import config


class BacktestEngineV3:
    """Further Optimized Backtest Engine"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []

        # ============ V3 OPTIMIZED PARAMETERS ============
        # Dynamic position sizing based on signal strength
        self.buy_threshold = 60
        self.max_positions = 4  # Reduced from 5

        # Position sizes based on signal strength
        self.position_sizes = {
            "weak": 0.08,    # 60-70 points: 8%
            "medium": 0.12,  # 70-80 points: 12%
            "strong": 0.18,  # 80+ points: 18%
        }

        # Tighter stops for better risk control
        self.trailing_stop_pct = 3.0   # Reduced from 5%
        self.hard_stop_pct = -6.0       # Reduced from -8%
        self.soft_stop_pct = -4.0       # New: soft stop

        # Partial take profit
        self.tp_partial_pct = 10.0      # Take 50% profit at +10%
        self.tp_full_pct = 20.0         # Full exit at +20%

        # Minimum holding period to avoid churn
        self.min_trade_days = 2

        # Trend filter - only buy in uptrend
        self.require_uptrend = True

        # Market environment filter
        self.max_drawdown_pause = 15.0  # Pause trading if portfolio drawdown > 15%

    def get_market_sentiment(self, stock_data: Dict, date: pd.Timestamp) -> float:
        """
        Calculate overall market sentiment based on all watched stocks
        Returns: 0-100 score (higher = more bullish)
        """
        bullish_count = 0
        total_count = 0

        for code, df in stock_data.items():
            hist = df[df["date"] <= date]
            if len(hist) >= 20:
                latest = hist.iloc[-1]
                # Simple bullish check: price above MA20
                if "MA20" in hist.columns and latest["close"] > latest["MA20"]:
                    bullish_count += 1
                total_count += 1

        return (bullish_count / total_count * 100) if total_count > 0 else 50

    def get_position_size(self, buy_score: int) -> float:
        """Get position size based on signal strength"""
        if buy_score >= 80:
            return self.position_sizes["strong"]
        elif buy_score >= 70:
            return self.position_sizes["medium"]
        else:
            return self.position_sizes["weak"]

    def run_backtest(
        self,
        stock_list: List[Dict],
        start_date: str = "20250101",
        end_date: str = "20251231"
    ) -> Dict:
        """Run optimized backtest"""
        print(f"\n{'='*60}")
        print(f"Backtest V3 - Further Optimized Strategy")
        print(f"{'='*60}")
        print(f"Period: {start_date} - {end_date}")
        print(f"Initial Capital: {self.initial_capital:,.2f} CNY")
        print(f"Stock Pool: {len(stock_list)} stocks")
        print(f"\nV3 Strategy Parameters:")
        print(f"  Buy Threshold: {self.buy_threshold} points")
        print(f"  Position Sizes: Weak={self.position_sizes['weak']*100}%, "
              f"Medium={self.position_sizes['medium']*100}%, "
              f"Strong={self.position_sizes['strong']*100}%")
        print(f"  Max Positions: {self.max_positions}")
        print(f"  Trailing Stop: {self.trailing_stop_pct}%")
        print(f"  Hard Stop: {self.hard_stop_pct}%")
        print(f"  Soft Stop: {self.soft_stop_pct}%")
        print(f"  Take Profit: {self.tp_partial_pct}% (partial), {self.tp_full_pct}% (full)")
        print(f"  Require Uptrend: {self.require_uptrend}")

        fetcher = DataFetcher()
        tech = TechnicalIndicators()

        results = {
            "total_return": 0,
            "total_trades": 0,
            "win_rate": 0,
            "max_drawdown": 0,
            "trades": self.trades,
            "final_capital": 0,
        }

        print(f"\nStarting backtest...")

        # 1. Fundamental filter
        print(f"\n[1] Fundamental filtering...")
        filter_obj = FundamentalFilter()

        original_filters = config.FUNDAMENTAL_FILTERS.copy()
        config.FUNDAMENTAL_FILTERS["roe_min"] = 0
        config.FUNDAMENTAL_FILTERS["pe_max"] = 200
        config.FUNDAMENTAL_FILTERS["revenue_growth_min"] = -100
        config.FUNDAMENTAL_FILTERS["profit_growth_min"] = -100

        codes = [s["code"] for s in stock_list[:40]]
        filtered_df = filter_obj.filter_by_fundamentals(codes, "AI")
        config.FUNDAMENTAL_FILTERS = original_filters

        qualified_stocks = []
        for _, row in filtered_df.iterrows():
            qualified_stocks.append({
                "code": row["code"],
                "name": row["name"],
                "sector": row.get("category", ""),
            })

        print(f"    Qualified: {len(qualified_stocks)} stocks")

        if not qualified_stocks:
            return results

        # 2. Get historical data
        print(f"\n[2] Loading data...")
        stock_data = {}
        for stock in qualified_stocks:
            code = stock["code"]
            df = fetcher.get_stock_history(code, start_date=start_date, end_date=end_date)
            if not df.empty and len(df) >= 60:
                df = tech.calculate_all(df)
                stock_data[code] = df

        print(f"    Loaded data for {len(stock_data)} stocks")

        # 3. Simulate trading
        print(f"\n[3] Simulating trading...")
        dates = pd.date_range(start=start_date, end=end_date, freq="B")

        # Calculate portfolio peak for drawdown-based trading pause
        portfolio_peak = self.initial_capital

        for i, date in enumerate(dates):
            # Calculate daily total assets
            total_value = self.cash
            for code, pos in self.positions.items():
                if code in stock_data:
                    day_data = stock_data[code][stock_data[code]["date"].dt.date == date.date()]
                    if not day_data.empty:
                        price = day_data.iloc[0]["close"]
                        total_value += pos["shares"] * price
                        if price > pos.get("peak_price", pos["entry_price"]):
                            pos["peak_price"] = price

            self.daily_values.append({"date": date, "value": total_value})

            # Update portfolio peak
            if total_value > portfolio_peak:
                portfolio_peak = total_value

            # Calculate portfolio drawdown
            portfolio_dd = (portfolio_peak - total_value) / portfolio_peak * 100

            # Check signals every 2 days (more responsive)
            if i % 2 != 0:
                continue

            # Get market sentiment
            market_sentiment = self.get_market_sentiment(stock_data, date)

            # Check sell signals first
            for code in list(self.positions.keys()):
                if code not in stock_data:
                    continue

                df = stock_data[code]
                hist = df[df["date"] <= date].copy()
                if len(hist) < 60:
                    continue

                signals = tech.get_latest_signals(hist)
                pos = self.positions[code]
                latest = hist.iloc[-1]
                current_price = latest["close"]

                profit_pct = (current_price - pos["entry_price"]) / pos["entry_price"] * 100
                holding_days = (date - pos["entry_date"]).days

                should_sell = False
                sell_reason = ""
                sell_shares = pos["shares"]

                # 1. Hard stop loss (immediate exit)
                if profit_pct <= self.hard_stop_pct:
                    should_sell = True
                    sell_reason = f"Hard stop({profit_pct:.1f}%)"

                # 2. Trailing stop (from peak)
                elif "peak_price" in pos:
                    drawdown_from_peak = (current_price - pos["peak_price"]) / pos["peak_price"] * 100
                    if drawdown_from_peak <= -self.trailing_stop_pct and profit_pct > 2:
                        should_sell = True
                        sell_reason = f"Trailing stop({drawdown_from_peak:.1f}% from peak)"

                # 3. Soft stop (partial exit if declining)
                elif profit_pct < 0 and profit_pct > self.hard_stop_pct:
                    if holding_days >= 5 and signals.get("macd_signal") == "death_cross":
                        should_sell = True
                        sell_shares = pos["shares"] // 2  # Sell half
                        sell_reason = f"Soft stop - partial({profit_pct:.1f}%)"

                # 4. Partial take profit
                elif profit_pct >= self.tp_partial_pct and pos.get("partial_taken", False) == False:
                    should_sell = True
                    sell_shares = pos["shares"] // 2
                    sell_reason = f"TP partial({profit_pct:.1f}%)"
                    pos["partial_taken"] = True  # Mark partial taken

                # 5. Full take profit
                elif profit_pct >= self.tp_full_pct:
                    should_sell = True
                    sell_reason = f"TP full({profit_pct:.1f}%)"

                # 6. Technical sell (only if holding long enough)
                elif holding_days >= self.min_trade_days:
                    if signals.get("macd_signal") == "death_cross" and profit_pct < 3:
                        should_sell = True
                        sell_reason = "MACD death cross"
                    elif signals.get("rsi_signal") == "overbought" and profit_pct > 5:
                        should_sell = True
                        sell_shares = pos["shares"] // 2  # Sell half on overbought
                        sell_reason = "RSI overbought - partial"

                if should_sell:
                    sell_amount = sell_shares * current_price
                    self.cash += sell_amount

                    self.trades.append({
                        "date": date,
                        "code": code,
                        "name": pos.get("name", code),
                        "action": "sell",
                        "price": current_price,
                        "shares": sell_shares,
                        "amount": sell_amount,
                        "reason": sell_reason,
                        "profit_pct": profit_pct,
                        "holding_days": holding_days,
                    })

                    # Update or remove position
                    if sell_shares >= pos["shares"]:
                        del self.positions[code]
                    else:
                        pos["shares"] -= sell_shares

            # Check buy signals
            # Skip if portfolio drawdown is too high
            if portfolio_dd > self.max_drawdown_pause:
                continue

            # Skip if market sentiment is weak
            if market_sentiment < 30:
                continue

            if len(self.positions) >= self.max_positions:
                continue

            for code in stock_data.keys():
                # Skip if already at max position for this stock
                if code in self.positions:
                    continue

                df = stock_data[code]
                hist = df[df["date"] <= date].copy()
                if len(hist) < 60:
                    continue

                signals = tech.get_latest_signals(hist)
                latest = hist.iloc[-1]

                # Trend filter: require uptrend
                if self.require_uptrend and signals.get("trend") != "up":
                    continue

                # Calculate buy score
                buy_score = 0
                buy_reasons = []

                # MACD signals
                if signals.get("macd_signal") == "golden_cross":
                    buy_score += 35
                    buy_reasons.append("MACD golden cross")

                # RSI signals
                if signals.get("rsi_signal") == "oversold":
                    buy_score += 20
                    buy_reasons.append("RSI oversold")
                elif 30 <= latest.get("RSI", 50) <= 50:
                    buy_score += 10  # Neutral RSI is also OK

                # MA alignment
                if signals.get("ma_signal") == "bullish":
                    buy_score += 25
                    buy_reasons.append("Above MA")

                # Volume confirmation
                if "VOLUME_RATIO" in hist.columns:
                    vol_ratio = latest["VOLUME_RATIO"]
                    if vol_ratio > 1.3:
                        buy_score += 15
                        buy_reasons.append(f"Volume({vol_ratio:.1f}x)")

                # Bonus for strong uptrend
                if signals.get("trend") == "up" and latest["RSI"] < 70:
                    buy_score += 10
                    buy_reasons.append("Strong uptrend")

                if buy_score >= self.buy_threshold:
                    buy_price = latest["close"]

                    # Dynamic position sizing
                    position_size = self.get_position_size(buy_score)
                    buy_amount = self.cash * position_size

                    if buy_amount > 1000:
                        shares = int(buy_amount / buy_price / 100) * 100
                        if shares > 0:
                            actual_amount = shares * buy_price
                            self.cash -= actual_amount

                            name = code
                            for s in qualified_stocks:
                                if s["code"] == code:
                                    name = s["name"]
                                    break

                            self.positions[code] = {
                                "shares": shares,
                                "entry_price": buy_price,
                                "entry_date": date,
                                "name": name,
                                "peak_price": buy_price,
                                "buy_score": buy_score,
                                "partial_taken": False,
                            }

                            self.trades.append({
                                "date": date,
                                "code": code,
                                "name": name,
                                "action": "buy",
                                "price": buy_price,
                                "shares": shares,
                                "amount": actual_amount,
                                "reason": f"{buy_score}pt:{','.join(buy_reasons)}",
                            })

                            if len(self.positions) >= self.max_positions:
                                break

        # 4. Close remaining positions
        print(f"\n[4] Closing positions...")
        for code, pos in self.positions.items():
            if code in stock_data:
                final_price = stock_data[code].iloc[-1]["close"]
                sell_amount = pos["shares"] * final_price
                self.cash += sell_amount

                profit_pct = (final_price - pos["entry_price"]) / pos["entry_price"] * 100

                self.trades.append({
                    "date": dates[-1],
                    "code": code,
                    "name": pos.get("name", code),
                    "action": "sell",
                    "price": final_price,
                    "shares": pos["shares"],
                    "amount": sell_amount,
                    "reason": "Backtest end",
                    "profit_pct": profit_pct,
                })

        # 5. Calculate results
        print(f"\n[5] Calculating results...")
        final_capital = self.cash
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100

        sell_trades = [t for t in self.trades if t["action"] == "sell"]
        win_trades = [t for t in sell_trades if t.get("profit_pct", 0) > 0]
        win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0

        # Max drawdown
        values = [v["value"] for v in self.daily_values]
        peak = values[0] if values else self.initial_capital
        max_drawdown = 0
        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak * 100 if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        hold_times = [t.get("holding_days", 0) for t in sell_trades if "holding_days" in t]
        avg_hold_time = np.mean(hold_times) if hold_times else 0

        # Calculate profit factor
        total_profit = sum([t["profit_pct"] for t in win_trades])
        total_loss = abs(sum([t["profit_pct"] for t in sell_trades if t.get("profit_pct", 0) <= 0]))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        results = {
            "initial_capital": self.initial_capital,
            "final_capital": final_capital,
            "total_return": total_return,
            "total_trades": len(sell_trades),
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "avg_hold_days": avg_hold_time,
            "profit_factor": profit_factor,
            "trades": self.trades,
            "daily_values": self.daily_values,
        }

        return results

    def print_results(self, results: Dict):
        """Print backtest results"""
        print(f"\n{'='*60}")
        print(f"Backtest V3 Results")
        print(f"{'='*60}")
        print(f"Initial Capital:  {results['initial_capital']:>12,.2f} CNY")
        print(f"Final Capital:    {results['final_capital']:>12,.2f} CNY")
        print(f"Total Return:     {results['total_return']:>11.2f}%")
        print(f"Total Trades:     {results['total_trades']:>12}")
        print(f"Win Rate:         {results['win_rate']:>11.2f}%")
        print(f"Avg Hold Days:    {results.get('avg_hold_days', 0):>11.1f}")
        print(f"Profit Factor:    {results.get('profit_factor', 0):>11.2f}")
        print(f"Max Drawdown:     {results['max_drawdown']:>11.2f}%")

        # Show trades
        if results["trades"]:
            print(f"\n{'='*60}")
            print(f"Trade History (Last 25)")
            print(f"{'='*60}")
            trades_df = pd.DataFrame(results["trades"])
            cols = ["date", "name", "code", "action", "price", "shares", "profit_pct", "reason"]
            available_cols = [c for c in cols if c in trades_df.columns]
            print(trades_df[available_cols].tail(25).to_string(index=False))

            # Profit/Loss analysis
            sell_trades = [t for t in results["trades"] if t["action"] == "sell" and "profit_pct" in t]
            if sell_trades:
                print(f"\n{'='*60}")
                print(f"Profit/Loss Analysis")
                print(f"{'='*60}")
                profit_trades = [t for t in sell_trades if t["profit_pct"] > 0]
                loss_trades = [t for t in sell_trades if t["profit_pct"] <= 0]

                avg_profit = np.mean([t["profit_pct"] for t in profit_trades]) if profit_trades else 0
                avg_loss = np.mean([t["profit_pct"] for t in loss_trades]) if loss_trades else 0

                print(f"Profit Trades: {len(profit_trades)}, Avg: {avg_profit:.2f}%")
                print(f"Loss Trades: {len(loss_trades)}, Avg: {avg_loss:.2f}%")
                print(f"Profit Factor: {results.get('profit_factor', 0):.2f}")

                if sell_trades:
                    best = max(sell_trades, key=lambda x: x["profit_pct"])
                    worst = min(sell_trades, key=lambda x: x["profit_pct"])
                    print(f"\nBest Trade: {best['name']}({best['code']}) +{best['profit_pct']:.2f}%")
                    print(f"Worst Trade: {worst['name']}({worst['code']}) {worst['profit_pct']:.2f}%")


def main():
    """Main function"""
    print("="*60)
    print("Stock Picker System - 2025 Backtest V3")
    print("="*60)

    fetcher = DataFetcher()
    backtest = BacktestEngineV3(initial_capital=100000)

    print("\nPreparing stock pool...")
    ai_stocks = fetcher.get_sector_stocks("人工智能")

    stock_list = []
    for code in ai_stocks[:50]:
        stock_list.append({
            "code": code,
            "name": code,
            "sector": "AI",
        })

    results = backtest.run_backtest(
        stock_list=stock_list,
        start_date="20250101",
        end_date="20251231"
    )

    backtest.print_results(results)

    print(f"\nBacktest V3 completed!")


if __name__ == "__main__":
    main()
