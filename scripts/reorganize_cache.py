# -*- coding: utf-8 -*-
"""
重组缓存文件结构：每年一个pkl文件
"""

import re
import pickle
from pathlib import Path
from collections import defaultdict
import pandas as pd
from datetime import datetime


def reorganize_to_yearly_files():
    """重组为每年一个文件"""

    cache_dir = Path('data/cache')
    backup_dir = Path('data/cache_backup')
    backup_dir.mkdir(exist_ok=True)

    pattern = re.compile(r'stock_hist_([^_]+)_(\d{8})_(\d{8})')

    # 扫描所有文件
    files = list(cache_dir.glob('stock_hist_*.pkl'))
    by_code = defaultdict(list)

    for f in files:
        m = pattern.search(f.name)
        if m:
            code = m.group(1)
            start = m.group(2)
            end = m.group(3)
            by_code[code].append((f, start, end))

    print(f'总股票: {len(by_code)}')
    print(f'总文件: {len(files)}')

    # 统计需要处理的
    to_split = [c for c, fs in by_code.items() if len(fs) > 0]
    print(f'需要处理的股票: {len(to_split)}')

    # 创建临时目录存放新文件
    temp_dir = Path('data/cache_new')
    temp_dir.mkdir(exist_ok=True)

    processed = 0
    skipped = 0
    error = 0

    for code, file_list in by_code.items():
        try:
            # 读取所有数据并合并
            all_data = []

            for f, start, end in sorted(file_list, key=lambda x: x[1]):
                try:
                    with open(f, 'rb') as file:
                        df = pickle.load(file)
                        if df is not None and not df.empty:
                            all_data.append(df)
                except Exception as e:
                    print(f'  读取失败 {f.name}: {e}')

            if not all_data:
                skipped += 1
                continue

            # 合并数据
            merged = pd.concat(all_data, ignore_index=True)

            # 确保有date列
            if 'date' not in merged.columns:
                skipped += 1
                continue

            # 转换日期
            merged['date'] = pd.to_datetime(merged['date'])

            # 按年份分组
            by_year = defaultdict(list)
            for _, row in merged.iterrows():
                year = row['date'].year
                by_year[year].append(row)

            # 每年保存一个文件
            for year, rows in by_year.items():
                year_df = pd.DataFrame(rows)
                start_date = f'{year}0101'
                end_date = f'{year}1231'

                # 只保留该年的数据
                year_df = year_df[(year_df['date'].dt.year == year)]

                if year_df.empty:
                    continue

                cache_key = f'stock_hist_{code}_{start_date}_{end_date}_qfq'
                cache_file = temp_dir / f'{cache_key}.pkl'

                with open(cache_file, 'wb') as f:
                    pickle.dump(year_df, f)

            processed += 1

            if processed % 100 == 0:
                print(f'进度: {processed}/{len(to_split)}')

        except Exception as e:
            print(f'处理 {code} 失败: {e}')
            error += 1

    print(f'\n完成:')
    print(f'  处理: {processed}')
    print(f'  跳过: {skipped}')
    print(f'  错误: {error}')
    print(f'  新文件保存在: {temp_dir}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='重组缓存为每年一个文件')
    parser.add_argument('--execute', action='store_true', help='执行重组（否则只分析）')

    args = parser.parse_args()

    if args.execute:
        reorganize_to_yearly_files()
    else:
        # 只分析
        print('分析模式 - 显示将要执行的操作')
        print('要执行重组，运行: python scripts/reorganize_cache.py --execute')
