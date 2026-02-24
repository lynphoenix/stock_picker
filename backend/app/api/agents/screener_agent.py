# -*- coding: utf-8 -*-
"""
ScreenerAgent - 股票筛选Agent
根据用户的自然语言查询筛选符合条件的股票
"""
import re
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class ScreenerAgent:
    """
    股票筛选Agent

    功能:
    1. 解析自然语言筛选条件
    2. 按行业板块筛选
    3. 按财务指标筛选 (ROE, PE, 市值等)
    4. 返回筛选结果
    """

    # 行业板块映射
    SECTOR_MAP = {
        "ai": "AI软件",
        "ai软件": "AI软件",
        "人工智能": "AI软件",
        "软件": "AI软件",
        "半导体": "半导体",
        "芯片": "半导体",
        "机器人": "机器人",
        "新能源": "新能源",
        "医药": "医药",
        "医疗": "医药",
    }

    # 股票板块映射 (从stock_pools.json加载)
    STOCK_POOLS = {}

    def __init__(self):
        self._load_stock_pools()

    def _load_stock_pools(self):
        """加载股票池配置"""
        # Try multiple possible paths
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "stock_pools.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "..", "data", "stock_pools.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "stock_pools.json"),
            "/root/data2/lyn/stock_picker/data/stock_pools.json",
        ]

        for pools_file in possible_paths:
            if os.path.exists(pools_file):
                with open(pools_file, 'r', encoding='utf-8') as f:
                    self.STOCK_POOLS = json.load(f)
                return

        # If not found, use default pools
        self.STOCK_POOLS = {
            "AI软件": ["688256", "300689", "600654", "600666", "600288"],
            "半导体": [],
            "机器人": ["000988", "300124", "300508", "300134", "300747"]
        }

    def can_handle(self, query: str) -> bool:
        """
        判断是否能处理该查询

        Args:
            query: 用户查询

        Returns:
            True if this is a stock screening query
        """
        query = query.lower()
        screening_keywords = ["找", "筛选", "选", "过滤", "符合条件的"]
        stock_keywords = ["股票", "股"]

        has_screening = any(kw in query for kw in screening_keywords)
        has_stock = any(kw in query for kw in stock_keywords)

        return has_screening and has_stock

    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        解析查询条件

        Args:
            query: 用户查询，如 "帮我找AI板块ROE>15%的股票"

        Returns:
            筛选条件字典
        """
        conditions = {
            "sectors": [],
            "roe_min": None,
            "roe_max": None,
            "pe_min": None,
            "pe_max": None,
            "market_cap_min": None,
            "market_cap_max": None,
            "limit": 50
        }

        query_lower = query.lower()

        # 解析行业板块
        for keyword, sector in self.SECTOR_MAP.items():
            if keyword in query_lower:
                if sector not in conditions["sectors"]:
                    conditions["sectors"].append(sector)

        # 解析ROE条件
        roe_match = re.search(r'roe[<>]=?(\d+\.?\d*)', query_lower)
        if roe_match:
            roe_value = float(roe_match.group(1))
            if '>=' in roe_match.group(0):
                conditions["roe_min"] = roe_value
            elif '<=' in roe_match.group(0):
                conditions["roe_max"] = roe_value
            elif '>' in roe_match.group(0):
                conditions["roe_min"] = roe_value
            elif '<' in roe_match.group(0):
                conditions["roe_max"] = roe_value
            else:
                conditions["roe_min"] = roe_value

        # 解析PE条件
        pe_match = re.search(r'pe[<>]=?(\d+\.?\d*)', query_lower)
        if pe_match:
            pe_value = float(pe_match.group(1))
            if '>=' in pe_match.group(0):
                conditions["pe_min"] = pe_value
            elif '<=' in pe_match.group(0):
                conditions["pe_max"] = pe_value
            elif '>' in pe_match.group(0):
                conditions["pe_min"] = pe_value
            elif '<' in pe_match.group(0):
                conditions["pe_max"] = pe_value
            else:
                conditions["pe_max"] = pe_value

        # 解析市值条件 (亿)
        cap_match = re.search(r'市值[<>]=?(\d+\.?\d*)(亿|万元)?', query)
        if cap_match:
            cap_value = float(cap_match.group(1))
            unit = cap_match.group(2)
            if unit == "亿":
                pass  # 默认是亿
            elif unit == "万元":
                cap_value = cap_value / 10000  # 转换为亿
            conditions["market_cap_min"] = cap_value

        # 解析数量限制
        limit_match = re.search(r'前?(\d+)只|最多(\d+)只', query)
        if limit_match:
            limit_value = int(limit_match.group(1) or limit_match.group(2))
            conditions["limit"] = min(limit_value, 50)  # 最多50只

        return conditions

    def screen(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        执行股票筛选

        Args:
            conditions: 筛选条件

        Returns:
            符合条件的股票列表
        """
        results = []

        # 获取所有符合条件的板块的股票
        all_symbols = set()
        for sector in conditions.get("sectors", []):
            if sector in self.STOCK_POOLS:
                all_symbols.update(self.STOCK_POOLS[sector])

        # 如果没有指定板块，返回所有可用股票
        if not all_symbols:
            for sector_stocks in self.STOCK_POOLS.values():
                all_symbols.update(sector_stocks)

        # 模拟筛选 (实际应该查询数据库获取真实财务数据)
        for symbol in list(all_symbols)[:conditions.get("limit", 50)]:
            # 这里使用模拟数据，实际应该从数据库查询
            stock_info = {
                "symbol": symbol,
                "name": self._get_stock_name(symbol),
                "sector": self._get_stock_sector(symbol),
                "roe": self._get_mock_roe(symbol),
                "pe": self._get_mock_pe(symbol),
                "market_cap": self._get_mock_market_cap(symbol),
                "price": self._get_mock_price(symbol),
                "change_pct": self._get_mock_change_pct(symbol)
            }

            # 检查是否满足ROE条件
            if conditions.get("roe_min") is not None:
                if stock_info["roe"] < conditions["roe_min"]:
                    continue

            if conditions.get("roe_max") is not None:
                if stock_info["roe"] > conditions["roe_max"]:
                    continue

            # 检查是否满足PE条件
            if conditions.get("pe_min") is not None:
                if stock_info["pe"] < conditions["pe_min"]:
                    continue

            if conditions.get("pe_max") is not None:
                if stock_info["pe"] > conditions["pe_max"]:
                    continue

            # 检查市值条件
            if conditions.get("market_cap_min") is not None:
                if stock_info["market_cap"] < conditions["market_cap_min"]:
                    continue

            results.append(stock_info)

        return results

    def _get_stock_name(self, symbol: str) -> str:
        """获取股票名称 (简化版)"""
        # 实际应该从数据库查询
        name_map = {
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
        }
        return name_map.get(symbol, f"股票{symbol}")

    def _get_stock_sector(self, symbol: str) -> str:
        """获取股票所属板块"""
        for sector, symbols in self.STOCK_POOLS.items():
            if symbol in symbols:
                return sector
        return "未知"

    def _get_mock_roe(self, symbol: str) -> float:
        """获取模拟ROE值"""
        # 根据股票代码生成固定的模拟值
        hash_val = hash(symbol) % 100
        return round(5 + (hash_val / 100) * 25, 2)  # 5-30% 之间

    def _get_mock_pe(self, symbol: str) -> float:
        """获取模拟PE值"""
        hash_val = hash(symbol) % 200
        return round(10 + (hash_val / 200) * 90, 2)  # 10-100 之间

    def _get_mock_market_cap(self, symbol: str) -> float:
        """获取模拟市值(亿)"""
        hash_val = hash(symbol) % 500
        return round(10 + hash_val, 2)  # 10-510亿

    def _get_mock_price(self, symbol: str) -> float:
        """获取模拟价格"""
        hash_val = hash(symbol) % 1000
        return round(10 + (hash_val / 1000) * 990, 2)

    def _get_mock_change_pct(self, symbol: str) -> float:
        """获取模拟涨跌幅"""
        hash_val = hash(symbol) % 200
        return round(-10 + (hash_val / 200) * 20, 2)  # -10% to +10%

    def format_results(self, stocks: List[Dict[str, Any]], conditions: Dict[str, Any]) -> str:
        """
        格式化筛选结果

        Args:
            stocks: 股票列表
            conditions: 筛选条件

        Returns:
            格式化的结果字符串
        """
        if not stocks:
            return "没有找到符合条件的股票，请尝试放宽筛选条件。"

        # 构建条件描述
        condition_parts = []
        if conditions.get("sectors"):
            condition_parts.append(f"行业: {', '.join(conditions['sectors'])}")
        if conditions.get("roe_min"):
            condition_parts.append(f"ROE > {conditions['roe_min']}%")
        if conditions.get("roe_max"):
            condition_parts.append(f"ROE < {conditions['roe_max']}%")
        if conditions.get("pe_max"):
            condition_parts.append(f"PE < {conditions['pe_max']}")

        condition_str = "，".join(condition_parts) if condition_parts else "全部"

        result = f"根据筛选条件 ({condition_str})，找到 {len(stocks)} 只股票:\n\n"

        for i, stock in enumerate(stocks[:10], 1):  # 最多显示10只
            # 判断ROE是否满足条件
            roe_indicator = "✓" if conditions.get("roe_min") and stock["roe"] >= conditions["roe_min"] else ""

            result += f"{i}. **{stock['name']}** ({stock['symbol']})\n"
            result += f"   - 行业: {stock['sector']}\n"
            result += f"   - ROE: {stock['roe']}%\n"
            result += f"   - PE: {stock['pe']}\n"
            result += f"   - 市值: {stock['market_cap']:.1f}亿\n"
            result += f"   - 价格: {stock['price']:.2f}元\n"
            result += f"   - 涨跌: {stock['change_pct']:+.2f}%\n\n"

        if len(stocks) > 10:
            result += f"... 还有 {len(stocks) - 10} 只股票，请查看完整列表。"

        return result

    async def execute(self, query: str) -> Dict[str, Any]:
        """
        执行股票筛选

        Args:
            query: 用户查询

        Returns:
            执行结果
        """
        # 解析查询条件
        conditions = self.parse_query(query)

        # 执行筛选
        stocks = self.screen(conditions)

        # 格式化结果
        formatted_results = self.format_results(stocks, conditions)

        return {
            "success": True,
            "query": query,
            "conditions": conditions,
            "stocks": stocks,
            "total": len(stocks),
            "formatted_results": formatted_results,
            "suggestions": [
                f"分析{stocks[0]['name']}" if stocks else "请调整筛选条件",
                "帮我找更多条件的股票"
            ] if stocks else []
        }
