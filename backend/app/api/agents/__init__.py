# -*- coding: utf-8 -*-
"""
Agent API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os

# Add the parent api directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from agents.screener_agent import ScreenerAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.signal_agent import SignalAgent

router = APIRouter()

# Initialize agents
screener_agent = ScreenerAgent()
analyzer_agent = AnalyzerAgent()
signal_agent = SignalAgent()


# ==================== Screener Agent ====================

class ScreenerRequest(BaseModel):
    """Screener request model"""
    sector: Optional[str] = None
    min_roe: Optional[float] = None
    max_roe: Optional[float] = None
    min_pe: Optional[float] = None
    max_pe: Optional[float] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    technical: Optional[Dict[str, Any]] = None
    limit: int = 50


class ScreenerResponse(BaseModel):
    """Screener response model"""
    success: bool
    stocks: List[Dict[str, Any]] = []
    total: int = 0
    conditions: Dict[str, Any] = {}


@router.post("/screen", response_model=ScreenerResponse)
async def screen_stocks(request: ScreenerRequest):
    """
    Screen stocks based on criteria

    Args:
        request: Screening criteria

    Returns:
        List of matching stocks
    """
    # Build conditions from request
    conditions = {}
    if request.sector:
        conditions["sectors"] = [request.sector]
    if request.min_roe is not None:
        conditions["roe_min"] = request.min_roe
    if request.max_roe is not None:
        conditions["roe_max"] = request.max_roe
    if request.min_pe is not None:
        conditions["pe_min"] = request.min_pe
    if request.max_pe is not None:
        conditions["pe_max"] = request.max_pe
    if request.min_market_cap is not None:
        conditions["market_cap_min"] = request.min_market_cap
    if request.max_market_cap is not None:
        conditions["market_cap_max"] = request.max_market_cap
    conditions["limit"] = request.limit

    # Execute screening
    stocks = screener_agent.screen(conditions)

    return ScreenerResponse(
        success=True,
        stocks=stocks,
        total=len(stocks),
        conditions=conditions
    )


# ==================== Analyzer Agent ====================

class AnalyzeRequest(BaseModel):
    """Analyze request model"""
    stock_code: str


class AnalyzeResponse(BaseModel):
    """Analyze response model"""
    success: bool
    symbol: str
    name: str = ""
    sector: str = ""
    price: float = 0.0
    change_pct: float = 0.0
    financial_score: float = 0.0
    sentiment_score: float = 0.0
    valuation_score: float = 0.0
    overall_score: float = 0.0
    recommendation: str = ""
    financial_details: Dict[str, Any] = {}
    sentiment_details: Dict[str, Any] = {}
    valuation_details: Dict[str, Any] = {}
    risks: List[str] = []
    opportunities: List[str] = []


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_stock(request: AnalyzeRequest):
    """
    Analyze a single stock

    Args:
        request: Stock code to analyze

    Returns:
        Stock analysis results
    """
    # Parse stock code from request
    stocks = analyzer_agent.parse_stock_code(request.stock_code)

    if not stocks:
        raise HTTPException(status_code=400, detail="无法识别股票代码")

    # Analyze the stock
    analysis = analyzer_agent.analyze_stock(stocks[0])

    return AnalyzeResponse(
        success=True,
        symbol=analysis["symbol"],
        name=analysis["name"],
        sector=analysis["sector"],
        price=analysis["price"],
        change_pct=analysis["change_pct"],
        financial_score=analysis["financial_score"],
        sentiment_score=analysis["sentiment_score"],
        valuation_score=analysis["valuation_score"],
        overall_score=analysis["overall_score"],
        recommendation=analysis["recommendation"],
        financial_details=analysis["financial_details"],
        sentiment_details=analysis["sentiment_details"],
        valuation_details=analysis["valuation_details"],
        risks=analysis["risks"],
        opportunities=analysis["opportunities"]
    )


# ==================== Signal Agent ====================

class SignalRequest(BaseModel):
    """Signal request model"""
    stock_code: str


class SignalResponse(BaseModel):
    """Signal response model"""
    success: bool
    symbol: str
    name: str = ""
    sector: str = ""
    price: float = 0.0
    signal: str = ""
    risk_level: str = ""
    target_price: float = 0.0
    stop_loss: float = 0.0
    position_size: str = ""
    reasoning: List[str] = []


@router.post("/signal", response_model=SignalResponse)
async def get_signal(request: SignalRequest):
    """
    Get trading signal for a stock

    Args:
        request: Stock code

    Returns:
        Trading signal
    """
    # Parse stock code from request
    stocks = analyzer_agent.parse_stock_code(request.stock_code)

    if not stocks:
        raise HTTPException(status_code=400, detail="无法识别股票代码")

    # Get signal for the stock
    signal_result = await signal_agent.execute(f"{request.stock_code}可以买吗")

    if not signal_result.get("success"):
        raise HTTPException(status_code=500, detail=signal_result.get("error", "生成信号失败"))

    # Parse signal from result
    content = signal_result.get("formatted_results", "")

    # Extract signal info (simplified parsing)
    signal = "持有"  # default
    if "买入" in content:
        signal = "买入"
    elif "卖出" in content:
        signal = "卖出"

    # Extract target price and stop loss
    target_price = 0.0
    stop_loss = 0.0

    import re
    target_match = re.search(r'目标价.*?(\d+\.?\d*)', content)
    if target_match:
        target_price = float(target_match.group(1))

    stop_match = re.search(r'止损价.*?(\d+\.?\d*)', content)
    if stop_match:
        stop_loss = float(stop_match.group(1))

    # Get stock info
    stock_info = analyzer_agent.analyze_stock(stocks[0])

    return SignalResponse(
        success=True,
        symbol=stocks[0],
        name=stock_info["name"],
        sector=stock_info["sector"],
        price=stock_info["price"],
        signal=signal,
        risk_level="中等",
        target_price=target_price,
        stop_loss=stop_loss,
        position_size="保持当前仓位",
        reasoning=["基于技术分析和基本面评估"]
    )
