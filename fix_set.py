import re

with open('core/data/auto_fetcher.py', 'r') as f:
    content = f.read()

# Fix the set method to normalize dates in all_dates
old_block = '''                # 合并历史数据
                for record_id, old_start, old_end, old_data in existing_records:
                    if old_data:
                        try:
                            decompressed = zlib.decompress(old_data).decode('utf-8')
                            old_df = json.loads(decompressed)
                            if old_df and isinstance(old_df, list):
                                for d in old_df:
                                    if isinstance(d, dict) and 'date' in d:
                                        all_dates.add(str(d['date']))
                        except:
                            pass

                # 合并数据
                if all_dates:
                    merged_data = data.copy()
                    for record_id, old_start, old_end, old_data in existing_records:
                        if old_data:
                            try:
                                decompressed = zlib.decompress(old_data).decode('utf-8')
                                old_df = json.loads(decompressed)
                                if old_df and isinstance(old_df, list):
                                    old_df_df = pd.DataFrame(old_df)
                                    if 'date' in old_df_df.columns:
                                        merged_data = pd.concat([merged_data, old_df_df]).drop_duplicates(subset=['date'], keep='last')
                            except:
                                pass

                    # 排序
                    if 'date' in merged_data.columns:
                        merged_data = merged_data.sort_values('date').reset_index(drop=True)

                    # 新的日期范围
                    sorted_dates = sorted(all_dates)
                    start_date = sorted_dates[0]
                    end_date = sorted_dates[-1]
                    data = merged_data

            # 格式化日期：YYYYMMDD -> YYYY-MM-DD
            if len(start_date) == 8:
                start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            if len(end_date) == 8:
                end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"'''

new_block = '''                # 合并历史数据
                for record_id, old_start, old_end, old_data in existing_records:
                    if old_data:
                        try:
                            decompressed = zlib.decompress(old_data).decode('utf-8')
                            old_df = json.loads(decompressed)
                            if old_df and isinstance(old_df, list):
                                for d in old_df:
                                    if isinstance(d, dict) and 'date' in d:
                                        # 标准化日期格式
                                        raw_date = str(d['date'])
                                        all_dates.add(self._normalize_date(raw_date))
                        except Exception as e:
                            print(f"合并历史数据失败: {e}")

                # 合并数据
                if all_dates:
                    merged_data = data.copy()
                    for record_id, old_start, old_end, old_data in existing_records:
                        if old_data:
                            try:
                                decompressed = zlib.decompress(old_data).decode('utf-8')
                                old_df = json.loads(decompressed)
                                if old_df and isinstance(old_df, list):
                                    old_df_df = pd.DataFrame(old_df)
                                    if 'date' in old_df_df.columns:
                                        # 标准化日期列
                                        old_df_df['date'] = old_df_df['date'].apply(lambda x: self._normalize_date(str(x)))
                                        merged_data = pd.concat([merged_data, old_df_df]).drop_duplicates(subset=['date'], keep='last')
                            except Exception as e:
                                print(f"合并数据失败: {e}")

                    # 排序
                    if 'date' in merged_data.columns:
                        merged_data = merged_data.sort_values('date').reset_index(drop=True)

                    # 新的日期范围
                    sorted_dates = sorted(all_dates)
                    start_date = sorted_dates[0]
                    end_date = sorted_dates[-1]
                    data = merged_data

            # 确保日期格式为 YYYY-MM-DD
            start_date = self._normalize_date(start_date) if start_date else start_date
            end_date = self._normalize_date(end_date) if end_date else end_date'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('core/data/auto_fetcher.py', 'w') as f:
        f.write(content)
    print('Fixed set method')
else:
    print('Pattern not found')
