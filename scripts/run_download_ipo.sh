#!/bin/bash
# 新IPO数据下载定时任务wrapper
cd /home/smai/linyining/stock_picker
python scripts/download_missing_ipo.py >> data/cron_download.log 2>&1
