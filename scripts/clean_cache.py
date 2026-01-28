# -*- coding: utf-8 -*-
"""
清理重复缓存文件
策略：保留最完整的文件，删除被覆盖的冗余文件
"""

import re
from pathlib import Path
from collections import defaultdict


def analyze_files():
    """分析文件，找出需要删除的"""
    cache_dir = Path('data/cache')
    pattern = re.compile(r'stock_hist_([^_]+)_(\d{8})_(\d{8})')

    files = list(cache_dir.glob('stock_hist_*.pkl'))
    print(f'总文件数: {len(files)}')

    # 按股票代码分组
    by_code = defaultdict(list)
    for f in files:
        m = pattern.search(f.name)
        if m:
            code = m.group(1)
            start = m.group(2)
            end = m.group(3)
            by_code[code].append((f, start, end))

    # 分析每只股票，找出要删除的文件
    to_delete = []
    kept = 0

    for code, file_list in by_code.items():
        if len(file_list) == 1:
            kept += 1
            continue

        # 按日期范围排序
        file_list.sort(key=lambda x: (x[1], x[2]))

        # 找出覆盖范围最大的文件（通常是跨年度大文件）
        # 以及整年文件，删除被覆盖的月度/小范围文件

        # 标记被覆盖的文件
        covered = set()

        for i, (f1, start1, end1) in enumerate(file_list):
            for j, (f2, start2, end2) in enumerate(file_list):
                if i >= j:
                    continue  # 同一个文件或已比较过的

                # 如果 f2 完全覆盖 f1，且 f2 不是月度文件
                if start2 <= start1 and end2 >= end1:
                    # 检查是否都是整年文件
                    is_f1_year = start1[4:] == '0101' and end1[4:] == '1231'
                    is_f2_year = start2[4:] == '0101' and end2[4:] == '1231'

                    # 如果 f2 是整年或跨年文件，f1 被覆盖
                    if is_f2_year or (end2[:4] != start2[:4]):  # 跨年
                        # f1 是月度文件或被完全覆盖
                        covered.add(f1)

        to_delete.extend(covered)
        kept += len(file_list) - len(covered)

    return to_delete, kept


def clean_duplicates(dry_run=True, show_list=False):
    """清理重复文件"""
    to_delete, kept = analyze_files()

    print(f'\n{'='*80}')
    print('清理分析结果')
    print(f'{'='*80}')
    print(f'保留文件: {kept}')
    print(f'删除文件: {len(to_delete)}')
    print(f'节省空间: {sum(f.stat().st_size for f in to_delete) / 1024 / 1024:.1f} MB')

    if show_list:
        print(f'\n{'='*80}')
        print('待删除文件列表（前100个）:')
        print(f'{'='*80}')
        for i, f in enumerate(sorted(to_delete)[:100]):
            size_kb = f.stat().st_size / 1024
            print(f'{i+1:4d}. {f.name} ({size_kb:.1f}KB)')

        if len(to_delete) > 100:
            print(f'\n... 还有 {len(to_delete) - 100} 个文件')

    if dry_run:
        print(f'\n[模拟运行] 不会实际删除文件')
        print(f'\n要实际删除，运行: python scripts/clean_cache.py --execute')
    else:
        print(f'\n[执行删除]')
        for f in to_delete:
            f.unlink()
        print(f'已删除 {len(to_delete)} 个文件')

    return to_delete


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='清理重复缓存文件')
    parser.add_argument('--execute', action='store_true', help='实际删除文件')
    parser.add_argument('--show-list', action='store_true', help='显示待删除文件列表')

    args = parser.parse_args()

    clean_duplicates(dry_run=not args.execute, show_list=args.show_list)
