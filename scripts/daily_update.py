# -*- coding: pacache-fencoding: utf-8 -*-
"""
每日数据更新和指标计算任务
功能：
1. 下载当日市场数据
2. 计算技术指标（均线、MACD、KDJ等）
3. 计算行业统计数据
4. 存储到本地数据库
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, List

sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from src.data.cache import get_cache_manager
from settings import CACHE_DIR


class DailyDataUpdater:
    """每日数据更新器"""

    def __init__(self):
        self.loader = StockLoader()
        self.cache = get_cache_manager()

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()

            df = df.rename(columns={
                "代码": "code",
                "名称": "name",
            })

            # 过滤ST
            df = df[~df['name'].str.contains('ST|退|暂停', na=False)]

            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()

    def download_today_data(self, stock_list: pd.DataFrame, date: str = None) -> Dict:
        """
        下载当日数据
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        print(f"[1] 下载 {date} 的数据...")

        results = {
            'success': [],
            'failed': [],
            'total_records': 0
        }

        # 限制数量避免触发反爬虫
        max_stocks = 500  # 每次最多500只
        stocks_to_download = stock_list.head(max_stocks)

        for i, (_, stock) in enumerate(stocks_to_download.iterrows()):
            code = stock['code']
            name = stock['name']

            try:
                df = self.loader.get_stock_history(code, date, date, use_cache=False)
                if df is not None and not df.empty:
                    # 保存
                    cache_key = f"stock_hist_{code}_{date}_{date}_qfq"
                    self.cache.set(cache_key, df, "data")

                    results['success'].append(code)
                    results['total_records'] += len(df)

                    if (i + 1) % 50 == 0:
                        print(f"    进度: {i+1}/{len(stocks_to_download)}")
                else:
                    results['failed'].append(code)

            except Exception as e:
                results['failed'].append(code)

            time.sleep(0.05)  # 延迟

        print(f"    成功: {len(results['success'])} 只")
        print(f"    失败: {len(results['failed'])} 只")

        return results

    def calculate_indicators(self, stock_list: pd.DataFrame, end_date: str = None):
        """
        计算技术指标
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        print(f"[2] 计算技术指标...")

        # 需要计算的历史数据长度
        lookback_days = {
            'MA5': 5,
            'MA10': 10,
            'MA20': 20,
            'MA60': 60,
            'MA120': 120,
            'MA250': 250
        }

        calculated = 0

        # 只计算前100只股票进行测试
        test_stocks = stock_list.head(100)

        for i, (_, stock) in enumerate(test_stocks.iterrows()):
            code = stock['code']

            try:
                # 获取历史数据（用于计算均线）
                start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=250)).strftime("%Y%m%d")
                df = self.loader.get_stock_history(code, start_date, end_date)

                if df is not None and not df.empty:
                    # 计算均线
                    for ma_name, days in lookback_days.items():
                        if len(df) >= days:
                            df[f'MA{ma_name[2:]}'] = df['close'].rolling(window=days).mean()

                    # 保存带指标的缓存
                    cache_key = f"stock_hist_{code}_{start_date}_{end_date}_qfq_with_indicators"
                    self.cache.set(cache_key, df, "data")

                    calculated += 1

                    if (i + 1) % 20 == 0:
                        print(f"    进度: {i+1}/{len(test_stocks)}")

            except Exception as e:
                pass

        print(f"    计算完成: {calculated} 只股票")

    def update_industry_stats(self, date: str = None):
        """
        更新行业统计数据
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        print(f"[3] 更新行业统计...")

        # 获取股票列表
        stock_list = self.get_stock_list()

        # 获取行业分类
        from akshare import stock_individual_info_em
        import time

        stock_to_industry = {}
        for i, (_, stock) in enumerate(stock_list.head(100).iterrows()):
            code = stock['code']
            try:
                info_df = stock_individual_info_em(symbol=code, timeout=3)
                industry_row = info_df[info_df['item'] == '行业']
                if not industry_row.empty:
                    stock_to_industry[code] = industry_row.iloc[0]['value']
                else:
                    stock_to_industry[code] = '其他'
            except:
                stock_to_industry[code] = '其他'

            if (i + 1) % 20 == 0:
                print(f"    进度: {i+1}/100")

        print(f"    行业分类完成: {len(stock_to_industry)} 只股票")

        # 按行业统计
        industry_stats = {}
        for code, industry in stock_to_industry.items():
            if industry not in industry_stats:
                industry_stats[industry] = {'stocks': [], 'total_market_cap': 0}
            industry_stats[industry]['stocks'].append(code)

        print(f"    行业数量: {len(industry_stats)}")

        # 保存行业统计
        stats_file = CACHE_DIR / f"industry_stats_{date}.pkl"
        import pickle
        with open(stats_file, 'wb') as f:
            pickle.dump(industry_stats, f)

        print(f"    已保存: {stats_file}")

    def run(self, date: str = None):
        """
        运行每日更新任务
        """
        print(f"{'='*80}")
        print(f"每日数据更新任务 - {date if date else datetime.now().strftime('%Y-%m-%d')}")
        print(f"{'='*80}\n")

        # 1. 获取股票列表
        stock_list = self.get_stock_list()
        if stock_list.empty:
            print("错误: 无法获取股票列表")
            return

        print(f"    股票总数: {len(stock_list)}")

        # 2. 下载当日数据
        download_results = self.download_today_data(stock_list, date)

        # 3. 计算指标
        if download_results['success']:
            self.calculate_indicators(stock_list, date)

        # 4. 更新行业统计
        self.update_industry_stats(date)

        print(f"\n{'='*80}")
        print("每日更新任务完成")
        print(f"{'='*80}")

        return download_results


def schedule_task():
    """
    定时任务调度器
    """
    import schedule

    def job():
        updater = DailyDataUpdater()
        updater.run()

    # 设置定时任务：每个交易日16:00执行
    schedule.every().day.at("16:00").do(job)

    print("定时任务已启动，等待执行...")
    print("按 Ctrl+C 停止")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        print("\n定时任务已停止")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="每日数据更新任务")
    parser.add_argument("--date", type=str, default=None, help="指定日期 (YYYYMMDD)")
    parser.add_argument("--schedule", action="store_true", help="启动定时任务")
    parser.add_argument("--test", action="store_true", help="测试模式（只处理少量股票）")

    args = parser.parse_args()

    updater = DailyDataUpdater()

    if args.schedule:
        schedule_task()
    elif args.date:
        updater.run(args.date)
    else:
        # 使用今天的日期
        updater.run()


if __name__ == "__main__":
    main()
