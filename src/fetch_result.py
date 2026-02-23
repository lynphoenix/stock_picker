# -*- coding: utf-8 -*-
"""
数据采集结果封装
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class FetchResult:
    """数据采集结果"""
    success: bool
    data: Optional[pd.DataFrame]
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    source: str = "akshare"

    def __repr__(self) -> str:
        if self.success:
            rows = len(self.data) if self.data is not None else 0
            return f"FetchResult(success=True, rows={rows}, source={self.source})"
        else:
            return f"FetchResult(success=False, error_type={self.error_type}, source={self.source})"
