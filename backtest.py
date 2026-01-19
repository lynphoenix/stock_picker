# -*- coding: utf-8 -*-
"""
Backtest Module V4 - Balanced Strategy
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


class BacktestEngineV4:
    """Balanced Backtest Engine - Simplified but Robust"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []

        # ============ V4 BALANCED PARAMETERS ============
        # Simplified and more robust parameters
        self.buy_threshold = 55  # Lowered from 60 for more opportunities
        self.position_size = 0.10  # Fixed 10% per position
        self.max_positions = 5  # Allow more diversification

        # Stop loss (wider to account for gaps)
        self.stop_loss_pct = -10.0  # -10% hard stop
        self.trailing_stop_pct = 4.0  # 4% from peak

        # Take profit
        self.tp_first_pct = 8.0   # First target at +8%
        self.tp_second_pct = 18.0  # Second target at +18%

        # Minimum holding period
        self.min_hold_days = 2

        # Signal weights
        self.signal_weights = {
            "macd_golden_cross": 30,
            "rsi_not_overbought": 15,  # RSI not overbought is also good
            "ma_bullish": 20,
            "volume_confirm": 15,
            "price_near_ma": 10,  # Price near support MA
        }

    def run_backtest(
        self,
        stock_list: List[Dict],
        start_date: str = "20250101",
        end_date: str = "20251231"
    ) -> Dict:
        """Run balanced backtest"""
        print(f"\n{'='*60}")
        print(f"Backtest V4 - Balanced Strategy")
        print(f"{'='*60}")
        print(f"Period: {start_date} - {end_date}")
        print(f"Initial Capital: {self.initial_capital:,.2f} CNY")
        print(f"Stock Pool: {len(stock_list)} stocks")
        print(f"\nV4 Strategy Parameters:")
        print(f"  Buy Threshold: {self.buy_threshold} points")
        print(f"  Position Size: {self.position_size*100}% (fixed)")
        print(f"  Max Positions: {self.max_positions}")
        print(f"  Stop Loss: {self.stop_loss_pct}%")
        print(f"  Trailing Stop: {self.trailing_stop_pct}% from peak")
        print(f"  Take Profit: {self.tp_first_pct}% (1st), {self.tp_second_pct}% (2nd)")

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

        # 1. Fundamental filter (very relaxed)
        print(f"\n[1] Fundamental filtering...")
        filter_obj = FundamentalFilter()

        original_filters = config.FUNDAMENTAL_FILTERS.copy()
        config.FUNDAMENTAL_FILTERS["roe_min"] = 0
        config.FUNDAMENTAL_FILTERS["pe_max"] = 300
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

            # Check signals every 3 days
            if i % 3 != 0:
                continue

            # Check sell signals
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

                # 1. Hard stop loss
                if profit_pct <= self.stop_loss_pct:
                    should_sell = True
                    sell_reason = f"Stop loss({profit_pct:.1f}%)"

                # 2. Trailing stop (only if profit > 3%)
                elif profit_pct > 3 and "peak_price" in pos:
                    drawdown_from_peak = (current_price - pos["peak_price"]) / pos["peak_price"] * 100
                    if drawdown_from_peak <= -self.trailing_stop_pct:
                        should_sell = True
                        sell_reason = f"Trailing stop({drawdown_from_peak:.1f}% from peak)"

                # 3. First take profit (sell 1/3)
                elif profit_pct >= self.tp_first_pct and pos.get("tp1_taken", False) == False:
                    should_sell = True
                    sell_shares = pos["shares"] // 3
                    sell_reason = f"TP1({profit_pct:.1f}%)"
                    pos["tp1_taken"] = True

                # 4. Second take profit (sell 1/3)
                elif profit_pct >= self.tp_second_pct and pos.get("tp2_taken", False) == False:
                    should_sell = True
                    sell_shares = pos["shares"] // 2
                    sell_reason = f"TP2({profit_pct:.1f}%)"
                    pos["tp2_taken"] = True

                # 5. Technical sell (if holding long enough and not in profit)
                elif holding_days >= self.min_hold_days and profit_pct < 2:
                    if signals.get("macd_signal") == "death_cross":
                        should_sell = True
                        sell_reason = "MACD death cross"
                    elif signals.get("ma_signal") == "bearish":
                        should_sell = True
                        sell_reason = "Below MA"

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

                    if sell_shares >= pos["shares"]:
                        del self.positions[code]
                    else:
                        pos["shares"] -= sell_shares

            # Check buy signals
            if len(self.positions) >= self.max_positions:
                continue

            for code in stock_data.keys():
                if code in self.positions:
                    continue

                df = stock_data[code]
                hist = df[df["date"] <= date].copy()
                if len(hist) < 60:
                    continue

                signals = tech.get_latest_signals(hist)
                latest = hist.iloc[-1]

                # Calculate buy score
                buy_score = 0
                buy_reasons = []

                # MACD golden cross (strong signal)
                if signals.get("macd_signal") == "golden_cross":
                    buy_score += self.signal_weights["macd_golden_cross"]
                    buy_reasons.append("MACD golden cross")

                # RSI not overbought (safer entry)
                rsi = latest.get("RSI", 50)
                if rsi < 70:
                    buy_score += self.signal_weights["rsi_not_overbought"]
                    if rsi < 35:
                        buy_reasons.append("RSI oversold")
                    elif rsi < 50:
                        buy_reasons.append("RSI low")

                # MA alignment
                if signals.get("ma_signal") == "bullish":
                    buy_score += self.signal_weights["ma_bullish"]
                    buy_reasons.append("Above MA")
                elif latest["close"] > latest.get("MA60", latest["close"]):
                    # Above long-term MA is also good
                    buy_score += 10
                    buy_reasons.append("Above MA60")

                # Volume confirmation
                if "VOLUME_RATIO" in hist.columns:
                    vol_ratio = latest["VOLUME_RATIO"]
                    if vol_ratio > 1.2:
                        buy_score += self.signal_weights["volume_confirm"]
                        buy_reasons.append(f"Volume({vol_ratio:.1f}x)")

                # Price near support (MA20)
                if "MA20" in hist.columns:
                    ma20 = latest["MA20"]
                    if 0 <= (latest["close"] - ma20) / ma20 * 100 <= 2:
                        buy_score += self.signal_weights["price_near_ma"]
                        buy_reasons.append("Near MA20 support")

                # Trend confirmation (avoid strong downtrend)
                if signals.get("trend") == "down":
                    buy_score -= 15  # Penalty for downtrend

                if buy_score >= self.buy_threshold:
                    buy_price = latest["close"]
                    buy_amount = self.cash * self.position_size

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
                                "tp1_taken": False,
                                "tp2_taken": False,
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
        print(f"Backtest V4 Results")
        print(f"{'='*60}")
        print(f"Initial Capital:  {results['initial_capital']:>12,.2f} CNY")
        print(f"Final Capital:    {results['final_capital']:>12,.2f} CNY")
        print(f"Total Return:     {results['total_return']:>11.2f}%")
        print(f"Total Trades:     {results['total_trades']:>12}")
        print(f"Win Rate:         {results['win_rate']:>11.2f}%")
        print(f"Avg Hold Days:    {results.get('avg_hold_days', 0):>11.1f}")
        print(f"Profit Factor:    {results.get('profit_factor', 0):>11.2f}")
        print(f"Max Drawdown:     {results['max_drawdown']:>11.2f}%")

        if results["trades"]:
            print(f"\n{'='*60}")
            print(f"Trade History (Last 25)")
            print(f"{'='*60}")
            trades_df = pd.DataFrame(results["trades"])
            cols = ["date", "name", "code", "action", "price", "shares", "profit_pct", "reason"]
            available_cols = [c for c in cols if c in trades_df.columns]
            print(trades_df[available_cols].tail(25).to_string(index=False))

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
    """Main function - Use Scientific Stock Pools"""
    print("="*60)
    print("Stock Picker System - 2025 Backtest V4 (Scientific Pools)")
    print("="*60)

    backtest = BacktestEngineV4(initial_capital=100000)

    # Load scientifically screened stock pools
    print("\nLoading scientific stock pools...")
    import json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pools_path = os.path.join(script_dir, "data", "stock_pools.json")

    with open(pools_path, "r", encoding="utf-8") as f:
        pools = json.load(f)

    print(f"Loaded pools: {list(pools.keys())}")

    # Combine all pools for backtest
    stock_list = []
    for pool_name, codes in pools.items():
        print(f"  {pool_name}: {len(codes)} stocks")
        for code in codes:
            stock_list.append({
                "code": code,
                "name": code,
                "sector": pool_name,
            })

    results = backtest.run_backtest(
        stock_list=stock_list,
        start_date="20250101",
        end_date="20251231"
    )

    backtest.print_results(results)

    print(f"\nBacktest V4 with scientific pools completed!")


if __name__ == "__main__":
    main()
