# -*- coding: utf-8 -*-
"""
AnalyzerAgent - 股票分析Agent
分析单只或多只股票的基本面、情绪和估值
"""
import re
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class AnalyzerAgent:
    """
    股票分析Agent

    功能:
    1. 解析股票查询
    2. 获取股票基本信息
    3. 计算财务评分
    4. 计算情绪评分
    5. 计算估值评分
    6. 计算综合评分
    """

    # 股票名称映射
    STOCK_NAMES = {
        "688256": "寒武纪",
        "300689": "星辉娱乐",
        "600654": "ST中安",
        "600666": "安宁股份",
        "600288": "中科曙光",
        "002414": "高德红外",
        "002373": "联络互动",
        "002261": "拓维信息",
        "002354": "天娱数科",
        "600571": "信达地产",
        "600728": "中科创达",
        "002214": "高斯贝尔",
        "000988": "华工科技",
        "300124": "长盈精密",
        "300508": "沪宁电梯",
        "300134": "大富科技",
        "300747": "锐科激光",
        "000001": "平安银行",
        "600000": "浦发银行",
        "600519": "贵州茅台",
        "000858": "五粮液",
        "601318": "中国平安",
        "600036": "招商银行",
        "002230": "科大讯飞",
    }

    # 股票行业映射
    STOCK_SECTORS = {
        "688256": "AI软件",
        "300689": "AI软件",
        "600288": "AI软件",
        "002261": "AI软件",
        "600728": "AI软件",
        "002230": "AI软件",  # 科大讯飞
        "000988": "机器人",
        "300124": "机器人",
        "300508": "机器人",
        "300134": "机器人",
        "300747": "机器人",
        "600519": "白酒",
        "000858": "白酒",
        "601318": "保险",
        "600036": "银行",
        "000001": "银行",
        "600000": "银行",
    }

    def __init__(self):
        pass

    def can_handle(self, query: str) -> bool:
        """
        判断是否能处理该查询
        """
        query_lower = query.lower()
        analysis_keywords = ["分析", "诊断", "评测", "评估"]
        stock_keywords = ["股票", "股", "帮我"]

        has_analysis = any(kw in query_lower for kw in analysis_keywords)

        # Check for stock keywords or known stock names
        has_stock = any(kw in query_lower for kw in stock_keywords)

        # Also check for known stock names (without converting to lowercase)
        known_names = list(self.STOCK_NAMES.values())
        has_known_name = any(name in query for name in known_names)

        # Also check name mapping
        name_mapping_values = ["科大讯飞", "寒武纪", "贵州茅台", "五粮液", "中国平安", "招商银行", "平安银行", "浦发银行"]
        has_mapped_name = any(name in query for name in name_mapping_values)

        return has_analysis and (has_stock or has_known_name or has_mapped_name)

    def parse_stock_code(self, query: str) -> List[str]:
        """
        从查询中提取股票代码

        Args:
            query: 用户查询

        Returns:
            股票代码列表
        """
        stocks = []

        # 尝试匹配6位数字代码
        code_matches = re.findall(r'\b(\d{6})\b', query)
        stocks.extend(code_matches)

        # 尝试匹配已知股票名称
        for code, name in self.STOCK_NAMES.items():
            if name in query:
                if code not in stocks:
                    stocks.append(code)

        # 常见股票名称简化匹配
        name_mapping = {
            "科大讯飞": "002230",
            "寒武纪": "688256",
            "贵州茅台": "600519",
            "五粮液": "000858",
            "中国平安": "601318",
            "招商银行": "600036",
            "平安银行": "000001",
            "浦发银行": "600000",
        }

        for name, code in name_mapping.items():
            if name in query:
                if code not in stocks:
                    stocks.append(code)

        return stocks

    def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """
        分析单只股票

        Args:
            symbol: 股票代码

        Returns:
            分析结果
        """
        name = self.STOCK_NAMES.get(symbol, f"股票{symbol}")
        sector = self.STOCK_SECTORS.get(symbol, "未知")

        # 生成模拟数据
        financial_score = self._calculate_financial_score(symbol)
        sentiment_score = self._calculate_sentiment_score(symbol)
        valuation_score = self._calculate_valuation_score(symbol)
        overall_score = round((financial_score * 0.4 + sentiment_score * 0.3 + valuation_score * 0.3), 1)

        # 获取当前价格和涨跌
        price = self._get_mock_price(symbol)
        change_pct = self._get_mock_change_pct(symbol)

        return {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "price": price,
            "change_pct": change_pct,
            "financial_score": financial_score,
            "sentiment_score": sentiment_score,
            "valuation_score": valuation_score,
            "overall_score": overall_score,
            "financial_details": self._get_financial_details(symbol),
            "sentiment_details": self._get_sentiment_details(symbol),
            "valuation_details": self._get_valuation_details(symbol),
            "recommendation": self._get_recommendation(overall_score),
            "risks": self._get_risks(symbol),
            "opportunities": self._get_opportunities(symbol),
        }

    def _calculate_financial_score(self, symbol: str) -> float:
        """计算财务评分"""
        # 基于股票代码生成固定评分
        hash_val = hash(symbol) % 100
        return round(60 + (hash_val / 100) * 35, 1)  # 60-95

    def _calculate_sentiment_score(self, symbol: str) -> float:
        """计算情绪评分"""
        hash_val = hash(symbol + "sentiment") % 100
        return round(55 + (hash_val / 100) * 40, 1)  # 55-95

    def _calculate_valuation_score(self, symbol: str) -> float:
        """计算估值评分"""
        hash_val = hash(symbol + "valuation") % 100
        return round(50 + (hash_val / 100) * 45, 1)  # 50-95

    def _get_financial_details(self, symbol: str) -> Dict[str, Any]:
        """获取财务详情"""
        return {
            "roe": round(5 + (hash(symbol) % 30), 1),
            "gross_margin": round(20 + (hash(symbol + "gm") % 40), 1),
            "net_margin": round(5 + (hash(symbol + "nm") % 20), 1),
            "debt_ratio": round(30 + (hash(symbol + "dr") % 40), 1),
            "revenue_growth": round(-10 + (hash(symbol + "rg") % 50), 1),
            "earnings_growth": round(-5 + (hash(symbol + "eg") % 60), 1),
        }

    def _get_sentiment_details(self, symbol: str) -> Dict[str, Any]:
        """获取情绪详情"""
        return {
            "news_count": hash(symbol + "news") % 100 + 10,
            "positive_ratio": round(50 + (hash(symbol + "pr") % 40), 1),
            "social_mentions": hash(symbol + "sm") % 1000 + 100,
            "institutional_holdings": round(10 + (hash(symbol + "ih") % 40), 1),
            "analyst_rating": ["买入", "增持", "持有", "减持", "卖出"][hash(symbol + "ar") % 5],
        }

    def _get_valuation_details(self, symbol: str) -> Dict[str, Any]:
        """获取估值详情"""
        return {
            "pe": round(10 + (hash(symbol + "pe") % 80), 1),
            "pb": round(1 + (hash(symbol + "pb") % 15), 1),
            "ps": round(1 + (hash(symbol + "ps") % 20), 1),
            "dividend_yield": round(0.5 + (hash(symbol + "dy") % 5), 2),
            "peg": round(0.5 + (hash(symbol + "peg") % 3), 1),
            "market_cap": round(10 + (hash(symbol + "mc") % 500), 1),
        }

    def _get_mock_price(self, symbol: str) -> float:
        """获取模拟价格"""
        hash_val = hash(symbol) % 1000
        return round(10 + (hash_val / 1000) * 990, 2)

    def _get_mock_change_pct(self, symbol: str) -> float:
        """获取模拟涨跌幅"""
        hash_val = hash(symbol) % 200
        return round(-10 + (hash_val / 200) * 20, 2)

    def _get_recommendation(self, overall_score: float) -> str:
        """获取推荐建议"""
        if overall_score >= 85:
            return "强烈推荐"
        elif overall_score >= 75:
            return "推荐"
        elif overall_score >= 65:
            return "谨慎推荐"
        elif overall_score >= 55:
            return "持有"
        else:
            return "建议回避"

    def _get_risks(self, symbol: str) -> List[str]:
        """获取风险提示"""
        risks = [
            "市场系统性风险",
            "行业周期波动",
            "宏观经济不确定性",
        ]

        if hash(symbol) % 3 == 0:
            risks.append("估值偏高风险")
        if hash(symbol + "risk") % 2 == 0:
            risks.append("业绩波动风险")

        return risks

    def _get_opportunities(self, symbol: str) -> List[str]:
        """获取机会提示"""
        opportunities = [
            "行业长期发展前景良好",
        ]

        if hash(symbol) % 2 == 0:
            opportunities.append("估值有望修复")
        if hash(symbol + "opp") % 3 == 0:
            opportunities.append("业绩增长潜力大")

        return opportunities

    def format_analysis(self, analysis: Dict[str, Any]) -> str:
        """
        格式化分析结果
        """
        stock = analysis

        result = f"# {stock['name']} ({stock['symbol']}) 分析报告\n\n"
        result += f"**行业板块**: {stock['sector']}\n"
        result += f"**当前价格**: {stock['price']:.2f}元 ({stock['change_pct']:+.2f}%)\n\n"

        # 评分总览
        result += "## 📊 评分总览\n\n"
        result += f"| 指标 | 评分 | 等级 |\n"
        result += f"|------|------|------|\n"
        result += f"| 综合评分 | **{stock['overall_score']}** | {stock['recommendation']} |\n"
        result += f"| 财务评分 | {stock['financial_score']} | {self._get_score_level(stock['financial_score'])} |\n"
        result += f"| 情绪评分 | {stock['sentiment_score']} | {self._get_score_level(stock['sentiment_score'])} |\n"
        result += f"| 估值评分 | {stock['valuation_score']} | {self._get_score_level(stock['valuation_score'])} |\n\n"

        # 财务详情
        fd = stock['financial_details']
        result += "## 💰 财务分析\n\n"
        result += f"- ROE: {fd['roe']}%\n"
        result += f"- 毛利率: {fd['gross_margin']}%\n"
        result += f"- 净利率: {fd['net_margin']}%\n"
        result += f"- 负债率: {fd['debt_ratio']}%\n"
        result += f"- 营收增长: {fd['revenue_growth']:+.1f}%\n"
        result += f"- 利润增长: {fd['earnings_growth']:+.1f}%\n\n"

        # 情绪分析
        sd = stock['sentiment_details']
        result += "## 📈 情绪分析\n\n"
        result += f"- 新闻数量: {sd['news_count']}\n"
        result += f"- 正面比例: {sd['positive_ratio']}%\n"
        result += f"- 社交讨论: {sd['social_mentions']}次\n"
        result += f"- 机构持仓: {sd['institutional_holdings']}%\n"
        result += f"- 分析师评级: {sd['analyst_rating']}\n\n"

        # 估值分析
        vd = stock['valuation_details']
        result += "## 💵 估值分析\n\n"
        result += f"- 市盈率 (PE): {vd['pe']}\n"
        result += f"- 市净率 (PB): {vd['pb']}\n"
        result += f"- 市销率 (PS): {vd['ps']}\n"
        result += f"- 股息率: {vd['dividend_yield']}%\n"
        result += f"- PEG: {vd['peg']}\n"
        result += f"- 总市值: {vd['market_cap']}亿\n\n"

        # 风险与机会
        result += "## ⚠️ 风险提示\n\n"
        for risk in stock['risks']:
            result += f"- {risk}\n"
        result += "\n"

        result += "## 🌟 机会提示\n\n"
        for opp in stock['opportunities']:
            result += f"- {opp}\n"

        return result

    def _get_score_level(self, score: float) -> str:
        """获取评分等级"""
        if score >= 85:
            return "优秀"
        elif score >= 75:
            return "良好"
        elif score >= 65:
            return "中等"
        elif score >= 55:
            return "及格"
        else:
            return "较差"

    async def execute(self, query: str) -> Dict[str, Any]:
        """
        执行股票分析
        """
        # 解析股票代码
        stocks = self.parse_stock_code(query)

        if not stocks:
            return {
                "success": False,
                "error": "未能识别股票代码，请输入股票代码或名称",
                "suggestions": ["分析科大讯飞", "分析600519", "分析贵州茅台"]
            }

        # 分析每只股票
        analyses = []
        for symbol in stocks[:5]:  # 最多分析5只
            analysis = self.analyze_stock(symbol)
            analyses.append(analysis)

        # 格式化结果
        if len(analyses) == 1:
            formatted = self.format_analysis(analyses[0])
        else:
            formatted = f"# 批量分析报告\n\n共分析 {len(analyses)} 只股票:\n\n"
            for i, a in enumerate(analyses, 1):
                formatted += f"### {i}. {a['name']} ({a['symbol']})\n"
                formatted += f"综合评分: {a['overall_score']} - {a['recommendation']}\n\n"

        return {
            "success": True,
            "query": query,
            "stocks": stocks,
            "analyses": analyses,
            "formatted_results": formatted,
            "suggestions": [
                f"{analyses[0]['name']}可以买吗" if analyses else "帮我找AI板块的股票"
            ]
        }
