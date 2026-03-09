# Fix get_trading_days caching properly

with open('core/data/data_monitor.py', 'r') as f:
    content = f.read()

# Fix the broken cache code
old_code = '''def get_trading_days(start_date: str, end_date: str) -> int:
    """获取日期范围内的交易日数量"""
    dates = get_trading_days_set()
    if not dates:
        return count_weekdays(start_date, end_date)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        count = 0
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            if date_str in dates:
                count += 1
            current += timedelta(days=1)
        result = count if count > 0 else count_weekdays(start_date, end_date)
ING_DAYS_CACHE[key] = result
        return result        _TRAD
    except:
        result = count_weekdays(start_date, end_date)
        _TRADING_DAYS_CACHE[key] = result
        return result'''

new_code = '''# 交易日计算缓存
_TRADING_DAYS_CACHE = {}

def get_trading_days(start_date: str, end_date: str) -> int:
    """获取日期范围内的交易日数量（带缓存）"""
    global _TRADING_DAYS_CACHE

    # 标准化日期格式
    key = f"{start_date}_{end_date}"
    if key in _TRADING_DAYS_CACHE:
        return _TRADING_DAYS_CACHE[key]

    dates = get_trading_days_set()
    if not dates:
        result = count_weekdays(start_date, end_date)
        _TRADING_DAYS_CACHE[key] = result
        return result

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        count = 0
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            if date_str in dates:
                count += 1
            current += timedelta(days=1)
        result = count if count > 0 else count_weekdays(start_date, end_date)
        _TRADING_DAYS_CACHE[key] = result
        return result
    except:
        result = count_weekdays(start_date, end_date)
        _TRADING_DAYS_CACHE[key] = result
        return result'''

content = content.replace(old_code, new_code)

with open('core/data/data_monitor.py', 'w') as f:
    f.write(content)

print('Fixed!')
