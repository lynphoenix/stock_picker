#!/usr/bin/env python3
"""清理重复的股票缓存记录，只保留最新的合并版本"""
import sqlite3
import zlib
import json
import pandas as pd

DB_PATH = 'core/data/stock_cache.db'

def normalize_date(date_str):
    """标准化日期格式为 YYYY-MM-DD"""
    if not date_str:
        return date_str
    # 移除所有分隔符
    cleaned = date_str.replace('-', '').replace('/', '').replace('.', '')
    # 如果是8位数字，转换为 YYYY-MM-DD
    if len(cleaned) == 8 and cleaned.isdigit():
        return f"{cleaned[:4]}-{cleaned[4:6]}-{cleaned[6:8]}"
    return date_str

def cleanup_duplicates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 找出所有有重复的股票
    cursor.execute("""
        SELECT symbol, COUNT(*) as cnt
        FROM stock_cache
        GROUP BY symbol
        HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()

    print(f"找到 {len(duplicates)} 只股票有重复记录")

    for symbol, cnt in duplicates:
        print(f"处理 {symbol} ({cnt} 条记录)...")

        # 获取该股票的所有记录
        cursor.execute("""
            SELECT id, start_date, end_date, data
            FROM stock_cache
            WHERE symbol = ?
            ORDER BY updated_at DESC
        """, (symbol,))
        records = cursor.fetchall()

        if not records:
            continue

        # 合并所有数据
        all_dates = set()
        all_data_frames = []

        for record_id, start_date, end_date, data in records:
            if data:
                try:
                    decompressed = zlib.decompress(data).decode('utf-8')
                    df_list = json.loads(decompressed)
                    if df_list and isinstance(df_list, list):
                        df = pd.DataFrame(df_list)
                        if 'date' in df.columns:
                            # 标准化日期
                            df['date'] = df['date'].apply(lambda x: normalize_date(str(x)))
                            all_data_frames.append(df)
                            # 收集所有日期
                            for d in df['date'].tolist():
                                all_dates.add(normalize_date(str(d)))
                except Exception as e:
                    print(f"  处理记录失败: {e}")

        if not all_data_frames:
            print(f"  跳过 - 无有效数据")
            continue

        # 合并数据
        merged = pd.concat(all_data_frames).drop_duplicates(subset=['date'], keep='last')
        merged = merged.sort_values('date').reset_index(drop=True)

        # 新的日期范围
        sorted_dates = sorted(all_dates)
        new_start = normalize_date(sorted_dates[0])
        new_end = normalize_date(sorted_dates[-1])

        print(f"  合并后: {new_start} ~ {new_end}, {len(merged)} 条数据")

        # 删除所有旧记录
        cursor.execute("DELETE FROM stock_cache WHERE symbol = ?", (symbol,))

        # 插入合并后的新记录
        json_str = merged.to_json(orient='records', force_ascii=False)
        compressed = zlib.compress(json_str.encode('utf-8'))
        cursor.execute("""
            INSERT INTO stock_cache (symbol, data_type, start_date, end_date, data, source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (symbol, 'daily', new_start, new_end, compressed, 'merged'))

    conn.commit()
    conn.close()
    print("完成!")

if __name__ == '__main__':
    cleanup_duplicates()
