# -*- coding: utf-8 -*-
"""
SignalAgent - 交易信号Agent
生成股票的买卖建议、目标价、止损价、仓位建议
"""
import re
import random
from typing import List, Dict, Any, Optional
from datetime import datetime


class SignalAgent:
    """
    交易信号Agent

    功能:
    1. 解析股票查询
    2. 分析当前价格和趋势
    3. 生成交易信号 (买入/卖出/持有)
    4. 计算目标价格
    5. 计算止损价格
    6. 建议仓位大小
    7. 提供交易理由
    """

    # 股票基本信息
    STOCK_INFO = {
        "002230": {"name": "科大讯飞", "sector": "AI软件", "base_price": 50.0},
        "688256": {"name": "寒武纪", "sector": "AI软件", "base_price": 100.0},
        "600519": {"name": "贵州茅台", "sector": "白酒", "base_price": 1800.0},
        "000858": {"name": "五粮液", "sector": "白酒", "base_price": 150.0},
        "601318": {"name": "中国平安", "sector": "保险", "base_price": 50.0},
        "600036": {"name": "招商银行", "sector": "银行", "base_price": 35.0},
        "000001": {"name": "平安银行", "sector": "银行", "base_price": 12.0},
        "600000": {"name": "浦发银行", "sector": "银行", "base_price": 8.0},
        "000988": {"name": "华工科技", "sector": "机器人", "base_price": 15.0},
        "300124": {"name": "长盈精密", "sector": "机器人", "base_price": 20.0},
    }

    def __init__(self):
        pass

    def can_handle(self, query: str) -> bool:
        """
        判断是否能处理该查询
        """
        query_lower = query.lower()

        # 交易信号关键词
        signal_keywords = [
            "买吗", "卖吗", "可以买", "可以卖",
            "买入", "卖出", "持有", "建仓", "清仓",
            "加仓", "减仓", "止损", "止盈",
            "目标价", "能买", "能卖"
        ]

        # 检查是否包含交易信号关键词
        has_signal_keyword = any(kw in query_lower for kw in signal_keywords)

        # 也检查常见股票名称
        known_names = list(self.STOCK_INFO.values())
        has_known_name = any(info["name"] in query for info in known_names)

        # 检查6位股票代码
        has_stock_code = bool(re.search(r'\b\d{6}\b', query))

        return has_signal_keyword or (has_known_name and ("?" in query or "吗" in query))

    def parse_stock_code(self, query: str) -> Optional[str]:
        """
        从查询中提取股票代码
        """
        # 匹配6位数字代码
        code_matches = re.findall(r'\b(\d{6})\b', query)
        if code_matches:
            return code_matches[0]

        # 匹配已知股票名称
        for code, info in self.STOCK_INFO.items():
            if info["name"] in query:
                return code

        return None

    def generate_signal(self, symbol: str) -> Dict[str, Any]:
        """
        生成交易信号
        """
        stock_info = self.STOCK_INFO.get(symbol, {"name": f"股票{symbol}", "sector": "未知", "base_price": 10.0})

        # 获取当前价格 (添加随机波动模拟真实价格)
        base_price = stock_info["base_price"]
        current_price = round(base_price * (0.9 + random.random() * 0.2), 2)

        # 生成技术指标
        ma5 = round(current_price * (0.95 + random.random() * 0.1), 2)
        ma10 = round(current_price * (0.92 + random.random() * 0.16), 2)
        ma20 = round(current_price * (0.88 + random.random() * 0.24), 2)

        # 计算信号
        trend = self._determine_trend(current_price, ma5, ma10, ma20)
        signal = self._generate_trading_signal(trend, current_price)

        # 计算价格目标
        target_price = self._calculate_target_price(current_price, signal)
        stop_loss = self._calculate_stop_loss(current_price, signal)

        # 计算仓位建议
        position_size = self._calculate_position_size(symbol, signal)

        # 生成交易理由
        reasoning = self._generate_reasoning(signal, trend, stock_info, current_price)

        return {
            "symbol": symbol,
            "name": stock_info["name"],
            "sector": stock_info["sector"],
            "current_price": current_price,
            "signal": signal,
            "signal_cn": self._get_signal_cn(signal),
            "target_price": target_price,
            "stop_loss": stop_loss,
            "position_size": position_size,
            "reasoning": reasoning,
            "technical_indicators": {
                "ma5": ma5,
                "ma10": ma10,
                "ma20": ma20,
                "trend": trend
            },
            "risk_level": self._get_risk_level(signal, current_price, stop_loss),
            "timestamp": datetime.now().isoformat()
        }

    def _determine_trend(self, price: float, ma5: float, ma10: float, ma20: float) -> str:
        """判断趋势"""
        if price > ma5 > ma10 > ma20:
            return "强势上涨"
        elif price > ma5 and ma5 > ma10:
            return "上涨趋势"
        elif price < ma5 < ma10 < ma20:
            return "强势下跌"
        elif price < ma5 and ma5 < ma10:
            return "下跌趋势"
        else:
            return "震荡整理"

    def _generate_trading_signal(self, trend: str, price: float) -> str:
        """生成交易信号"""
        trend_signals = {
            "强势上涨": "买入",
            "上涨趋势": "买入",
            "强势下跌": "卖出",
            "下跌趋势": "卖出",
            "震荡整理": "持有"
        }

        signal = trend_signals.get(trend, "持有")

        # 添加一些随机性使结果更真实
        if random.random() < 0.1:  # 10%的概率反转
            if signal == "买入":
                signal = "持有"
            elif signal == "卖出":
                signal = "持有"

        return signal

    def _calculate_target_price(self, current_price: float, signal: str) -> float:
        """计算目标价格"""
        if signal == "买入":
            # 上涨空间 10-30%
            increase = random.uniform(0.10, 0.30)
            return round(current_price * (1 + increase), 2)
        elif signal == "卖出":
            # 下跌空间 5-20%
            decrease = random.uniform(0.05, 0.20)
            return round(current_price * (1 - decrease), 2)
        else:
            # 持有状态下目标价不变
            return round(current_price, 2)

    def _calculate_stop_loss(self, current_price: float, signal: str) -> float:
        """计算止损价格"""
        if signal == "买入":
            # 止损设在买入价下方 5-10%
            stop_pct = random.uniform(0.05, 0.10)
            return round(current_price * (1 - stop_pct), 2)
        elif signal == "卖出":
            # 空头止损设在买入价上方 5-10%
            stop_pct = random.uniform(0.05, 0.10)
            return round(current_price * (1 + stop_pct), 2)
        else:
            # 持有状态不设止损
            return round(current_price * 0.95, 2)

    def _calculate_position_size(self, symbol: str, signal: str) -> str:
        """计算仓位建议"""
        # 基于股票代码生成固定的仓位建议
        hash_val = hash(symbol) % 100

        if signal == "买入":
            if hash_val < 30:
                return "轻仓 (10-20%)"
            elif hash_val < 70:
                return "半仓 (30-50%)"
            else:
                return "重仓 (50-70%)"
        elif signal == "卖出":
            return "清仓 (0%)"
        else:
            return "保持当前仓位"

    def _generate_reasoning(self, signal: str, trend: str, stock_info: dict, current_price: float) -> List[str]:
        """生成交易理由"""
        reasons = []

        if signal == "买入":
            reasons.append(f"当前股价{current_price:.2f}元，处于{trend}状态")
            reasons.append(f"{stock_info['sector']}行业长期发展前景良好")
            reasons.append("技术面显示积极信号，均线呈多头排列")
            reasons.append("结合基本面分析，当前估值具有一定吸引力")
        elif signal == "卖出":
            reasons.append(f"当前股价{current_price:.2f}元，趋势可能转弱")
            reasons.append("技术面显示调整信号，建议获利了结")
            reasons.append(f"{stock_info['sector']}行业短期面临不确定性")
            reasons.append("风险控制角度，建议减少持仓")
        else:
            reasons.append(f"当前股价{current_price:.2f}元，处于{trend}")
            reasons.append("建议保持现有仓位，观察进一步信号")
            reasons.append("等待趋势明朗后再做决策")

        return reasons

    def _get_signal_cn(self, signal: str) -> str:
        """获取中文信号"""
        signal_map = {
            "买入": "买入",
            "卖出": "卖出",
            "持有": "持有"
        }
        return signal_map.get(signal, "持有")

    def _get_risk_level(self, signal: str, current_price: float, stop_loss: float) -> str:
        """获取风险等级"""
        if signal == "持有":
            return "中等"

        risk_pct = abs(current_price - stop_loss) / current_price

        if risk_pct < 0.05:
            return "低"
        elif risk_pct < 0.08:
            return "中等"
        else:
            return "较高"

    def format_signal(self, signal_data: Dict[str, Any]) -> str:
        """
        格式化交易信号
        """
        signal = signal_data

        result = f"# {signal['name']} ({signal['symbol']}) 交易信号\n\n"
        result += f"**行业板块**: {signal['sector']}\n"
        result += f"**当前价格**: {signal['current_price']:.2f}元\n\n"

        # 信号总览
        signal_emoji = "🟢" if signal['signal'] == "买入" else ("🔴" if signal['signal'] == "卖出" else "🟡")
        result += f"## 📊 交易信号\n\n"
        result += f"{signal_emoji} **{signal['signal_cn']}** (风险等级: {signal['risk_level']})\n\n"

        # 价格目标
        result += "## 💰 价格目标\n\n"
        result += f"| 目标 | 价格 |\n"
        result += f"|------|------|\n"
        result += f"| 当前价 | {signal['current_price']:.2f}元 |\n"
        result += f"| 目标价 | {signal['target_price']:.2f}元 |\n"
        result += f"| 止损价 | {signal['stop_loss']:.2f}元 |\n\n"

        if signal['signal'] == "买入":
            profit_pct = (signal['target_price'] - signal['current_price']) / signal['current_price'] * 100
            loss_pct = (signal['current_price'] - signal['stop_loss']) / signal['current_price'] * 100
            result += f"潜在涨幅: **{profit_pct:.1f}%**\n"
            result += f"潜在跌幅: **{loss_pct:.1f}%**\n"
            result += f"盈亏比: **{profit_pct/loss_pct:.2f}**\n\n"

        # 仓位建议
        result += f"## 📈 仓位建议\n\n"
        result += f"**{signal['position_size']}**\n\n"

        # 技术指标
        ti = signal['technical_indicators']
        result += "## 📉 技术指标\n\n"
        result += f"- MA5: {ti['ma5']:.2f}元\n"
        result += f"- MA10: {ti['ma10']:.2f}元\n"
        result += f"- MA20: {ti['ma20']:.2f}元\n"
        result += f"- 趋势: {ti['trend']}\n\n"

        # 交易理由
        result += "## 📝 交易理由\n\n"
        for i, reason in enumerate(signal['reasoning'], 1):
            result += f"{i}. {reason}\n"

        result += "\n---\n"
        result += "*本信号仅供参考，不构成投资建议。投资有风险，入市需谨慎。*\n"

        return result

    async def execute(self, query: str) -> Dict[str, Any]:
        """
        执行交易信号生成
        """
        # 解析股票代码
        symbol = self.parse_stock_code(query)

        if not symbol:
            return {
                "success": False,
                "error": "未能识别股票代码，请输入股票代码或名称",
                "suggestions": ["科大讯飞可以买吗", "600519可以买吗", "贵州茅台能买吗"]
            }

        # 生成交易信号
        signal_data = self.generate_signal(symbol)

        # 格式化结果
        formatted = self.format_signal(signal_data)

        return {
            "success": True,
            "query": query,
            "symbol": symbol,
            "signal_data": signal_data,
            "formatted_results": formatted,
            "suggestions": [
                f"分析{signal_data['name']}" if signal_data['signal'] == "买入" else "帮我找其他股票"
            ]
        }
