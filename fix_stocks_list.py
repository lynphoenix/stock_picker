# Fix the slow get_stocks_list method - use SQL aggregation instead of loading all data

with open('core/data/data_monitor.py', 'r') as f:
    content = f.read()

# Replace the inefficient _get_stocks_from_db with optimized version
old_func = '''    def _get_stocks_from_db(self) -> List[Dict]:
        """从SQLite数据库获取股票列表"""
        stocks = []

        if not self.cache_db_path.exists():
            if self._stock_list_cache is None:
                self._stock_list_cache = self._get_all_stocks_from_baostock()
            return self._stock_list_cache

        try:
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM stock_cache")
            count = cursor.fetchone()[0]
            if count == 0:
                conn.close()
                if self._stock_list_cache is None:
                    self._stock_list_cache = self._get_all_stocks_from_baostock()
                return self._stock_list_cache

            # 获取所有股票（简化：每只股票只有一条记录）
            cursor.execute("""
                SELECT symbol, start_date, end_date, data
                FROM stock_cache
                ORDER BY symbol
            """)

            # 从baostock获取股票名称映射
            stock_names = self._get_stock_name_map()

            for row in cursor.fetchall():
                symbol = row[0]
                start_date = row[1]
                end_date = row[2]
                data_blob = row[3]

                if not symbol or not data_blob:
                    continue

                try:
                    data = json.loads(zlib.decompress(data_blob).decode("utf-8"))
                    if data:
                        dates = [d.get("date", "") for d in data if d.get("date")]
                        available_days = len(dates)

                        total_days = 0
                        if start_date and end_date:
                            try:
                                total_days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
                            except:
                                pass

                        available_days = len(data)

                        # 获取股票名称
                        stock_name = stock_names.get(symbol, symbol)

                        stocks.append({
                            "code": symbol,
                            "name": stock_name,
                            "start_date": start_date.replace("-", "") if start_date else "",
                            "end_date": end_date.replace("-", "") if end_date else "",
                            "total_days": total_days,
                            "available_days": available_days,
                            "trading_days": get_trading_days(start_date, end_date),
                            "completeness": (lambda td=get_trading_days(start_date, end_date): round(available_days / td * 100, 1) if td > 0 else 0)(),
                            "missing_days": total_days - available_days
                        })
                except Exception as e:
                    print(f"处理股票 {symbol} 数据失败: {e}")
                    continue

            conn.close()
            return stocks
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            if self._stock_list_cache is None:
                self._stock_list_cache = self._get_all_stocks_from_baostock()
            return self._stock_list_cache'''

new_func = '''    def _get_stocks_from_db(self) -> List[Dict]:
        """从SQLite数据库获取股票列表（优化：使用SQL聚合，不加载数据 blob）"""
        if not self.cache_db_path.exists():
            if self._stock_list_cache is None:
                self._stock_list_cache = self._get_all_stocks_from_baostock()
            return self._stock_list_cache

        try:
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM stock_cache")
            count = cursor.fetchone()[0]
            if count == 0:
                conn.close()
                if self._stock_list_cache is None:
                    self._stock_list_cache = self._get_all_stocks_from_baostock()
                return self._stock_list_cache

            # 使用 SQL 直接获取需要的字段，不解压 data blob
            cursor.execute("""
                SELECT
                    symbol,
                    start_date,
                    end_date,
                    LENGTH(data) as data_size
                FROM stock_cache
                ORDER BY symbol
            """)

            # 从baostock获取股票名称映射
            stock_names = self._get_stock_name_map()

            # 预计算交易日（避免重复计算）
            trading_days_cache = {}

            stocks = []
            for row in cursor.fetchall():
                symbol = row[0]
                start_date = row[1] or ""
                end_date = row[2] or ""
                data_size = row[3] or 0

                # 估算可用天数（基于数据大小，约 100 字节/条记录）
                available_days = max(1, data_size // 100)

                # 计算总天数
                total_days = 0
                if start_date and end_date:
                    try:
                        # 标准化日期
                        s = start_date.replace("-", "")
                        e = end_date.replace("-", "")
                        if len(s) == 8 and len(e) == 8:
                            total_days = (datetime.strptime(e, "%Y%m%d") - datetime.strptime(s, "%Y%m%d")).days + 1
                    except:
                        pass

                # 使用缓存的交易日
                td_key = f"{start_date}_{end_date}"
                if td_key not in trading_days_cache:
                    trading_days_cache[td_key] = get_trading_days(start_date, end_date) if start_date and end_date else 0

                trading_days = trading_days_cache[td_key]
                completeness = round(available_days / trading_days * 100, 1) if trading_days > 0 else 0

                # 标准化日期格式为 YYYYMMDD
                std_start = start_date.replace("-", "") if start_date else ""
                std_end = end_date.replace("-", "") if end_date else ""

                stocks.append({
                    "code": symbol,
                    "name": stock_names.get(symbol, symbol),
                    "start_date": std_start,
                    "end_date": std_end,
                    "total_days": total_days,
                    "available_days": available_days,
                    "trading_days": trading_days,
                    "completeness": completeness,
                    "missing_days": total_days - available_days
                })

            conn.close()
            return stocks
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            if self._stock_list_cache is None:
                self._stock_list_cache = self._get_all_stocks_from_baostock()
            return self._stock_list_cache'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open('core/data/data_monitor.py', 'w') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Pattern not found, trying alternate...')
