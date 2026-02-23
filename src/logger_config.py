# -*- coding: utf-8 -*-
"""
日志配置模块
"""
import logging
from pathlib import Path
from datetime import datetime


def setup_logger(name: str, log_file: str = None, level=logging.INFO):
    """
    配置日志器

    Args:
        name: 日志器名称
        log_file: 日志文件路径，默认为 data/logs/{name}_{date}.log
        level: 日志级别

    Returns:
        配置好的logger实例
    """
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 默认日志文件路径
    if log_file is None:
        date_str = datetime.now().strftime('%Y%m%d')
        log_file = f"data/logs/{name}_{date_str}.log"

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 文件handler - 记录所有级别
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)

    # 控制台handler - 只显示WARNING及以上
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # 添加handlers
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
