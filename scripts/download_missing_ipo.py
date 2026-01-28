# -*- coding: utf-8 -*-
"""
下载新IPO股票数据
"""

import sys
from pathlib import Path
import pickle
from datetime import datetime
import time

sys.path.append(str(Path(__file__).parent.parent))

import akshare as ak
from settings import CACHE_DIR


def download_missing_ipo():
    """下载缺失的新IPO数据"""

    cache_dir = CACHE_DIR

    # 读取缺失列表
    missing_2024_file = Path('data/missing_ipo_2024.txt')
    missing_2025_file = Path('data/missing_ipo_2025.txt')

    if not missing_2024_file.exists() or not missing_2025_file.exists():
        print("缺失列表文件不存在，请先生成")
        return 0, 0

    with open(missing_2024_file, 'r') as f:
        missing_2024 = [line.strip() for line in f if line.strip()]

    with open(missing_2025_file, 'r') as f:
        missing_2025 = [line.strip() for line in f if line.strip()]

    all_missing = list(set(missing_2024 + missing_2025))

    print(f"{'='*80}")
    print(f"下载新IPO股票数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    print(f"总计: {len(all_missing)}只")
    print(f"  2024年: {len(missing_2024)}只")
    print(f"  2025年: {len(missing_2025)}只")
    print()

    success_2024 = 0
    failed_2024 = 0
    success_2025 = 0
    failed_2025 = 0

    for i, code in enumerate(all_missing):
        try:
            # 下载2024年数据
            if code in missing_2024:
                cache_file = cache_dir / f'stock_hist_{code}_20240101_20241231_qfq.pkl'
                if not cache_file.exists():
                    df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date='20240101', end_date='20241231', adjust='qfq')
                    if df is not None and not df.empty:
                        with open(cache_file, 'wb') as f:
                            pickle.dump(df, f)
                        success_2024 += 1
                        print(f"[{i+1}/{len(all_missing)}] {code} 2024: {len(df)}条")
                    else:
                        failed_2024 += 1
                        print(f"[{i+1}/{len(all_missing)}] {code} 2024: 无数据")
                else:
                    print(f"[{i+1}/{len(all_missing)}] {code} 2024: 已存在")

            # 下载2025年数据
            if code in missing_2025:
                cache_file = cache_dir / f'stock_hist_{code}_20250101_20251231_qfq.pkl'
                if not cache_file.exists():
                    df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date='20250101', end_date='20251231', adjust='qfq')
                    if df is not None and not df.empty:
                        with open(cache_file, 'wb') as f:
                            pickle.dump(df, f)
                        success_2025 += 1
                        print(f"  └─ 2025: {len(df)}条")
                    else:
                        failed_2025 += 1
                        print(f"  └─ 2025: 无数据")
                else:
                    print(f"  └─ 2025: 已存在")

        except Exception as e:
            if code in missing_2024:
                failed_2024 += 1
            if code in missing_2025:
                failed_2025 += 1
            print(f"[{i+1}/{len(all_missing)}] {code}: 失败 - {str(e)[:40]}")

        # 延迟避免反爬虫
        time.sleep(0.2)

        if (i + 1) % 20 == 0:
            print(f"\n=== 进度: {i+1}/{len(all_missing)}, 成功2024:{success_2024}, 2025:{success_2025} ===\n")
            time.sleep(3)

    print(f"\n{'='*80}")
    print("下载完成")
    print(f"{'='*80}")
    print(f"2024年: 成功{success_2024}, 失败{failed_2024}")
    print(f"2025年: 成功{success_2025}, 失败{failed_2025}")

    # 记录日志
    log_file = Path('data/download_ipo_log.txt')
    with open(log_file, 'a') as f:
        f.write(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 下载完成\n")
        f.write(f"2024年: 成功{success_2024}, 失败{failed_2024}\n")
        f.write(f"2025年: 成功{success_2025}, 失败{failed_2025}\n")

    return success_2024 + success_2025, failed_2024 + failed_2025


if __name__ == '__main__':
    download_missing_ipo()
