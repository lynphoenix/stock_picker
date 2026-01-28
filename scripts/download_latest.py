# -*- coding: utf-8 -*-
"""
下载最新数据和指数数据
"""

import sys
from pathlib import Path
import pandas as pd
import pickle
import time
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

import akshare as ak
from settings import CACHE_DIR


class LatestDataDownloader:
    """最新数据下载器"""

    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download_latest_data(self, start_date: str = None, end_date: str = None):
        """
        下载最新数据

        Args:
            start_date: 开始日期 YYYYMMDD，默认20260101
            end_date: 结束日期 YYYYMMDD，默认今天
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = '20260101'

        print(f"{'='*80}")
        print(f"下载最新数据 ({start_date} - {end_date})")
        print(f"{'='*80}\n")

        # 读取股票列表
        stock_list_file = Path('data/stock_list_latest.csv')
        if not stock_list_file.exists():
            print("获取股票列表...")
            stock_list = ak.stock_info_a_code_name()
            stock_list.to_csv(stock_list_file, index=False, encoding='utf-8')
        else:
            stock_list = pd.read_csv(stock_list_file)

        print(f"股票列表: {len(stock_list)} 只\n")

        success = 0
        failed = 0
        skipped = 0
        total_records = 0

        for i, (_, row) in enumerate(stock_list.iterrows()):
            code = row['code']
            name = row['name']

            # 检查缓存
            cache_key = f'stock_hist_{code}_{start_date}_{end_date}_qfq'
            cache_file = self.cache_dir / f'{cache_key}.pkl'

            if cache_file.exists():
                skipped += 1
                continue

            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period='daily',
                    start_date=start_date,
                    end_date=end_date,
                    adjust='qfq'
                )

                if df is not None and not df.empty:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(df, f)
                    success += 1
                    total_records += len(df)
                    if success <= 20 or success % 500 == 0:
                        print(f"  [{i+1}/{len(stock_list)}] {code} {name}: {len(df)}条")
                else:
                    failed += 1

            except Exception as e:
                failed += 1

            time.sleep(0.1)

            # 每500只暂停
            if (i + 1) % 500 == 0:
                print(f"\n  === 进度: {i+1}/{len(stock_list)}, 成功:{success}, 失败:{failed}, 跳过:{skipped} ===\n")
                time.sleep(3)

        print(f"\n{'='*80}")
        print("下载完成")
        print(f"{'='*80}")
        print(f"成功: {success} 只")
        print(f"失败: {failed} 只")
        print(f"跳过: {skipped} 只")
        print(f"总记录: {total_records:,} 条")

        return success, failed, skipped

    def download_index_data(self, start_date: str = None, end_date: str = None):
        """
        下载指数数据

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = '20150101'

        print(f"\n{'='*80}")
        print(f"下载指数数据 ({start_date} - {end_date})")
        print(f"{'='*80}\n")

        # 主要指数
        major_indices = {
            '000001': '上证指数',
            '399001': '深证成指',
            '399006': '创业板指',
            '000300': '沪深300',
            '000016': '上证50',
            '399905': '中证500',
            '000688': '科创50',
            '000905': '中证全指',
            '399673': '创业板50',
            '000852': '中证1000',
        }

        success = 0
        failed = 0

        for code, name in major_indices.items():
            cache_key = f'index_hist_{code}_{start_date}_{end_date}'
            cache_file = self.cache_dir / f'{cache_key}.pkl'

            if cache_file.exists():
                print(f"  {code} {name}: 已存在")
                success += 1
                continue

            try:
                df = ak.stock_zh_index_daily(
                    symbol=f'sh{code}' if code.startswith('00') else f'sz{code}'
                )

                if df is not None and not df.empty:
                    # 筛选日期范围
                    df = df[(df.index >= start_date) & (df.index <= end_date)]

                    with open(cache_file, 'wb') as f:
                        pickle.dump(df, f)

                    print(f"  {code} {name}: {len(df)}条")
                    success += 1
                else:
                    print(f"  {code} {name}: 无数据")
                    failed += 1

            except Exception as e:
                print(f"  {code} {name}: 失败 - {str(e)[:30]}")
                failed += 1

            time.sleep(0.5)

        print(f"\n{'='*80}")
        print("指数下载完成")
        print(f"{'='*80}")
        print(f"成功: {success} 个")
        print(f"失败: {failed} 个")

        return success, failed


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="下载最新数据和指数数据")
    parser.add_argument("--start-date", type=str, default=None, help="开始日期 YYYYMMDD")
    parser.add_argument("--end-date", type=str, default=None, help="结束日期 YYYYMMDD")
    parser.add_argument("--index-only", action="store_true", help="只下载指数")
    parser.add_argument("--stock-only", action="store_true", help="只下载股票")

    args = parser.parse_args()

    downloader = LatestDataDownloader()

    if not args.index_only:
        downloader.download_latest_data(args.start_date, args.end_date)

    if not args.stock_only:
        downloader.download_index_data(args.start_date, args.end_date)


if __name__ == "__main__":
    main()
