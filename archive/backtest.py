# -*- coding: utf-8 -*-
"""
Backtest Module - Validate stock picking logic with historical data
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


class BacktestEngine:
    """Backtest Engine"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []

    def run_backtest(
        self,
        stock_list: List[Dict],
        start_date: str = "20250101",
        end_date: str = "20251231"
    ) -> Dict:
        """Run backtest"""
        print(f"\n{'='*60}")
        print(f"Backtest Settings")
        print(f"{'='*60}")
        print(f"Period: {start_date} - {end_date}")
        print(f"Initial Capital: {self.initial_capital:,.2f} CNY")
        print(f"Stock Pool: {len(stock_list)} stocks")

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

        codes = [s["code"] for s in stock_list[:20]]
        filtered_df = filter_obj.filter_by_fundamentals(codes, "AI")

        if filtered_df.empty:
            print("    No stocks passed, relaxing filters...")
            config.FUNDAMENTAL_FILTERS["roe_min"] = 0
            config.FUNDAMENTAL_FILTERS["pe_max"] = 200
            config.FUNDAMENTAL_FILTERS["revenue_growth_min"] = -50
            config.FUNDAMENTAL_FILTERS["profit_growth_min"] = -50
            filtered_df = filter_obj.filter_by_fundamentals(codes, "AI")

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

        # 2. Get historical data and simulate trading
        print(f"\n[2] Simulating trading...")

        stock_data = {}
        for stock in qualified_stocks:
            code = stock["code"]
            df = fetcher.get_stock_history(code, start_date=start_date, end_date=end_date)
            if not df.empty:
                df = tech.calculate_all(df)
                stock_data[code] = df

        print(f"    Loaded data for {len(stock_data)} stocks")

        # Simulate trading by date
        dates = pd.date_range(start=start_date, end=end_date, freq="B")

        for i, date in enumerate(dates):
            # Calculate daily total assets
            total_value = self.cash
            for code, pos in self.positions.items():
                if code in stock_data:
                    day_data = stock_data[code][stock_data[code]["date"].dt.date == date.date()]
                    if not day_data.empty:
                        price = day_data.iloc[0]["close"]
                        total_value += pos["shares"] * price

            self.daily_values.append({"date": date, "value": total_value})

            # Check signals weekly
            if i % 5 != 0:
                continue

            # Check sell signals
            for code in list(self.positions.keys()):
                if code in stock_data:
                    df = stock_data[code]
                    hist = df[df["date"] <= date].copy()
                    if len(hist) >= 60:
                        signals = tech.get_latest_signals(hist)
                        pos = self.positions[code]

                        should_sell = False
                        sell_reason = ""

                        if signals.get("macd_signal") == "death_cross":
                            should_sell = True
                            sell_reason = "MACD death cross"
                        elif signals.get("rsi_signal") == "overbought":
                            should_sell = True
                            sell_reason = "RSI overbought"
                        elif signals.get("ma_signal") == "bearish":
                            should_sell = True
                            sell_reason = "Below MA"
                        else:
                            latest = hist.iloc[-1]
                            loss_pct = (latest["close"] - pos["entry_price"]) / pos["entry_price"] * 100
                            if loss_pct <= config.SIGNAL_CONFIG["sell"]["stop_loss"]:
                                should_sell = True
                                sell_reason = f"Stop loss({loss_pct:.1f}%)"

                        if should_sell:
                            latest = hist.iloc[-1]
                            sell_price = latest["close"]
                            sell_amount = pos["shares"] * sell_price
                            self.cash += sell_amount

                            self.trades.append({
                                "date": date,
                                "code": code,
                                "name": pos.get("name", code),
                                "action": "sell",
                                "price": sell_price,
                                "shares": pos["shares"],
                                "amount": sell_amount,
                                "reason": sell_reason,
                                "profit_pct": (sell_price - pos["entry_price"]) / pos["entry_price"] * 100,
                            })

                            del self.positions[code]

            # Check buy signals
            for code in stock_data.keys():
                if code in self.positions:
                    continue

                df = stock_data[code]
                hist = df[df["date"] <= date].copy()
                if len(hist) >= 60:
                    signals = tech.get_latest_signals(hist)

                    buy_score = 0
                    buy_reasons = []

                    if signals.get("macd_signal") == "golden_cross":
                        buy_score += 30
                        buy_reasons.append("MACD golden cross")
                    if signals.get("rsi_signal") == "oversold":
                        buy_score += 25
                        buy_reasons.append("RSI oversold")
                    if signals.get("ma_signal") == "bullish":
                        buy_score += 20
                        buy_reasons.append("Above MA")

                    if buy_score >= 50:
                        latest = hist.iloc[-1]
                        buy_price = latest["close"]
                        buy_amount = self.cash * 0.1
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
                                }

                                self.trades.append({
                                    "date": date,
                                    "code": code,
                                    "name": name,
                                    "action": "buy",
                                    "price": buy_price,
                                    "shares": shares,
                                    "amount": actual_amount,
                                    "reason": ",".join(buy_reasons),
                                })

        # 3. Calculate final results
        print(f"\n[3] Calculating results...")

        # Close all positions
        for code, pos in self.positions.items():
            if code in stock_data:
                final_price = stock_data[code].iloc[-1]["close"]
                sell_amount = pos["shares"] * final_price
                self.cash += sell_amount

                self.trades.append({
                    "date": dates[-1],
                    "code": code,
                    "name": pos.get("name", code),
                    "action": "sell",
                    "price": final_price,
                    "shares": pos["shares"],
                    "amount": sell_amount,
                    "reason": "Backtest end close",
                    "profit_pct": (final_price - pos["entry_price"]) / pos["entry_price"] * 100,
                })

        final_capital = self.cash
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100

        # Calculate win rate
        sell_trades = [t for t in self.trades if t["action"] == "sell"]
        win_trades = [t for t in sell_trades if t.get("profit_pct", 0) > 0]
        win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0

        # Calculate max drawdown
        values = [v["value"] for v in self.daily_values]
        peak = values[0] if values else self.initial_capital
        max_drawdown = 0
        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak * 100 if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        results = {
            "initial_capital": self.initial_capital,
            "final_capital": final_capital,
            "total_return": total_return,
            "total_trades": len(sell_trades),
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "trades": self.trades,
            "daily_values": self.daily_values,
        }

        return results

    def print_results(self, results: Dict):
        """Print backtest results"""
        print(f"\n{'='*60}")
        print(f"Backtest Results")
        print(f"{'='*60}")
        print(f"Initial Capital:  {results['initial_capital']:>12,.2f} CNY")
        print(f"Final Capital:    {results['final_capital']:>12,.2f} CNY")
        print(f"Total Return:     {results['total_return']:>11.2f}%")
        print(f"Total Trades:     {results['total_trades']:>12}")
        print(f"Win Rate:         {results['win_rate']:>11.2f}%")
        print(f"Max Drawdown:     {results['max_drawdown']:>11.2f}%")

        # Show trades
        if results["trades"]:
            print(f"\n{'='*60}")
            print(f"Trade History (Last 20)")
            print(f"{'='*60}")
            trades_df = pd.DataFrame(results["trades"])
            print(trades_df[["date", "name", "code", "action", "price", "shares", "reason"]].tail(20).to_string(index=False))

            # Show profit/loss analysis
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

                # Best and worst trades
                if sell_trades:
                    best = max(sell_trades, key=lambda x: x["profit_pct"])
                    worst = min(sell_trades, key=lambda x: x["profit_pct"])
                    print(f"\nBest Trade: {best['name']}({best['code']}) +{best['profit_pct']:.2f}%")
                    print(f"Worst Trade: {worst['name']}({worst['code']}) {worst['profit_pct']:.2f}%")


def main():
    """Main function"""
    print("="*60)
    print("Stock Picker System - 2025 Backtest")
    print("="*60)

    # Init
    fetcher = DataFetcher()
    backtest = BacktestEngine(initial_capital=100000)

    # Get stock pool
    print("\nPreparing stock pool...")
    ai_stocks = fetcher.get_sector_stocks("人工智能")

    # Build stock list
    stock_list = []
    for code in ai_stocks[:30]:
        stock_list.append({
            "code": code,
            "name": code,
            "sector": "AI",
        })

    # Run backtest
    results = backtest.run_backtest(
        stock_list=stock_list,
        start_date="20250101",
        end_date="20251231"
    )

    # Print results
    backtest.print_results(results)

    print(f"\nBacktest completed!")


if __name__ == "__main__":
    main()
