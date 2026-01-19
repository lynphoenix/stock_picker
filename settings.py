# -*- coding: utf-8 -*-
"""
全局配置文件
只包含全局性的配置，策略参数在策略类内部定义
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# 数据目录配置
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
BACKTEST_RESULTS_DIR = DATA_DIR / "backtest_results"

# 缓存配置
CACHE_ENABLED = True
CACHE_EXPIRE_DAYS = 7  # 缓存过期天数

# 网络请求配置
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
REQUEST_DELAY = 0.1  # 请求间隔（秒）

# 并发配置
MAX_WORKERS = 4

# 日志配置
LOG_LEVEL = "INFO"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

# 回测默认配置
DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_MAX_POSITIONS = 5
DEFAULT_POSITION_SIZE = 0.2  # 每个仓位占资金的比例

# 数据源配置
DEFAULT_ADJUST = "qfq"  # 前复权

# 创建必要的目录
for dir_path in [DATA_DIR, CACHE_DIR, BACKTEST_RESULTS_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
