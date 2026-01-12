# -*- coding: utf-8 -*-
"""
数据获取模块 - 使用AKShare获取A股数据
"""
import akshare as ak
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys

# 添加父目录到路径以导入config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class DataFetcher:
    """数据获取类"""

    def __init__(self):
        self.cache_dir = config.CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_stock_list(self, market: str = "A股") -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型（A股、沪深等）

        Returns:
            股票列表DataFrame，包含代码、名称等
        """
        try:
            # 获取A股实时行情
            df = ak.stock_zh_a_spot_em()

            # 重命名列
            df = df.rename(columns={
                "代码": "code",
                "名称": "name",
                "最新价": "price",
                "涨跌幅": "change_pct",
                "成交量": "volume",
                "成交额": "amount",
                "总市值": "market_cap",
                "流通市值": "float_cap",
            })

            # 添加后缀
            df["symbol"] = df["code"]
            df["exchange"] = df["code"].apply(
                lambda x: "SH" if x.startswith("6") else "SZ"
            )

            return df[["code", "symbol", "name", "exchange", "price",
                      "change_pct", "volume", "amount", "market_cap", "float_cap"]]

        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_sector_stocks(self, sector_name: str) -> List[str]:
        """
        获取指定板块的股票代码列表

        Args:
            sector_name: 板块名称（如"机器人"、"人工智能"）

        Returns:
            股票代码列表
        """
        try:
            # 获取板块成分股
            df = ak.stock_board_concept_cons_em(symbol=sector_name)

            if "代码" in df.columns:
                return df["代码"].tolist()
            return []

        except Exception as e:
            print(f"获取板块 {sector_name} 成分股失败: {e}")
            return []

    def get_all_target_sectors_stocks(self) -> Dict[str, List[str]]:
        """
        获取所有目标板块的股票池

        Returns:
            {板块名: [股票代码列表]}
        """
        result = {}

        for category, sectors in config.TARGET_SECTORS.items():
            category_stocks = []
            for sector in sectors:
                stocks = self.get_sector_stocks(sector)
                category_stocks.extend(stocks)

            # 去重
            result[category] = list(set(category_stocks))

        return result

    def get_stock_history(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取股票历史行情

        Args:
            symbol: 股票代码（如 "000001"）
            period: 周期（daily, weekly, monthly）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust: 复权类型（qfq前复权, hfq后复权, ""不复权）

        Returns:
            历史行情DataFrame
        """
        try:
            # 确定交易所
            exchange = "sz" if symbol.startswith("0") or symbol.startswith("3") else "sh"

            if not end_date:
                end_date = datetime.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            # 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )

            if df is not None and not df.empty:
                # 重命名列
                df = df.rename(columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                })
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)

            return df

        except Exception as e:
            print(f"获取 {symbol} 历史数据失败: {e}")
            return pd.DataFrame()

    def get_stock_fundamentals(self, symbol: str) -> Dict:
        """
        获取股票基本面数据

        Args:
            symbol: 股票代码

        Returns:
            基本面数据字典
        """
        try:
            # 获取个股信息
            df = ak.stock_individual_info_em(symbol=symbol)

            if df is not None and not df.empty:
                # 转换为字典
                info = dict(zip(df["item"], df["value"]))

                # 提取关键指标
                result = {
                    "code": symbol,
                    "name": info.get("股票简称", ""),
                    "industry": info.get("行业", ""),
                    "pe": self._parse_number(info.get("市盈率-动态", "0")),
                    "pb": self._parse_number(info.get("市净率", "0")),
                    "market_cap": self._parse_number(info.get("总市值", "0")),
                    "float_cap": self._parse_number(info.get("流通市值", "0")),
                }

                # 获取财务指标（ROE等）- 使用同花顺API
                try:
                    fin_df = ak.stock_financial_abstract_ths(symbol=symbol)
                    if not fin_df.empty:
                        latest = fin_df.iloc[-1]
                        result["roe"] = self._parse_number(latest.get("净资产收益率", 0))
                        result["revenue_growth"] = self._parse_number(latest.get("营业总收入同比增长率", 0))
                        result["profit_growth"] = self._parse_number(latest.get("净利润同比增长率", 0))
                except Exception as e:
                    # 如果获取失败，记录日志但不中断
                    result["roe"] = 0
                    result["revenue_growth"] = 0
                    result["profit_growth"] = 0

                return result

        except Exception as e:
            print(f"获取 {symbol} 基本面失败: {e}")

        return {}

    def _parse_number(self, value) -> float:
        """解析数字字符串"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # 去除百分号等
                value = value.replace("%", "").replace(",", "").strip()
                if value in ["-", "--", "", "None"]:
                    return 0.0
                return float(value)
        except:
            pass
        return 0.0

    def save_stock_pools(self, pools: Dict[str, List[str]]):
        """保存股票池到本地"""
        path = os.path.join(config.DATA_DIR, "stock_pools.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(pools, f, ensure_ascii=False, indent=2)

    def load_stock_pools(self) -> Dict[str, List[str]]:
        """从本地加载股票池"""
        path = os.path.join(config.DATA_DIR, "stock_pools.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}


if __name__ == "__main__":
    # 测试代码
    fetcher = DataFetcher()

    print("=== 测试获取股票列表 ===")
    stocks = fetcher.get_stock_list()
    print(f"共 {len(stocks)} 只股票")
    print(stocks.head())

    print("\n=== 测试获取板块成分股 ===")
    ai_stocks = fetcher.get_sector_stocks("人工智能")
    print(f"人工智能板块共 {len(ai_stocks)} 只股票")
    print(ai_stocks[:10])

    print("\n=== 测试获取历史行情 ===")
    history = fetcher.get_stock_history("000001")
    print(history.head())

    print("\n=== 测试获取基本面 ===")
    fundamental = fetcher.get_stock_fundamentals("000001")
    print(fundamental)
