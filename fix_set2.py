# Fix the set method to normalize dates

with open('core/data/auto_fetcher.py', 'r') as f:
    lines = f.readlines()

# Find the section to modify and fix it
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]

    # Replace the old date format conversion with normalized date handling
    if '# 格式化日期：YYYYMMDD -> YYYY-MM-DD' in line:
        # Skip the old conversion lines
        if i + 1 < len(lines) and 'if len(start_date) == 8:' in lines[i+1]:
            i += 3  # skip the if blocks
            if i < len(lines) and 'if len(end_date) == 8:' in lines[i]:
                i += 3  # skip more
            # Add new normalization
            new_lines.append('            # 确保日期格式为 YYYY-MM-DD\n')
            new_lines.append('            start_date = self._normalize_date(start_date) if start_date else start_date\n')
            new_lines.append('            end_date = self._normalize_date(end_date) if end_date else end_date\n')
            continue

    # Fix the all_dates.add line to normalize dates
    if 'all_dates.add(str(d[\'date\']))' in line:
        # Replace with normalized version
        new_line = line.replace(
            "all_dates.add(str(d['date']))",
            "all_dates.add(self._normalize_date(str(d['date'])))"
        )
        new_lines.append(new_line)
        i += 1
        continue

    # Fix the merged_data concat section
    if 'merged_data = pd.concat([merged_data, old_df_df]).drop_duplicates(subset=[\'date\'], keep=\'last\')' in line:
        # Insert date normalization before this line
        new_lines.append('                                        # 标准化日期列\n')
        new_lines.append('                                        old_df_df[\'date\'] = old_df_df[\'date\'].apply(lambda x: self._normalize_date(str(x)))\n')
        new_lines.append(line)
        i += 1
        continue

    new_lines.append(line)
    i += 1

with open('core/data/auto_fetcher.py', 'w') as f:
    f.writelines(new_lines)

print('Fixed!')
