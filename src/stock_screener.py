# -*- coding: utf-8 -*-
"""
股票池筛选器 - 基于实际数据科学筛选
"""
import akshare as ak
import pandas as pd
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class StockPoolScreener:
    """股票池筛选器 - 科学筛选真正的AI/TMT公司"""

    # 真正的AI/TMT相关申万行业
    SW_INDUSTRIES = [
        "计算机应用",  # 软件开发
        "计算机设备",  # 硬件
        "半导体",      # 芯片
        "电子",         # 电子元件
        "通信",         # 通信设备
    ]

    # AI相关关键词（用于主营业务筛选）
    AI_KEYWORDS = [
        "人工智能", "AI", "AIGC", "大模型", "机器学习",
        "深度学习", "神经网络", "自然语言", "语音识别",
        "计算机视觉", "图像识别", "智能语音", "云计算",
        "大数据", "物联网", "区块链", "虚拟现实",
        "芯片设计", "集成电路", "半导体", "智驾",
        "自动驾驶", "机器人", "自动化", "工业互联网",
    ]

    def __init__(self):
        self.all_stocks = None

    def get_all_stocks(self) -> pd.DataFrame:
        """获取所有A股列表"""
        if self.all_stocks is None:
            from src.data_fetcher import DataFetcher
            fetcher = DataFetcher()
            self.all_stocks = fetcher.get_stock_list()
        return self.all_stocks

    def screen_by_sw_industry(self, industry: str = None) -> List[str]:
        """
        基于申万行业筛选

        Args:
            industry: 申万行业名称（如"计算机应用"）
        """
        print(f"\n[申万行业筛选] 行业: {industry or '全部科技行业'}")

        # 获取股票基本信息
        all_stocks = self.get_all_stocks()

        # 筛选结果
        result_codes = []

        # 遍历所有股票，获取行业信息
        for code in all_stocks['code'].tolist():
            try:
                info = ak.stock_individual_info_em(symbol=code)
                if not info.empty:
                    stock_industry = info[info['item'] == '行业']['value'].values[0] if '行业' in info['item'].values else ''
                    stock_name = info[info['item'] == '股票简称']['value'].values[0] if '股票简称' in info['item'].values else ''

                    # 检查是否匹配目标行业
                    if industry:
                        if industry in stock_industry:
                            result_codes.append(code)
                            # print(f"  ✓ {code} {stock_name}: {stock_industry}")
                    else:
                        # 如果没有指定行业，筛选所有科技相关行业
                        if any(sw in stock_industry for sw in self.SW_INDUSTRIES):
                            result_codes.append(code)
            except:
                continue

        print(f"    筛选结果: {len(result_codes)} 只股票")
        return result_codes

    def screen_by_business(self, codes: List[str], keywords: List[str] = None) -> List[str]:
        """
        基于主营业务描述筛选

        Args:
            codes: 股票代码列表
            keywords: 业务关键词列表
        """
        print(f"\n[主营业务筛选] 关键词数: {len(keywords or self.AI_KEYWORDS)}")

        if keywords is None:
            keywords = self.AI_KEYWORDS

        result = []

        for code in codes:
            try:
                info = ak.stock_individual_info_em(symbol=code)
                if not info.empty:
                    main_business = info[info['item'] == '主营业务']['value'].values[0] if '主营业务' in info['item'].values else ''
                    stock_name = info[info['item'] == '股票简称']['value'].values[0] if '股票简称' in info['item'].values else ''

                    # 检查主营业务是否包含关键词
                    match_count = 0
                    matched_keywords = []
                    for kw in keywords:
                        if kw.lower() in main_business.lower():
                            match_count += 1
                            matched_keywords.append(kw)

                    # 至少匹配2个关键词，或匹配核心AI关键词
                    core_ai_keywords = ['人工智能', 'AI', 'AIGC', '大模型', '机器学习', '深度学习']
                    core_match = any(kw in main_business for kw in core_ai_keywords)

                    if match_count >= 2 or core_match:
                        result.append(code)
                        # print(f"  ✓ {code} {stock_name}: 匹配 {match_count} 个关键词")
            except:
                continue

        print(f"    筛选结果: {len(result)} 只股票")
        return result

    def screen_by_market_cap(self, codes: List[str], min_cap: float = 50) -> List[str]:
        """
        基于市值筛选（剔除小盘股）

        Args:
            codes: 股票代码列表
            min_cap: 最小市值（亿元）
        """
        print(f"\n[市值筛选] 最小市值: {min_cap}亿元")

        from src.data_fetcher import DataFetcher
        fetcher = DataFetcher()

        result = []
        for code in codes:
            try:
                fund = fetcher.get_stock_fundamentals(code)
                if fund and fund.get("market_cap", 0) > 0:
                    cap_yi = fund["market_cap"] / 100000000  # 转换为亿元
                    if cap_yi >= min_cap:
                        result.append(code)
                    # else:
                    #     print(f"  ✗ {code} 市值{cap_yi:.1f}亿 < {min_cap}亿")
            except:
                continue

        print(f"    筛选结果: {len(result)} 只股票")
        return result

    def screen_by_fundamentals(self, codes: List[str]) -> pd.DataFrame:
        """
        基本面筛选

        Args:
            codes: 股票代码列表
        """
        print(f"\n[基本面筛选]")

        from src.fundamentals import FundamentalFilter
        filter_obj = FundamentalFilter()

        # 放宽筛选条件进行筛选
        import config
        original = config.FUNDAMENTAL_FILTERS.copy()
        config.FUNDAMENTAL_FILTERS["roe_min"] = 0
        config.FUNDAMENTAL_FILTERS["pe_max"] = 300
        config.FUNDAMENTAL_FILTERS["revenue_growth_min"] = -100
        config.FUNDAMENTAL_FILTERS["profit_growth_min"] = -100

        result_df = filter_obj.filter_by_fundamentals(codes, "AI")

        # 恢复原始配置
        config.FUNDAMENTAL_FILTERS = original

        print(f"    筛选结果: {len(result_df)} 只股票")
        return result_df

    def comprehensive_screen(
        self,
        industry: str = None,
        min_market_cap: float = 50,
        max_count: int = None
    ) -> List[Dict]:
        """
        综合筛选：真正的AI/TMT公司

        Args:
            industry: 申万行业
            min_market_cap: 最小市值（亿元）
            max_count: 最大返回数量
        """
        print('='*80)
        print('综合筛选：真正的AI/TMT股票池')
        print('='*80)
        print(f"参数: 行业={industry or '科技类'}, 最小市值={min_market_cap}亿")

        # Step 1: 按申万行业筛选
        codes_by_industry = self.screen_by_sw_industry(industry)

        if not codes_by_industry:
            print("\n未找到符合条件的股票，请检查行业参数")
            return []

        # Step 2: 按主营业务筛选
        codes_by_business = self.screen_by_business(codes_by_industry)

        if not codes_by_business:
            print("\n未找到符合条件的股票，请检查关键词")
            return []

        # Step 3: 按市值筛选
        codes_by_cap = self.screen_by_market_cap(codes_by_business, min_market_cap)

        if not codes_by_cap:
            print("\n未找到符合条件的股票")
            return []

        # Step 4: 基本面筛选（用于排序）
        print("\n[基本面评分]")
        from src.data_fetcher import DataFetcher
        fetcher = DataFetcher()

        stocks_with_score = []
        for code in codes_by_cap:
            try:
                fund = fetcher.get_stock_fundamentals(code)
                if fund:
                    stocks_with_score.append({
                        "code": code,
                        "name": fund.get("name", ""),
                        "industry": fund.get("industry", ""),
                        "pe": fund.get("pe", 0),
                        "roe": fund.get("roe", 0),
                        "revenue_growth": fund.get("revenue_growth", 0),
                        "profit_growth": fund.get("profit_growth", 0),
                        "market_cap": fund.get("market_cap", 0),
                    })
            except:
                pass

        # 简单评分：ROE * 0.3 + 营收增长 * 0.3 + 利润增长 * 0.2 - PE/100 * 0.2
        for stock in stocks_with_score:
            roe = stock["roe"] if stock["roe"] else 0
            revenue_growth = stock["revenue_growth"] if stock["revenue_growth"] else 0
            profit_growth = stock["profit_growth"] if stock["profit_growth"] else 0
            pe = stock["pe"] if stock["pe"] and stock["pe"] > 0 else 50

            score = (roe * 0.3 + revenue_growth * 0.3 + profit_growth * 0.2 - pe/100 * 0.2)
            stock["score"] = score

        # 按评分排序
        stocks_with_score.sort(key=lambda x: x["score"], reverse=True)

        if max_count:
            stocks_with_score = stocks_with_score[:max_count]

        # 输出结果
        print(f"\n[最终结果] {len(stocks_with_score)} 只股票")
        print('-'*80)
        for stock in stocks_with_score:
            print(f'  {stock["code"]} {stock["name"]:8s} PE:{stock["pe"]:>6.1f} '
                  f'ROE:{stock["roe"]:>5.1f}% 营收:{stock["revenue_growth"]:>5.1f}% '
                  f'评分:{stock["score"]:>5.2f}')

        return stocks_with_score


def main():
    """测试筛选器"""
    screener = StockPoolScreener()

    # 测试：筛选"计算机应用"行业的真正AI股票
    print("\n" + "="*80)
    print("测试：筛选计算机应用行业中的AI股票")
    print("="*80)

    result = screener.comprehensive_screen(
        industry="计算机应用",
        min_market_cap=30,
        max_count=20
    )

    print(f"\n筛选完成，共 {len(result)} 只股票")

    # 保存结果
    if result:
        import json
        pools = {"AI应用_" + str(len(result)): [s["code"] for s in result]}
        path = "C:/Users/lin/stock_picker/data/stock_pools.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(pools, f, ensure_ascii=False, indent=2)

        print(f"\n已保存到: {path}")


if __name__ == "__main__":
    main()
