# -*- coding: utf-8 -*-
"""
技术指标计算 - 复用现有的 src/technical.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.technical import TechnicalIndicators as _TechnicalIndicators


class TechnicalIndicators(_TechnicalIndicators):
    """
    技术指标计算类

    继承自原有的 TechnicalIndicators，保持向后兼容
    后续可以逐步重构
    """
    pass
