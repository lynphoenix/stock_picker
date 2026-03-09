# Fix the slow loop in _get_stocks_from_db

with open('core/data/data_monitor.py', 'r') as f:
    lines = f.readlines()

# Find the lines to replace
new_lines = []
skip_until = None
i = 0

while i < len(lines):
    line = lines[i]

    # Find the start of the problematic loop
    if 'for row in cursor.fetchall():' in line:
        # Skip old loop and replace with optimized version
        new_lines.append('            # 预计算交易日缓存\n')
        new_lines.append('            trading_days_cache = {}\n')
        new_lines.append('\n')
        new_lines.append('            for row in cursor.fetchall():\n')
        new_lines.append('                symbol = row[0]\n')
        new_lines.append('                start_date = row[1] or ""\n')
        new_lines.append('                end_date = row[2] or ""\n')
        new_lines.append('                data_size = row[3] or 0\n')
        new_lines.append('\n')
        new_lines.append('                if not symbol:\n')
        new_lines.append('                    continue\n')
        new_lines.append('\n')
        new_lines.append('                # 估算可用天数（基于数据大小，约100字节/条记录）\n')
        new_lines.append('                available_days = max(1, data_size // 100)\n')
        new_lines.append('\n')
        new_lines.append('                # 计算总天数\n')
        new_lines.append('                total_days = 0\n')
        new_lines.append('                if start_date and end_date:\n')
        new_lines.append('                    try:\n')
        new_lines.append('                        s = start_date.replace("-", "")\n')
        new_lines.append('                        e = end_date.replace("-", "")\n')
        new_lines.append('                        if len(s) == 8 and len(e) == 8:\n')
        new_lines.append('                            total_days = (datetime.strptime(e, "%Y%m%d") - datetime.strptime(s, "%Y%m%d")).days + 1\n')
        new_lines.append('                    except:\n')
        new_lines.append('                        pass\n')
        new_lines.append('\n')
        new_lines.append('                # 使用缓存的交易日\n')
        new_lines.append('                td_key = f"{start_date}_{end_date}"\n')
        new_lines.append('                if td_key not in trading_days_cache:\n')
        new_lines.append('                    trading_days_cache[td_key] = get_trading_days(start_date, end_date) if start_date and end_date else 0\n')
        new_lines.append('\n')
        new_lines.append('                trading_days = trading_days_cache[td_key]\n')
        new_lines.append('                completeness = round(available_days / trading_days * 100, 1) if trading_days > 0 else 0\n')
        new_lines.append('\n')
        new_lines.append('                stocks.append({\n')
        new_lines.append('                    "code": symbol,\n')
        new_lines.append('                    "name": stock_names.get(symbol, symbol),\n')
        new_lines.append('                    "start_date": start_date.replace("-", "") if start_date else "",\n')
        new_lines.append('                    "end_date": end_date.replace("-", "") if end_date else "",\n')
        new_lines.append('                    "total_days": total_days,\n')
        new_lines.append('                    "available_days": available_days,\n')
        new_lines.append('                    "trading_days": trading_days,\n')
        new_lines.append('                    "completeness": completeness,\n')
        new_lines.append('                    "missing_days": total_days - available_days\n')
        new_lines.append('                })\n')

        # Skip the old lines (from 'for row' to the end of that block)
        i += 1
        # Skip until we find the next major section
        brace_count = 0
        while i < len(lines):
            if 'conn.close()' in lines[i]:
                new_lines.append(lines[i])
                i += 1
                break
            i += 1
        continue

    new_lines.append(line)
    i += 1

with open('core/data/data_monitor.py', 'w') as f:
    f.writelines(new_lines)

print('Fixed!')
