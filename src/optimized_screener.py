# -*- coding: utf-8 -*-
"""
优化的股票池筛选器 - 使用缓存和批量处理
"""
import akshare as ak
import pandas as pd
import json
import os
import sys
from typing import List, Dict, Set
from tqdm import tqdm
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class OptimizedStockScreener:
    """优化的股票池筛选器"""

    # 真正的科技行业（申万分类 + 扩展）
    TECH_INDUSTRIES = [
        "计算机应用", "计算机设备", "半导体", "电子", "通信",
        "软件开发", "互联网服务", "IT服务"
    ]

    # 目标概念板块（作为数据源）- 从config导入
    # 如果需要自定义，可以在这里覆盖
    TARGET_SECTORS = config.TARGET_SECTORS

    def __init__(self):
        # 缓存目录 - 使用config中的配置
        self.CACHE_DIR = config.CACHE_DIR
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self.info_cache = self._load_cache("stock_info_cache.pkl")

    def _load_cache(self, filename: str) -> dict:
        """加载缓存"""
        path = os.path.join(self.CACHE_DIR, filename)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_cache(self, data: dict, filename: str):
        """保存缓存"""
        path = os.path.join(self.CACHE_DIR, filename)
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def get_stock_info_batch(self, codes: List[str], use_cache: bool = True) -> Dict:
        """
        批量获取股票信息（带缓存）

        Args:
            codes: 股票代码列表
            use_cache: 是否使用缓存
        """
        uncached_codes = []
        results = {}

        # 从缓存获取已存在的
        if use_cache:
            for code in codes:
                if code in self.info_cache:
                    results[code] = self.info_cache[code]
                else:
                    uncached_codes.append(code)
        else:
            uncached_codes = codes

        print(f"缓存命中: {len(results)}/{len(codes)}, 需要查询: {len(uncached_codes)}")

        # 批量查询未缓存的
        if uncached_codes:
            for code in tqdm(uncached_codes, desc="查询股票信息"):
                try:
                    info = ak.stock_individual_info_em(symbol=code)
                    if not info.empty:
                        info_dict = {}
                        for _, row in info.iterrows():
                            info_dict[str(row['item'])] = str(row['value'])
                        results[code] = info_dict
                except Exception as e:
                    # 失败的股票标记为None
                    results[code] = None

            # 更新缓存
            if use_cache:
                self.info_cache.update(results)
                self._save_cache(self.info_cache, "stock_info_cache.pkl")

        return results

    def screen_sector_stocks(self, sector_name: str) -> List[Dict]:
        """
        从概念板块筛选真正的科技公司

        Args:
            sector_name: 板块名称（如"人工智能"）
        """
        print("="*80)
        print(f"筛选板块: {sector_name}")
        print("="*80)

        # Step 1: 获取概念板块股票
        print(f"\n[Step 1] 获取{sector_name}概念板块...")
        try:
            sector_df = ak.stock_board_concept_cons_em(symbol=sector_name)
        except:
            print(f"    错误: 无法获取板块 '{sector_name}'")
            return []

        codes = sector_df['代码'].tolist()
        print(f"    概念板块总数: {len(codes)} 只")

        # Step 2: 批量获取股票信息
        print(f"\n[Step 2] 批量获取股票信息...")
        stock_info_dict = self.get_stock_info_batch(codes, use_cache=True)

        # Step 3: 按行业筛选
        print(f"\n[Step 3] 按申万科技行业筛选...")
        tech_stocks = []

        for code, info in stock_info_dict.items():
            if info is None:
                continue

            industry = info.get('行业', '')
            name = info.get('股票简称', '')

            # 检查是否是科技行业
            is_tech = any(ind in industry for ind in self.TECH_INDUSTRIES)

            if is_tech:
                tech_stocks.append({
                    'code': code,
                    'name': name,
                    'industry': industry,
                    'raw_info': info
                })

        print(f"    科技行业筛选: {len(tech_stocks)} 只")

        # Step 4: 获取基本面数据并评分
        print(f"\n[Step 4] 获取基本面数据并评分...")
        from src.data_fetcher import DataFetcher
        fetcher = DataFetcher()

        scored_stocks = []
        for stock in tqdm(tech_stocks, desc="基本面评分"):
            try:
                fund = fetcher.get_stock_fundamentals(stock['code'])
                if fund:
                    # 计算评分
                    roe = fund.get("roe", 0) or 0
                    revenue_growth = fund.get("revenue_growth", 0) or 0
                    profit_growth = fund.get("profit_growth", 0) or 0
                    pe = fund.get("pe", 0) or 50
                    market_cap = fund.get("market_cap", 0) or 0

                    # 市值筛选 > 30亿
                    if market_cap < 3000000000:
                        continue

                    # 评分公式
                    score = (roe * 0.3 + revenue_growth * 0.3 +
                            profit_growth * 0.2 - pe/100 * 0.2)

                    scored_stocks.append({
                        'code': stock['code'],
                        'name': stock['name'],
                        'industry': stock['industry'],
                        'pe': pe,
                        'roe': roe,
                        'revenue_growth': revenue_growth,
                        'profit_growth': profit_growth,
                        'market_cap': market_cap / 100000000,  # 转为亿元
                        'score': score
                    })
            except:
                pass

        # 按评分排序
        scored_stocks.sort(key=lambda x: x['score'], reverse=True)

        print(f"    最终筛选: {len(scored_stocks)} 只")

        return scored_stocks

    def generate_stock_pools(self, output_path: str = None) -> Dict[str, List[str]]:
        """
        生成所有科技股票池

        Args:
            output_path: 输出文件路径
        """
        if output_path is None:
            output_path = os.path.join(config.DATA_DIR, "stock_pools.json")

        all_pools = {}

        for pool_name, concepts in self.TARGET_SECTORS.items():
            print(f"\n\n{'='*80}")
            print(f"生成股票池: {pool_name}")
            print(f"概念: {concepts}")
            print(f"{'='*80}")

            pool_stocks = []
            for concept in concepts:
                print(f"\n处理概念: {concept}")
                stocks = self.screen_sector_stocks(concept)

                if stocks:
                    # 取前30只
                    top_stocks = stocks[:30]
                    pool_stocks.extend(top_stocks)

                    print(f"\n{concept} 前10只:")
                    for s in top_stocks[:10]:
                        print(f"  {s['code']} {s['name']:10s} "
                              f"PE:{s['pe']:>6.1f} ROE:{s['roe']:>5.1f}% "
                              f"评分:{s['score']:>5.2f}")

            # 去重（按代码）
            seen = set()
            unique_stocks = []
            for s in pool_stocks:
                if s['code'] not in seen:
                    seen.add(s['code'])
                    unique_stocks.append(s)

            # 按评分重新排序
            unique_stocks.sort(key=lambda x: x['score'], reverse=True)

            # 保存代码列表
            all_pools[pool_name] = [s['code'] for s in unique_stocks[:50]]

            print(f"\n{pool_name} 最终: {len(all_pools[pool_name])} 只")

        # 保存到文件
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_pools, f, ensure_ascii=False, indent=2)

        print(f"\n\n{'='*80}")
        print(f"已保存到: {output_path}")
        print(f"股票池: {list(all_pools.keys())}")
        for name, codes in all_pools.items():
            print(f"  {name}: {len(codes)} 只")
        print('='*80)

        return all_pools


def main():
    """主程序"""
    screener = OptimizedStockScreener()

    print("="*80)
    print("科学股票池生成器")
    print("="*80)
    print("\n此程序将:")
    print("1. 从概念板块获取股票列表")
    print("2. 使用申万行业分类筛选真正的科技公司")
    print("3. 剔除市值<30亿的小盘股")
    print("4. 按基本面评分排序")
    print("5. 保存到 stock_pools.json")
    print("\n带有缓存机制，第二次运行会更快！")

    # 生成股票池
    pools = screener.generate_stock_pools()

    print("\n完成！")


if __name__ == "__main__":
    main()
