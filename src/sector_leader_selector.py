# -*- coding: utf-8 -*-
"""
板块龙头筛选器 - 基于活跃度和业绩的双重筛选
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SectorLeaderSelector:
    """
    板块龙头选择器

    筛选逻辑：
    1. 活跃度排名前30%：板块活跃时，个股活跃度排名
    2. 业绩排名前50%：基本面指标综合排名
    3. 取交集
    """

    def __init__(self, lookback_days: int = 60):
        """
        Args:
            lookback_days: 回溯天数，用于识别板块活跃期
        """
        self.lookback_days = lookback_days

    def get_sector_active_stocks(
        self,
        sector_name: str,
        start_date: str = None,
        end_date: str = None
    ) -> pd.DataFrame:
        """
        获取板块成分股及历史数据

        Args:
            sector_name: 板块名称
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            包含历史行情的DataFrame
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%Y%m%d")

        print(f"\n{'='*70}")
        print(f"分析板块: {sector_name}")
        print(f"时间范围: {start_date} - {end_date}")
        print(f"{'='*70}")

        # 获取板块成分股
        print(f"\n[1] 获取板块成分股...")
        try:
            sector_df = ak.stock_board_concept_cons_em(symbol=sector_name)
        except Exception as e:
            print(f"    错误: 无法获取板块 '{sector_name}': {e}")
            return pd.DataFrame()

        if sector_df.empty:
            print(f"    警告: 板块 '{sector_name}' 没有成分股数据")
            return pd.DataFrame()

        codes = sector_df['代码'].tolist()
        print(f"    成分股数量: {len(codes)}")

        # 限制数量，避免过多API请求
        if len(codes) > 100:
            print(f"    警告: 成分股过多，限制为前100只")
            codes = codes[:100]

        # 获取板块指数历史数据（用于判断活跃期）
        print(f"\n[2] 获取板块指数历史数据...")
        try:
            # 获取板块历史行情
            sector_history = ak.stock_board_concept_name_em(symbol=sector_name)
            if sector_history is not None and not sector_history.empty:
                # 识别活跃期：板块涨幅 > 3% 或 成交额放大
                if '涨跌幅' in sector_history.columns:
                    sector_history['涨跌幅'] = pd.to_numeric(sector_history['涨跌幅'], errors='coerce')
                    active_days = sector_history[sector_history['涨跌幅'] > 2.0]
                    print(f"    活跃日数量: {len(active_days)}/{len(sector_history)}")
                else:
                    active_days = pd.DataFrame()
            else:
                active_days = pd.DataFrame()
        except Exception as e:
            print(f"    警告: 无法获取板块指数数据: {e}")
            active_days = pd.DataFrame()

        # 获取个股历史数据
        print(f"\n[3] 获取个股历史数据...")
        stocks_data = {}

        for i, code in enumerate(codes):
            try:
                # 确定交易所
                exchange = "sz" if code.startswith("0") or code.startswith("3") else "sh"

                hist = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )

                if hist is not None and not hist.empty:
                    # 重命名列
                    hist = hist.rename(columns={
                        "日期": "date",
                        "开盘": "open",
                        "收盘": "close",
                        "最高": "high",
                        "最低": "low",
                        "成交量": "volume",
                        "成交额": "amount",
                        "涨跌幅": "change_pct",
                        "换手率": "turnover"
                    })

                    # 计算活跃度指标
                    hist['avg_amount'] = hist['amount'].rolling(5).mean()
                    hist['amount_ratio'] = hist['amount'] / hist['avg_amount']

                    stocks_data[code] = hist

                if (i + 1) % 20 == 0:
                    print(f"    进度: {i+1}/{len(codes)}")

            except Exception as e:
                # 跳过失败的股票
                continue

        print(f"    成功获取: {len(stocks_data)}/{len(codes)}")

        # 计算活跃度排名
        print(f"\n[4] 计算活跃度排名...")
        activity_scores = {}

        for code, hist in stocks_data.items():
            # 活跃度 = 平均换手率 × 平均成交额比率
            avg_turnover = hist['turnover'].mean() if 'turnover' in hist.columns else 0
            avg_amount_ratio = hist['amount_ratio'].mean() if 'amount_ratio' in hist.columns else 1

            # 综合活跃度得分
            activity_score = avg_turnover * avg_amount_ratio
            activity_scores[code] = activity_score

        # 排名
        sorted_activity = sorted(activity_scores.items(), key=lambda x: x[1], reverse=True)

        # 获取股票基本信息（名称、最新价等）
        print(f"\n[5] 获取股票基本信息...")
        stock_info = []

        # 使用实时行情获取最新信息
        try:
            spot_df = ak.stock_zh_a_spot_em()
            spot_dict = dict(zip(spot_df['代码'], spot_df[['名称', '最新价', '总市值', '市盈率-动态']].values))
        except:
            spot_dict = {}

        for code, score in sorted_activity:
            try:
                # 优先使用实时行情数据
                if code in spot_dict:
                    name, price, market_cap, pe = spot_dict[code]
                    price = float(price) if price not in ['-', '', None] else 0
                    market_cap = float(market_cap) if market_cap not in ['-', '', None] else 0
                    pe = self._parse_float(pe)
                else:
                    # 备用：从individual_info获取
                    info = ak.stock_individual_info_em(symbol=code)
                    if info is not None and not info.empty:
                        info_dict = dict(zip(info['item'], info['value']))
                        name = info_dict.get('股票简称', '')
                        price = self._parse_float(info_dict.get('最新价', 0))
                        market_cap = self._parse_float(info_dict.get('总市值', 0))
                        pe = self._parse_float(info_dict.get('市盈率-动态', 0))
                    else:
                        continue

                stock_info.append({
                    'code': code,
                    'name': str(name),
                    'price': price,
                    'market_cap': market_cap,
                    'pe': pe,
                    'activity_score': score,
                    'activity_rank': len(sorted_activity) - [c for c, _ in sorted_activity].index(code)
                })
            except Exception as e:
                # 如果获取信息失败，跳过
                continue

        result_df = pd.DataFrame(stock_info)

        if not result_df.empty:
            # 计算活跃度排名百分位
            result_df['activity_percentile'] = result_df['activity_rank'] / len(result_df)

        return result_df

    def get_fundamental_scores(self, codes: List[str]) -> Dict[str, float]:
        """
        获取基本面评分

        Args:
            codes: 股票代码列表

        Returns:
            {代码: 基本面评分}
        """
        from src.data_fetcher import DataFetcher

        fetcher = DataFetcher()
        scores = {}

        print(f"\n[6] 获取基本面数据...")

        for i, code in enumerate(codes):
            try:
                fund = fetcher.get_stock_fundamentals(code)
                if fund:
                    # 基本面评分 = ROE × 0.4 + 营收增速 × 0.3 + 利润增速 × 0.3
                    roe = fund.get("roe", 0) or 0
                    revenue_growth = fund.get("revenue_growth", 0) or 0
                    profit_growth = fund.get("profit_growth", 0) or 0

                    # 标准化处理
                    score = (roe * 0.4 + revenue_growth * 0.3 + profit_growth * 0.3)
                    scores[code] = score

                if (i + 1) % 20 == 0:
                    print(f"    进度: {i+1}/{len(codes)}")

            except:
                continue

        return scores

    def select_sector_leaders(
        self,
        sector_name: str,
        activity_threshold: float = 0.3,
        fundamental_threshold: float = 0.5,
        max_stocks: int = 30
    ) -> List[Dict]:
        """
        筛选板块龙头

        Args:
            sector_name: 板块名称
            activity_threshold: 活跃度阈值（前30% = 0.3）
            fundamental_threshold: 业绩阈值（前50% = 0.5）
            max_stocks: 最大返回数量

        Returns:
            筛选后的股票列表
        """
        # 获取活跃度数据
        df = self.get_sector_active_stocks(sector_name)

        if df.empty:
            print(f"\n错误: 无法获取板块 '{sector_name}' 的数据")
            return []

        # 获取基本面评分
        fundamental_scores = self.get_fundamental_scores(df['code'].tolist())

        # 添加基本面评分到DataFrame
        df['fundamental_score'] = df['code'].map(fundamental_scores)

        # 计算基本面排名
        df['fundamental_rank'] = df['fundamental_score'].rank(ascending=False, method='min')
        df['fundamental_percentile'] = 1 - (df['fundamental_rank'] - 1) / len(df)

        # 筛选
        print(f"\n{'='*70}")
        print(f"筛选结果")
        print(f"{'='*70}")

        # 活跃度前30%
        activity_qualified = df[df['activity_percentile'] >= (1 - activity_threshold)]
        print(f"\n活跃度前{int(activity_threshold*100)}%: {len(activity_qualified)} 只")

        # 业绩前50%
        fundamental_qualified = df[df['fundamental_percentile'] >= (1 - fundamental_threshold)]
        print(f"业绩前{int(fundamental_threshold*100)}%: {len(fundamental_qualified)} 只")

        # 取交集
        qualified_codes = set(activity_qualified['code']) & set(fundamental_qualified['code'])
        result_df = df[df['code'].isin(qualified_codes)].copy()

        # 按活跃度和业绩综合得分排序
        result_df['combined_score'] = (
            result_df['activity_percentile'] * 0.5 +
            result_df['fundamental_percentile'] * 0.5
        )
        result_df = result_df.sort_values('combined_score', ascending=False)

        print(f"\n最终筛选（交集）: {len(result_df)} 只")

        # 限制数量
        result_df = result_df.head(max_stocks)

        # 格式化输出
        print(f"\n返回数量: {len(result_df)} 只")
        print(f"\n{'-'*70}")
        print(f"{'代码':<8} {'名称':<10} {'价格':>8} {'市值':>10} {'活跃度%':>8} {'业绩%':>8}")
        print(f"{'-'*70}")

        results = []
        for _, row in result_df.iterrows():
            market_cap_yi = row['market_cap'] / 100000000
            print(f"{row['code']:<8} {row['name']:<10} {row['price']:>8.2f} {market_cap_yi:>10.1f} "
                  f"{row['activity_percentile']*100:>7.1f}% {row['fundamental_percentile']*100:>7.1f}%")

            results.append({
                'code': row['code'],
                'name': row['name'],
                'price': row['price'],
                'market_cap': market_cap_yi,
                'pe': row['pe'],
                'activity_percentile': row['activity_percentile'],
                'fundamental_percentile': row['fundamental_percentile'],
                'combined_score': row['combined_score']
            })

        return results

    def _parse_float(self, value) -> float:
        """解析浮点数"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                value = value.replace("%", "").replace(",", "").strip()
                if value in ["-", "--", "", "None"]:
                    return 0.0
                return float(value)
        except:
            pass
        return 0.0


def main():
    """测试主程序"""
    selector = SectorLeaderSelector(lookback_days=60)

    # 测试几个板块（使用正确的概念板块名称）
    test_sectors = [
        "人工智能",
        "工业母机",  # 机器人相关
        "汽车芯片",   # 半导体相关
    ]

    all_results = {}

    for sector in test_sectors:
        print(f"\n\n{'#'*70}")
        print(f"# 筛选板块: {sector}")
        print(f"{'#'*70}")

        try:
            results = selector.select_sector_leaders(
                sector_name=sector,
                activity_threshold=0.3,  # 活跃度前30%
                fundamental_threshold=0.5,  # 业绩前50%
                max_stocks=30
            )

            all_results[sector] = [r['code'] for r in results]

        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

    # 保存结果
    import json
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "sector_leaders.json"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n\n{'='*70}")
    print(f"结果已保存到: {output_path}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
