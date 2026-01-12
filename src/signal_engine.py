# -*- coding: utf-8 -*-
"""
买卖点信号引擎
"""
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.data_fetcher import DataFetcher
from src.technical import TechnicalIndicators
from src.sector_heat import SectorHeat


class SignalEngine:
    """买卖点信号引擎"""

    def __init__(self):
        self.fetcher = DataFetcher()
        self.tech = TechnicalIndicators()
        self.heat = SectorHeat()
        self.cfg = config.SIGNAL_CONFIG

    def analyze_stock(
        self,
        code: str,
        name: str,
        sector: str = "",
        entry_price: Optional[float] = None
    ) -> Dict:
        """
        分析单只股票的买卖信号

        Args:
            code: 股票代码
            name: 股票名称
            sector: 所属板块
            entry_price: 持仓成本价（用于判断止损）

        Returns:
            分析结果字典
        """
        result = {
            "code": code,
            "name": name,
            "sector": sector,
            "price": 0,
            "change_pct": 0,
            "signal": "hold",  # buy/sell/hold
            "signal_strength": 0,  # 信号强度 0-100
            "reasons": [],
            "risks": [],
            "indicators": {},
        }

        try:
            # 获取历史数据
            df = self.fetcher.get_stock_history(code)

            if df.empty:
                result["reasons"].append("无法获取历史数据")
                return result

            # 计算技术指标
            df = self.tech.calculate_all(df)

            # 获取最新数据
            latest = df.iloc[-1]
            result["price"] = float(latest["close"])
            result["change_pct"] = float(latest["close"] / latest["open"] - 1) * 100

            # 获取技术信号
            tech_signals = self.tech.get_latest_signals(df)
            result["indicators"] = {
                "macd": float(latest["MACD"]),
                "dif": float(latest["MACD_DIF"]),
                "dea": float(latest["MACD_DEA"]),
                "rsi": float(latest["RSI"]),
                "ma5": float(latest["MA5"]),
                "ma20": float(latest["MA20"]),
                "ma60": float(latest["MA60"]),
            }

            # 计算板块热度
            sector_heat = 0.5
            if sector:
                sector_heat = self.heat.get_stock_sector_heat(sector)

            # 判断买入信号
            buy_score = 0
            buy_reasons = []

            # 1. MACD金叉
            if tech_signals.get("macd_signal") == "golden_cross":
                buy_score += 30
                buy_reasons.append("MACD金叉")

            # 2. RSI超卖反弹
            if tech_signals.get("rsi_signal") == "oversold":
                buy_score += 25
                buy_reasons.append("RSI超卖")

            # 3. 站上20日均线
            if tech_signals.get("ma_signal") == "bullish":
                buy_score += 20
                buy_reasons.append("站上20日均线")

            # 4. 板块热度
            if sector_heat > self.cfg["buy"]["sector_heat_percentile"]:
                buy_score += int(sector_heat * 25)
                buy_reasons.append(f"板块热度({int(sector_heat*100)}%)")

            # 判断卖出信号
            sell_score = 0
            sell_reasons = []

            # 1. MACD死叉
            if tech_signals.get("macd_signal") == "death_cross":
                sell_score += 30
                sell_reasons.append("MACD死叉")

            # 2. RSI超买
            if tech_signals.get("rsi_signal") == "overbought":
                sell_score += 25
                sell_reasons.append("RSI超买")

            # 3. 跌破20日均线
            if tech_signals.get("ma_signal") == "bearish":
                sell_score += 20
                sell_reasons.append("跌破20日均线")

            # 4. 止损检查
            if entry_price:
                loss_pct = (result["price"] - entry_price) / entry_price * 100
                if loss_pct <= self.cfg["sell"]["stop_loss"]:
                    sell_score += 100  # 止损优先级最高
                    sell_reasons.append(f"触发止损({loss_pct:.1f}%)")

            # 综合判断
            if sell_score >= 60:
                result["signal"] = "sell"
                result["signal_strength"] = min(sell_score, 100)
                result["reasons"] = sell_reasons
            elif buy_score >= 50:
                result["signal"] = "buy"
                result["signal_strength"] = min(buy_score, 100)
                result["reasons"] = buy_reasons
            else:
                result["signal"] = "hold"
                result["signal_strength"] = 0

            # 风险提示
            if tech_signals.get("trend") == "down":
                result["risks"].append("处于下跌趋势")

            if latest["RSI"] > 80:
                result["risks"].append("RSI严重超买")

        except Exception as e:
            result["reasons"].append(f"分析失败: {str(e)}")

        return result

    def analyze_stocks(
        self,
        stock_list: List[Dict],
        entry_prices: Optional[Dict[str, float]] = None
    ) -> List[Dict]:
        """
        批量分析股票

        Args:
            stock_list: [{"code":..., "name":..., "sector":...}, ...]
            entry_prices: {code: entry_price, ...}

        Returns:
            分析结果列表
        """
        results = []

        for stock in stock_list:
            code = stock.get("code")
            name = stock.get("name")
            sector = stock.get("sector", "")

            entry_price = entry_prices.get(code) if entry_prices else None

            result = self.analyze_stock(code, name, sector, entry_price)
            results.append(result)

        # 按信号强度排序
        buy_signals = [r for r in results if r["signal"] == "buy"]
        sell_signals = [r for r in results if r["signal"] == "sell"]

        buy_signals = sorted(buy_signals, key=lambda x: x["signal_strength"], reverse=True)
        sell_signals = sorted(sell_signals, key=lambda x: x["signal_strength"], reverse=True)

        return {
            "buy": buy_signals,
            "sell": sell_signals,
            "hold": [r for r in results if r["signal"] == "hold"],
        }

    def get_signals_summary(self, analysis_result: Dict) -> str:
        """
        生成信号汇总文本（用于通知）
        """
        lines = []
        lines.append("=== 选股信号汇总 ===")
        lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        buy_list = analysis_result.get("buy", [])
        sell_list = analysis_result.get("sell", [])

        lines.append(f"【买入信号】{len(buy_list)}只")
        for stock in buy_list[:10]:
            lines.append(
                f"  {stock['name']}({stock['code']}) "
                f"¥{stock['price']:.2f} "
                f"强度:{stock['signal_strength']} "
                f"{'|'.join(stock['reasons'])}"
            )

        lines.append(f"\n【卖出信号】{len(sell_list)}只")
        for stock in sell_list[:10]:
            lines.append(
                f"  {stock['name']}({stock['code']}) "
                f"¥{stock['price']:.2f} "
                f"强度:{stock['signal_strength']} "
                f"{'|'.join(stock['reasons'])}"
            )

        return "\n".join(lines)


if __name__ == "__main__":
    # 测试代码
    engine = SignalEngine()

    # 测试单股分析
    print("=== 单股分析 ===")
    result = engine.analyze_stock("000001", "平安银行", "银行")
    print(f"信号: {result['signal']}")
    print(f"理由: {result['reasons']}")
    print(f"指标: {result['indicators']}")

    # 测试批量分析
    print("\n=== 批量分析 ===")
    stocks = [
        {"code": "000001", "name": "平安银行", "sector": "银行"},
        {"code": "000002", "name": "万科A", "sector": "房地产"},
    ]
    batch_result = engine.analyze_stocks(stocks)
    print(engine.get_signals_summary(batch_result))
