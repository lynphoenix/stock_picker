# Add cache to DataService

with open('backend/app/services/data_service.py', 'r') as f:
    content = f.read()

# Add cache variables to __init__
old_init = '''    def __init__(self):
        self.monitor = DataMonitor()
        self.config_file = Path(root_dir) / "data" / "fetch_schedule.json"
        self.tasks_dir = Path(root_dir) / "data" / "repair_tasks"'''

new_init = '''    def __init__(self):
        self.monitor = DataMonitor()
        self.config_file = Path(root_dir) / "data" / "fetch_schedule.json"
        self.tasks_dir = Path(root_dir) / "data" / "repair_tasks"
        # 股票列表缓存
        self._stocks_cache = None
        self._stocks_cache_time = None
        self._stocks_cache_ttl = 60  # 缓存60秒'''

content = content.replace(old_init, new_init)

# Modify get_stocks_list to use cache
old_get_stocks = '''    def get_stocks_list(
        self,
        market: str = "all",
        sort_by: str = "completeness",
        only_missing: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> StockDataList:
        """获取股票数据列表"""
        data = self.monitor.get_stocks_list('''

new_get_stocks = '''    def get_stocks_list(
        self,
        market: str = "all",
        sort_by: str = "completeness",
        only_missing: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> StockDataList:
        """获取股票数据列表（带缓存）"""
        from datetime import datetime
        now = datetime.now()

        # 检查缓存是否有效
        if (self._stocks_cache is not None and
            self._stocks_cache_time is not None and
            (now - self._stocks_cache_time).total_seconds() < self._stocks_cache_ttl and
            self._stocks_cache.get('market') == market and
            self._stocks_cache.get('sort_by') == sort_by):

            # 返回缓存数据
            cached = self._stocks_cache
            total = cached['total']
            offset = (page - 1) * page_size
            paginated = cached['stocks'][offset:offset + page_size]
            stocks = [StockDataItem(**item) for item in paginated]
            return StockDataList(
                total=total,
                page=page,
                page_size=page_size,
                stocks=stocks
            )

        # 重新获取
        data = self.monitor.get_stocks_list('''

content = content.replace(old_get_stocks, new_get_stocks)

# After getting data, save to cache
old_return = '''        stocks = [StockDataItem(**item) for item in data["stocks"]]

        return StockDataList(
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
            stocks=stocks
        )'''

new_return = '''        stocks = [StockDataItem(**item) for item in data["stocks"]]

        # 保存到缓存
        self._stocks_cache = {
            'market': market,
            'sort_by': sort_by,
            'total': data['total'],
            'stocks': data['stocks']
        }
        self._stocks_cache_time = now

        return StockDataList(
            total=data["total"],
            page=data["page"],
            page_size=data["page_size"],
            stocks=stocks
        )'''

content = content.replace(old_return, new_return)

with open('backend/app/services/data_service.py', 'w') as f:
    f.write(content)

print('Fixed!')
