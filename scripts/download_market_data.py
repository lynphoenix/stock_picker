# -*- coding: utf-8 -*-
"""
全市场历史数据下载脚本
功能：
1. 下载全A股2015年至今的日线数据
2. 数据校验和完整性检查
3. 增量更新（只下载缺失部分）
4. 支持断点续传
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, List, Set, Tuple
import pickle
from itertools import islice

sys.path.append(str(Path(__file__).parent.parent))

from src.data.stock_loader import StockLoader
from src.data.cache import get_cache_manager
from settings import CACHE_DIR


class MarketDataDownloader:
    """全市场数据下载器"""

    def __init__(self):
        self.loader = StockLoader()
        self.cache = get_cache_manager()
        self.cache_dir = CACHE_DIR

        # 下载数据存储
        self.download_stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_records': 0
        }

    def get_all_stocks(self) -> pd.DataFrame:
        """
        获取全A股列表
        """
        print("[1] 获取全A股列表...")

        # 尝试从缓存获取
        cache_key = "stock_list_A股"
        cached = self.cache.get(cache_key, "data")
        if cached is not None:
            print(f"    从缓存获取: {len(cached)} 只股票")
            return cached

        # 从akshare获取
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
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
            df["symbol"] = df["code"]
            df["exchange"] = df["code"].apply(
                lambda x: "SH" if x.startswith("6") else "SZ"
            )

            result = df[["code", "symbol", "name", "exchange", "price",
                         "change_pct", "volume", "amount", "market_cap", "float_cap"]]

            # 缓存1天
            self.cache.set(cache_key, result, "data")
            print(f"    获取成功: {len(result)} 只股票")
            return result

        except Exception as e:
            print(f"    获取失败: {e}")
            return pd.DataFrame()

    def filter_valid_stocks(self, stock_list: pd.DataFrame) -> pd.DataFrame:
        """
        过滤有效股票（剔除ST、退市等）
        """
        print("[2] 过滤有效股票...")

        # 过滤ST股票
        filtered = stock_list[
            ~stock_list['name'].str.contains('ST|退|暂停', na=False)
        ].copy()

        # 过滤市值过小的股票（可选）
        # filtered = filtered[filtered['market_cap'] > 1000000000]

        print(f"    过滤后: {len(filtered)} 只股票")
        return filtered

    def check_data_completeness(self, stock_list: pd.DataFrame) -> Dict[str, List]:
        """
        检查数据完整性
        返回: {stock_code: [missing_years]}
        """
        print("[3] 检查数据完整性...")

        target_years = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
        missing_data = {}

        # 检查每只股票的缓存文件
        for _, stock in stock_list.head(100).iterrows():  # 先检查100只
            code = stock['code']
            missing_years = []

            for year in target_years:
                cache_key = f"stock_hist_{code}_{year}0101_{year}1231_qfq"
                cache_file = self.cache_dir / f"{cache_key}.pkl"

                if not cache_file.exists():
                    missing_years.append(year)
                else:
                    # 检查数据是否为空
                    try:
                        with open(cache_file, 'rb') as f:
                            df = pickle.load(f)
                            if df is None or len(df) == 0:
                                missing_years.append(year)
                    except:
                        missing_years.append(year)

            if missing_years:
                missing_data[code] = missing_years

        # 统计
        total_missing = sum(len(years) for years in missing_data.values())
        print(f"    抽检100只股票:")
        print(f"    数据完整: {100 - len(missing_data)} 只")
        print(f"    有缺失: {len(missing_data)} 只")
        print(f"    总缺失年份数: {total_missing}")

        return missing_data

    def download_stock_data(self, stock_code: str, start_year: int, end_year: int, force_redownload: bool = False) -> bool:
        """
        下载单只股票的历史数据
        """
        # 预期每年的交易日数量
        expected_trading_days = {
            2014: 245, 2015: 244, 2016: 244, 2017: 244, 2018: 243,
            2019: 244, 2020: 243, 2021: 243, 2022: 242, 2023: 243,
            2024: 243, 2025: 20, 2026: 20  # 2025-2026年目前只有部分数据
        }

        for year in range(start_year, end_year + 1):
            cache_key = f"stock_hist_{stock_code}_{year}0101_{year}1231_qfq"
            cache_file = self.cache_dir / f"{cache_key}.pkl"

            # 如果已有缓存，智能判断是否需要重新下载
            if cache_file.exists() and not force_redownload:
                quality = self.analyze_data_quality(stock_code, year)

                if quality['status'] == 'complete':
                    self.download_stats['skipped'] += 1
                    continue
                elif quality['status'] == 'missing':
                    # 文件不存在，继续下载
                    pass
                elif quality.get('should_redownload', False):
                    # 明确需要重新下载
                    print(f"      {stock_code} {year}: ⚠ {quality['reason']}, 重新下载...")
                elif quality['status'].startswith('incomplete'):
                    # 数据不完整，但可能是正常的（停牌/IPO）
                    # 严格模式：仍然重新下载以确保
                    if year >= 2025:
                        self.download_stats['skipped'] += 1
                        continue
                    else:
                        print(f"      {stock_code} {year}: ⚠ {quality['reason']} ({quality['actual']}/{quality['expected']}天), 重新下载验证...")
                else:
                    # 其他情况（文件损坏等），重新下载
                    print(f"      {stock_code} {year}: ⚠ {quality.get('reason', '数据异常')}, 重新下载...")

            # 下载数据
            try:
                df = self.loader.get_stock_history(
                    stock_code,
                    f"{year}0101",
                    f"{year}1231",
                    use_cache=False  # 强制下载
                )

                if df is not None and not df.empty:
                    # 保存到缓存
                    self.cache.set(cache_key, df, "data")
                    self.download_stats['success'] += 1
                    self.download_stats['total_records'] += len(df)
                    print(f"      {stock_code} {year}: ✓ {len(df)}条")
                else:
                    self.download_stats['failed'] += 1
                    print(f"      {stock_code} {year}: ✗ 无数据")
                    return False

                time.sleep(0.05)  # 短暂延迟

            except Exception as e:
                self.download_stats['failed'] += 1
                print(f"      {stock_code} {year}: ✗ {str(e)[:30]}")
                return False

        return True

    def download_all_data(
        self,
        start_year: int = 2015,
        end_year: int = None,
        max_stocks: int = None,
        resume_from: str = None,
        fix_incomplete: bool = False
    ):
        """
        下载全市场数据

        Args:
            start_year: 开始年份
            end_year: 结束年份
            max_stocks: 最大股票数（None表示全部）
            resume_from: 从某只股票继续（断点续传）
            fix_incomplete: 是否补全不完整的数据
        """
        if end_year is None:
            end_year = datetime.now().year

        print(f"{'='*80}")
        print(f"全市场历史数据下载 ({start_year}-{end_year})")
        print(f"{'='*80}\n")

        # 1. 获取股票列表
        all_stocks = self.get_all_stocks()
        if all_stocks.empty:
            print("错误: 无法获取股票列表")
            return

        # 2. 过滤有效股票
        valid_stocks = self.filter_valid_stocks(all_stocks)

        # 3. 限制数量（如果指定）
        if max_stocks:
            valid_stocks = valid_stocks.head(max_stocks)

        print(f"\n[3] 准备下载 {len(valid_stocks)} 只股票的数据...")

        # 4. 检查完整性（可选）
        # missing_data = self.check_data_completeness(valid_stocks)

        # 5. 开始下载
        print(f"\n[4] 开始下载...")
        print(f"    年份范围: {start_year} - {end_year}")
        print(f"    股票数量: {len(valid_stocks)}")
        print(f"    预计时间: 约 {len(valid_stocks) * (end_year - start_year + 1) * 0.05 / 60:.1f} 分钟")

        # 找到续传位置
        start_idx = 0
        if resume_from:
            for i, (_, stock) in enumerate(valid_stocks.iterrows()):
                if stock['code'] == resume_from:
                    start_idx = i + 1
                    break
            print(f"    从 {resume_from} 继续下载...")

        success_stocks = []
        failed_stocks = []

        # 使用 islice 跳过前面的行
        rows_iter = valid_stocks.iterrows()
        if start_idx > 0:
            rows_iter = islice(valid_stocks.iterrows(), start_idx, None)

        for i, (_, stock) in enumerate(rows_iter, start=start_idx):
            code = stock['code']
            name = stock['name']

            print(f"  [{i+1}/{len(valid_stocks)}] {code} {name}")

            if self.download_stock_data(code, start_year, end_year, force_redownload=fix_incomplete):
                success_stocks.append(code)
            else:
                failed_stocks.append(code)

            # 每100只股票暂停
            if (i + 1) % 100 == 0:
                print(f"\n  === 进度: {i+1}/{len(valid_stocks)}, 暂停3秒 ===")
                time.sleep(3)

        # 6. 统计结果
        print(f"\n{'='*80}")
        print("下载完成统计")
        print(f"{'='*80}")
        print(f"成功: {self.download_stats['success']} 次")
        print(f"失败: {self.download_stats['failed']} 次")
        print(f"跳过(已有): {self.download_stats['skipped']} 次")
        print(f"总记录数: {self.download_stats['total_records']} 条")
        print(f"成功率: {self.download_stats['success'] / (self.download_stats['success'] + self.download_stats['failed']) * 100:.1f}%")

        if failed_stocks:
            print(f"\n失败股票 ({len(failed_stocks)}只): {failed_stocks[:20]}...")

        return success_stocks, failed_stocks

    def verify_data_quality(self, sample_size: int = 100):
        """
        验证数据质量
        """
        print(f"\n[5] 验证数据质量 (随机抽检{sample_size}只股票)...")

        cache_files = list(self.cache_dir.glob("stock_hist_*_202*.pkl"))

        if not cache_files:
            print("    无缓存数据")
            return

        import random
        sample_files = random.sample(cache_files, min(sample_size, len(cache_files)))

        empty_count = 0
        error_count = 0
        total_records = 0

        for f in sample_files:
            try:
                with open(f, 'rb') as f:
                    df = pickle.load(f)

                if df is None:
                    empty_count += 1
                elif not isinstance(df, pd.DataFrame):
                    error_count += 1
                else:
                    total_records += len(df)

                    # 检查必需字段
                    required_cols = ['date', 'open', 'close', 'high', 'low']
                    if not all(col in df.columns for col in required_cols):
                        error_count += 1

            except Exception as e:
                error_count += 1

        print(f"    抽检文件: {len(sample_files)}")
        print(f"    空数据: {empty_count}")
        print(f"    错误数据: {error_count}")
        print(f"    有效数据: {len(sample_files) - empty_count - error_count}")
        print(f"    总记录数: {total_records}")

        if total_records > 0:
            print(f"    平均每文件: {total_records / (len(sample_files) - empty_count):.0f} 条")

    def analyze_data_quality(self, stock_code: str, year: int) -> dict:
        """
        分析单只股票单年数据质量，区分下载失败和正常缺失
        """
        expected_trading_days = {
            2014: 245, 2015: 244, 2016: 244, 2017: 244, 2018: 243,
            2019: 244, 2020: 243, 2021: 243, 2022: 242, 2023: 243, 2024: 243
        }

        cache_key = f"stock_hist_{stock_code}_{year}0101_{year}1231_qfq"
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        if not cache_file.exists():
            return {'status': 'missing', 'reason': '文件不存在'}

        try:
            with open(cache_file, 'rb') as f:
                df = pickle.load(f)
        except:
            return {'status': 'corrupted', 'reason': '文件损坏'}

        if df is None or len(df) == 0:
            return {'status': 'empty', 'reason': '数据为空'}

        # 分析数据
        df = df.sort_values('date')
        actual_days = len(df)
        expected = expected_trading_days.get(year, 244)

        # 检查日期范围
        date_span = (df['date'].max() - df['date'].min()).days + 1

        # 检查是否有大缺口（可能表示长期停牌）
        df['date_diff'] = df['date'].diff()
        large_gaps = df[df['date_diff'] > pd.Timedelta(days=20)]

        # 完整性判断
        completeness = actual_days / expected

        if completeness >= 0.98:
            return {
                'status': 'complete',
                'actual': actual_days,
                'expected': expected,
                'completeness': f'{completeness*100:.1f}%'
            }

        # 数据不完整，分析原因
        if date_span < 100:
            return {
                'status': 'incomplete_new_stock',
                'actual': actual_days,
                'expected': expected,
                'date_span': date_span,
                'reason': f'新股或长期停牌（仅覆盖{date_span}天）',
                'should_redownload': False
            }
        elif len(large_gaps) >= 2:
            return {
                'status': 'incomplete_suspension',
                'actual': actual_days,
                'expected': expected,
                'gaps': len(large_gaps),
                'reason': f'可能有{len(large_gaps)}次长期停牌',
                'should_redownload': False
            }
        elif completeness < 0.8:
            return {
                'status': 'incomplete_download_error',
                'actual': actual_days,
                'expected': expected,
                'completeness': f'{completeness*100:.1f}%',
                'reason': '数据严重缺失，可能是下载失败',
                'should_redownload': True
            }
        else:
            return {
                'status': 'incomplete_minor',
                'actual': actual_days,
                'expected': expected,
                'completeness': f'{completeness*100:.1f}%',
                'reason': '少量缺失，可能是零散停牌',
                'should_redownload': False
            }

    def check_trading_days_completeness(self, year: int = 2024, sample_stocks: int = 50):
        """
        检查交易日数据的完整性
        验证是否有缺失的交易日
        """
        print(f"\n[详细校验] 检查 {year} 年交易日数据完整性...")

        # 获取该年份的缓存文件
        year_files = list(self.cache_dir.glob(f"stock_hist_*_{year}*.pkl"))
        print(f"    找到 {len(year_files)} 个{year}年的缓存文件")

        if not year_files:
            print("    无数据")
            return

        # 预期每年的交易日数量（约244天，考虑节假日）
        expected_trading_days = {
            2014: 245, 2015: 244, 2016: 244, 2017: 244, 2018: 243,
            2019: 244, 2020: 243, 2021: 243, 2022: 242, 2023: 243,
            2024: 243, 2025: 20  # 2025年目前只有部分数据
        }

        expected = expected_trading_days.get(year, 244)

        # 随机抽样检查
        import random
        sample_size = min(sample_stocks, len(year_files))
        sample_files = random.sample(year_files, sample_size)

        incomplete_stocks = []
        missing_data = {}

        for i, f in enumerate(sample_files):
            parts = f.stem.split('_')
            if len(parts) >= 3:
                code = parts[2]

            try:
                with open(f, 'rb') as file:
                    df = pickle.load(file)

                if df is not None and len(df) > 0:
                    actual_days = len(df)

                    # 检查数量差异
                    if actual_days < expected * 0.8:  # 少于80%认为可能有问题
                        incomplete_stocks.append((code, actual_days))

                    # 检查日期连续性（简单检查）
                    if 'date' in df.columns:
                        df_sorted = df.sort_values('date')
                        date_range = (df_sorted['date'].max() - df_sorted['date'].min()).days

                        # 如果日期跨度远大于记录数，说明中间有缺失
                        if date_range > actual_days * 2:
                            missing_days_estimate = date_range - actual_days
                            missing_data[code] = {
                                'actual': actual_days,
                                'date_span': date_range,
                                'estimated_missing': missing_days_estimate
                            }

            except Exception as e:
                pass

        # 输出结果
        print(f"\n    抽检 {sample_size} 只股票的结果:")
        print(f"    预期交易日: ~{expected} 天")

        if incomplete_stocks:
            print(f"\n    数据可能不完整 ({len(incomplete_stocks)}只):")
            for code, days in incomplete_stocks[:10]:
                print(f"      {code}: {days} 天")
        else:
            print(f"    ✓ 抽检股票数据量正常")

        if missing_data:
            print(f"\n    可能存在缺失交易日:")
            for code, info in list(missing_data.items())[:5]:
                print(f"      {code}: 实际{info['actual']}天, 跨度{info['date_span']}天, "
                      f"可能缺失~{info['estimated_missing']}天")

        return {
            'sample_size': sample_size,
            'expected_days': expected,
            'incomplete': incomplete_stocks,
            'missing_dates': missing_data
        }


    def scan_data_quality(self, year: int = 2024, max_stocks: int = None, full_inspection: bool = False):
        """
        扫描所有股票的数据质量并生成报告
        区分：下载失败 vs 正常缺失（停牌/IPO）

        Args:
            year: 检查年份
            max_stocks: 最大股票数（None表示全检）
            full_inspection: 强制全检模式（覆盖max_stocks限制）
        """
        print(f"\n{'='*80}")
        print(f"扫描 {year} 年数据质量 ({'全检模式' if full_inspection or max_stocks is None else f'限制{max_stocks}只'})")
        print(f"{'='*80}\n")

        # 获取所有股票列表
        stock_list = self.get_all_stocks()
        if stock_list.empty:
            print("无法获取股票列表")
            return

        valid_stocks = self.filter_valid_stocks(stock_list)
        # full_inspection 或 max_stocks=None 时做全检
        if not full_inspection and max_stocks:
            valid_stocks = valid_stocks.head(max_stocks)

        print(f"扫描 {len(valid_stocks)} 只股票...\n")

        # 统计
        stats = {
            'complete': 0,
            'new_stock': 0,
            'suspension': 0,
            'download_error': 0,
            'missing': 0,
            'corrupted': 0
        }

        download_errors = []  # 可能是下载失败的

        for i, (_, stock) in enumerate(valid_stocks.iterrows()):
            code = stock['code']
            name = stock['name']

            quality = self.analyze_data_quality(code, year)

            if quality['status'] == 'complete':
                stats['complete'] += 1
            elif quality['status'] == 'incomplete_new_stock':
                stats['new_stock'] += 1
            elif quality['status'] == 'incomplete_suspension':
                stats['suspension'] += 1
            elif quality['status'] == 'incomplete_download_error':
                stats['download_error'] += 1
                download_errors.append((code, name, quality))
            elif quality['status'] == 'missing':
                stats['missing'] += 1
            elif quality['status'] == 'corrupted':
                stats['corrupted'] += 1

            # 进度显示
            if (i + 1) % 500 == 0:
                print(f"  进度: {i+1}/{len(valid_stocks)}")

        # 输出报告
        print(f"\n{'='*80}")
        print("数据质量报告")
        print(f"{'='*80}")
        print(f"数据完整: {stats['complete']} 只 ({stats['complete']/len(valid_stocks)*100:.1f}%)")
        print(f"新股/IPO: {stats['new_stock']} 只")
        print(f"长期停牌: {stats['suspension']} 只")
        print(f"疑似下载失败: {stats['download_error']} 只")
        print(f"文件缺失: {stats['missing']} 只")
        print(f"文件损坏: {stats['corrupted']} 只")

        if download_errors:
            print(f"\n疑似下载失败的股票 (建议重新下载):")
            for code, name, info in download_errors[:20]:
                print(f"  {code} {name}: {info['actual']}/{info['expected']}天 - {info['reason']}")

        print(f"\n{'='*80}")
        print("建议操作:")
        if stats['download_error'] > 0 or stats['missing'] > 0:
            print(f"  运行: python scripts/download_market_data.py --start-year {year} --end-year {year} --fix-incomplete")
        else:
            print(f"  {year}年数据质量良好，无需修复")

        return stats

    def retry_failed_downloads(self, start_year: int = 2015, end_year: int = None):
        """
        重试之前失败的下载
        扫描所有股票，找出缺失或损坏的数据，重新下载
        """
        if end_year is None:
            end_year = datetime.now().year

        print(f"{'='*80}")
        print(f"重试失败的数据下载 ({start_year}-{end_year})")
        print(f"{'='*80}\n")

        # 获取所有股票列表
        stock_list = self.get_all_stocks()
        if stock_list.empty:
            print("错误: 无法获取股票列表")
            return

        valid_stocks = self.filter_valid_stocks(stock_list)
        print(f"检查 {len(valid_stocks)} 只股票...\n")

        # 找出需要重新下载的股票和年份
        retry_queue = []  # [(code, year, reason), ...]

        for _, stock in valid_stocks.iterrows():
            code = stock['code']
            name = stock['name']

            for year in range(start_year, end_year + 1):
                quality = self.analyze_data_quality(code, year)

                # 需要重新下载的情况
                if quality['status'] in ['missing', 'corrupted', 'empty', 'incomplete_download_error']:
                    retry_queue.append((code, name, year, quality['status'], quality.get('reason', '')))

        print(f"[1] 发现 {len(retry_queue)} 个需要重试的下载任务\n")

        if not retry_queue:
            print("所有数据完整，无需重试")
            return

        # 按年份分组显示
        from collections import defaultdict
        by_year = defaultdict(list)
        for code, name, year, status, reason in retry_queue:
            by_year[year].append((code, name, status, reason))

        for year in sorted(by_year.keys()):
            print(f"  {year}年: {len(by_year[year])} 个")

        print(f"\n[2] 开始重新下载...")

        success_count = 0
        failed_count = 0

        for i, (code, name, year, status, reason) in enumerate(retry_queue):
            print(f"  [{i+1}/{len(retry_queue)}] {code} {name} {year}年 ({status})")

            try:
                start_date = f"{year}0101"
                end_date = f"{year}1231"

                df = self.loader.get_stock_history(code, start_date, end_date, use_cache=False)

                if df is not None and not df.empty:
                    cache_key = f"stock_hist_{code}_{start_date}_{end_date}_qfq"
                    self.cache.set(cache_key, df, "data")
                    self.download_stats['success'] += 1
                    self.download_stats['total_records'] += len(df)
                    print(f"      ✓ {len(df)}条")
                    success_count += 1
                else:
                    print(f"      ✗ 无数据")
                    failed_count += 1

            except Exception as e:
                print(f"      ✗ {str(e)[:30]}")
                failed_count += 1

            time.sleep(0.05)  # 延迟

            # 每100个暂停
            if (i + 1) % 100 == 0:
                print(f"\n  === 进度: {i+1}/{len(retry_queue)}, 暂停3秒 ===")
                time.sleep(3)

        print(f"\n{'='*80}")
        print("重试完成统计")
        print(f"{'='*80}")
        print(f"成功: {success_count} 个")
        print(f"失败: {failed_count} 个")
        print(f"成功率: {success_count / len(retry_queue) * 100:.1f}%")

        return success_count, failed_count


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="全市场历史数据下载")
    parser.add_argument("--start-year", type=int, default=2015, help="开始年份")
    parser.add_argument("--end-year", type=int, default=None, help="结束年份（默认当前年）")
    parser.add_argument("--max-stocks", type=int, default=None, help="最大股票数量（测试用）")
    parser.add_argument("--resume", type=str, default=None, help="从某只股票继续下载")
    parser.add_argument("--verify", action="store_true", help="只验证数据，不下载")
    parser.add_argument("--check-trading-days", type=int, default=None, help="检查指定年份的交易日完整性")
    parser.add_argument("--fix-incomplete", action="store_true", help="补全不完整的数据（数据量<预期）")
    parser.add_argument("--scan-quality", type=int, default=None, help="扫描指定年份的数据质量")
    parser.add_argument("--scan-max", type=int, default=None, help="质量扫描的最大股票数")
    parser.add_argument("--full-inspection", action="store_true", help="全检模式（扫描所有股票，不限制数量）")
    parser.add_argument("--retry-failed", action="store_true", help="重试之前失败的下载")

    args = parser.parse_args()

    downloader = MarketDataDownloader()

    if args.scan_quality:
        # 扫描数据质量
        downloader.scan_data_quality(args.scan_quality, max_stocks=args.scan_max, full_inspection=args.full_inspection)
    elif args.check_trading_days:
        # 详细校验交易日完整性
        downloader.check_trading_days_completeness(args.check_trading_days)
    elif args.verify:
        # 只验证数据
        stock_list = downloader.get_all_stocks()
        downloader.verify_data_quality()
    elif args.retry_failed:
        # 重试失败的下载
        downloader.retry_failed_downloads(start_year=args.start_year, end_year=args.end_year)
    else:
        # 下载数据
        if args.fix_incomplete:
            print(f"⚠ 补全模式：将重新下载数据量少于预期的年份\n")

        downloader.download_all_data(
            start_year=args.start_year,
            end_year=args.end_year,
            max_stocks=args.max_stocks,
            resume_from=args.resume,
            fix_incomplete=args.fix_incomplete
        )

        # 验证数据
        downloader.verify_data_quality()


if __name__ == "__main__":
    main()
