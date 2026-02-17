# AI Investment Assistant Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an intelligent investment research assistant that combines market data analysis, sentiment analysis, and financial statement analysis to provide stock trading signals with explanation and verification.

**Architecture:** Multi-tier system with RAG + Agent architecture. Frontend (React chat/dashboard) → API (FastAPI) → Agent Layer (LangGraph) → RAG Knowledge Layer (ChromaDB/PostgreSQL) → Data Sources (Tushare/Baostock/News APIs).

**Tech Stack:** React 18, TypeScript, FastAPI, LangGraph/LangChain, DeepSeek/OpenAI API, ChromaDB, PostgreSQL, Redis.

---

## Phase 0: Infrastructure Setup (1 week)

### Task 0.1: Create Project Structure

**Files:**
- Create: `core/agents/__init__.py`
- Create: `core/rag/__init__.py`
- Create: `core/sentiment/__init__.py`
- Create: `core/financial/__init__.py`
- Create: `backend/app/api/chat.py`
- Create: `backend/app/api/data_quality.py`
- Create: `backend/app/services/agent_service.py`
- Create: `frontend/src/pages/Chat.tsx`
- Create: `frontend/src/pages/DataMonitor.tsx`

**Step 1: Create the agent module structure**

```bash
mkdir -p core/agents core/rag core/sentiment core/financial
touch core/agents/__init__.py core/rag/__init__.py core/sentiment/__init__.py core/financial/__init__.py
```

**Step 2: Create the backend API structure**

```bash
mkdir -p backend/app/services
touch backend/app/api/chat.py backend/app/api/data_quality.py
touch backend/app/services/agent_service.py backend/app/services/data_quality_service.py
```

**Step 3: Create the frontend page structure**

```bash
mkdir -p frontend/src/pages
touch frontend/src/pages/Chat.tsx frontend/src/pages/DataMonitor.tsx
```

**Step 4: Commit**

```bash
git add core/agents core/rag core/sentiment core/financial backend/app/api/chat.py backend/app/api/data_quality.py backend/app/services frontend/src/pages
git commit -m "feat: create project structure for AI Investment Assistant"
```

---

### Task 0.2: Update Dependencies

**Files:**
- Modify: `requirements.txt`
- Modify: `frontend/package.json`

**Step 1: Add backend dependencies to requirements.txt**

```bash
cat >> requirements.txt << 'EOF'
# AI/LLM
langchain>=0.1.0
langgraph>=0.0.20
langchain-openai>=0.0.5
openai>=1.0.0

# Vector Database
chromadb>=0.4.0

# Additional Data Processing
beautifulsoup4>=4.12.0
lxml>=4.9.0
feedparser>=6.0.0

# Async
httpx>=0.25.0
aiohttp>=3.9.0

# WebSocket
websockets>=12.0
python-socketio>=5.10.0
EOF
```

**Step 2: Add frontend dependencies**

```bash
cd frontend && npm install --save \
  @langchain/core \
  @langchain/openai \
  react-markdown \
  recharts \
  lucide-react \
  tailwind-merge
cd ..
```

**Step 3: Commit**

```bash
git add requirements.txt frontend/package.json frontend/package-lock.json
git commit -m "deps: add AI/LLM and frontend dependencies"
```

---

## Phase 1: Data Layer (2 weeks)

### Task 1.1: Create Multi-Source Data Manager

**Files:**
- Create: `core/data/multi_source_manager.py`
- Test: `tests/test_multi_source_manager.py`

**Step 1: Write the failing test**

```python
# tests/test_multi_source_manager.py
import pytest
from core.data.multi_source_manager import MultiSourceDataManager, DataSourcePriority

@pytest.mark.asyncio
async def test_data_source_fallback():
    """Test that data sources fallback correctly"""
    manager = MultiSourceDataManager()

    # Mock primary source to fail
    async def failing_source(code, start, end):
        raise Exception("Primary source failed")

    # Mock secondary source to succeed
    async def secondary_source(code, start, end):
        return {"code": code, "data": [1, 2, 3]}

    manager.register_source("primary", failing_source, priority=1)
    manager.register_source("secondary", secondary_source, priority=2)

    result = await manager.get_data("000001", "20240101", "20240131")

    assert result is not None
    assert result["data"] == [1, 2, 3]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_multi_source_manager.py::test_data_source_fallback -v
```
Expected: `ModuleNotFoundError: No module named 'core.data.multi_source_manager'`

**Step 3: Write minimal implementation**

```python
# core/data/multi_source_manager.py
from typing import List, Dict, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    REALTIME = "realtime"
    HISTORICAL = "historical"
    FINANCIAL = "financial"
    NEWS = "news"

@dataclass
class DataSource:
    name: str
    func: Callable
    priority: int = 1
    source_type: DataSourceType = DataSourceType.HISTORICAL
    enabled: bool = True

class MultiSourceDataManager:
    """Multi-source data manager with automatic fallback"""

    def __init__(self):
        self._sources: Dict[str, List[DataSource]] = {
            data_type.value: []
            for data_type in DataSourceType
        }

    def register_source(
        self,
        name: str,
        func: Callable,
        priority: int = 1,
        source_type: DataSourceType = DataSourceType.HISTORICAL
    ):
        """Register a data source"""
        source = DataSource(name=name, func=func, priority=priority, source_type=source_type)
        sources = self._sources[source_type.value]
        sources.append(source)
        # Sort by priority (lower number = higher priority)
        sources.sort(key=lambda s: s.priority)

    async def get_data(
        self,
        code: str,
        start_date: str,
        end_date: str,
        source_type: DataSourceType = DataSourceType.HISTORICAL,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Get data from available sources with fallback"""
        sources = self._sources[source_type.value]

        for source in sources:
            if not source.enabled:
                continue

            try:
                logger.info(f"Trying {source.name} for {code}")
                result = await source.func(code, start_date, end_date, **kwargs)
                if result:
                    logger.info(f"Successfully fetched from {source.name}")
                    return result
            except Exception as e:
                logger.warning(f"{source.name} failed: {e}")
                continue

        logger.error(f"All sources failed for {code}")
        return None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_multi_source_manager.py::test_data_source_fallback -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_multi_source_manager.py core/data/multi_source_manager.py
git commit -m "feat: add multi-source data manager with fallback support"
```

---

### Task 1.2: Implement Tushare Real-time Data Provider

**Files:**
- Create: `core/data/providers/tushare_realtime.py`
- Test: `tests/test_tushare_realtime.py`

**Step 1: Write the failing test**

```python
# tests/test_tushare_realtime.py
import pytest
from core.data.providers.tushare_realtime import TushareRealtimeProvider

@pytest.mark.asyncio
async def test_get_minute_data():
    """Test fetching minute-level data from Tushare"""
    provider = TushareRealtimeProvider(api_token="test_token")

    # Mock the API call
    provider._api_call = lambda *args, **kwargs: {
        "items": [["2026-02-17 10:30:00", "48.50", "48.80", "48.40", "48.70", "10000"]]
    }

    result = await provider.get_minute_data("002230", "2026-02-17 09:30:00", "2026-02-17 15:00:00")

    assert result is not None
    assert len(result) > 0
    assert "close" in result.columns
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_tushare_realtime.py::test_get_minute_data -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/data/providers/tushare_realtime.py
import pandas as pd
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TushareRealtimeProvider:
    """Tushare Pro real-time and minute-level data provider"""

    def __init__(self, api_token: str):
        self.api_token = api_token
        self._ts = None

    def _get_ts(self):
        """Lazy import and initialize tushare"""
        if self._ts is None:
            import tushare as ts
            ts.set_token(self.api_token)
            self._ts = ts.pro_api()
        return self._ts

    async def get_minute_data(
        self,
        code: str,
        start_time: str,
        end_time: str
    ) -> Optional[pd.DataFrame]:
        """
        Get minute-level data

        Args:
            code: Stock code (e.g., "002230")
            start_time: Start time "YYYY-MM-DD HH:MM:SS"
            end_time: End time "YYYY-MM-DD HH:MM:SS"

        Returns:
            DataFrame with columns: [time, open, high, low, close, volume]
        """
        try:
            ts = self._get_ts()

            # Convert code to Tushare format
            ts_code = self._convert_code(code)

            # Parse dates
            trade_date = start_time.split()[0].replace("-", "")

            # Fetch minute data
            df = ts.stk_mins(
                ts_code=ts_code,
                trade_date=trade_date,
                start_time=start_time.split()[1].replace(":", ""),
                end_time=end_time.split()[1].replace(":", "")
            )

            if df.empty:
                logger.warning(f"No minute data for {code} on {trade_date}")
                return None

            # Standardize column names
            df = self._standardize_columns(df)
            return df

        except Exception as e:
            logger.error(f"Failed to fetch minute data for {code}: {e}")
            return None

    def _convert_code(self, code: str) -> str:
        """Convert code to Tushare format"""
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith("8"):
            return f"{code}.BJ"
        return code

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names"""
        column_map = {
            "trade_time": "time",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "vol": "volume",
            "amount": "amount"
        }
        df = df.rename(columns=column_map)
        return df
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_tushare_realtime.py::test_get_minute_data -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_tushare_realtime.py core/data/providers/tushare_realtime.py
git commit -m "feat: add Tushare real-time data provider"
```

---

### Task 1.3: Implement News Sentiment Data Provider

**Files:**
- Create: `core/sentiment/news_provider.py`
- Test: `tests/test_news_provider.py`

**Step 1: Write the failing test**

```python
# tests/test_news_provider.py
import pytest
from core.sentiment.news_provider import NewsSentimentProvider

@pytest.mark.asyncio
async def test_fetch_stock_news():
    """Test fetching news for a stock"""
    provider = NewsSentimentProvider()

    # Mock the fetch
    provider._fetch_news = lambda code: [
        {"title": "科大讯飞发布教育大模型", "content": "...", "time": "2026-02-17"}
    ]

    result = await provider.get_news("002230", days=7)

    assert result is not None
    assert len(result) > 0
    assert "title" in result[0]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_news_provider.py::test_fetch_stock_news -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/sentiment/news_provider.py
import aiohttp
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class NewsSentimentProvider:
    """News and sentiment data provider"""

    def __init__(self):
        self.sources = [
            "https://www.cnbc.com/id/*/company/news",
            "https://finance.yahoo.com/rss/headline",
            # Add more sources for Chinese news
        ]

    async def get_news(
        self,
        code: str,
        days: int = 7
    ) -> List[Dict[str, any]]:
        """
        Get news for a stock

        Args:
            code: Stock code
            days: Number of days to look back

        Returns:
            List of news articles with sentiment
        """
        news_list = []

        # Get stock name for search
        # (This would be fetched from database)
        search_keywords = [code]  # Add stock name

        for keyword in search_keywords:
            articles = await self._fetch_from_sina(keyword)
            news_list.extend(articles)

        # Analyze sentiment for each article
        for article in news_list:
            article["sentiment"] = await self._analyze_sentiment(article.get("content", ""))

        return news_list[:50]  # Return top 50

    async def _fetch_from_sina(self, keyword: str) -> List[Dict]:
        """Fetch news from Sina Finance"""
        url = f"http://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{keyword}/p/1.phtml"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    html = await response.text()

            soup = BeautifulSoup(html, 'lxml')
            news_items = []

            for item in soup.select('.list_14'):
                title_elem = item.select_one('a')
                if not title_elem:
                    continue

                news_items.append({
                    "title": title_elem.get_text(strip=True),
                    "url": title_elem.get('href', ''),
                    "source": "sina",
                    "time": self._parse_time(item.select_one('.dat_time'))
                })

            return news_items

        except Exception as e:
            logger.error(f"Failed to fetch from Sina: {e}")
            return []

    async def _analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text

        Returns:
            Score from -1 (negative) to 1 (positive)
        """
        # Simple rule-based sentiment (can be replaced with LLM)
        positive_words = ["上涨", "增长", "利好", "突破", "创新高"]
        negative_words = ["下跌", "亏损", "利空", "跌破", "风险"]

        score = 0
        for word in positive_words:
            score += text.count(word) * 0.1
        for word in negative_words:
            score -= text.count(word) * 0.1

        return max(-1, min(1, score))

    def _parse_time(self, time_elem) -> Optional[str]:
        """Parse time element"""
        if not time_elem:
            return None
        return time_elem.get_text(strip=True)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_news_provider.py::test_fetch_stock_news -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_news_provider.py core/sentiment/news_provider.py
git commit -m "feat: add news sentiment provider"
```

---

### Task 1.4: Implement Financial Statement Parser

**Files:**
- Create: `core/financial/statement_parser.py`
- Test: `tests/test_statement_parser.py`

**Step 1: Write the failing test**

```python
# tests/test_statement_parser.py
import pytest
from core.financial.statement_parser import FinancialStatementParser

@pytest.mark.asyncio
async def test_parse_income_statement():
    """Test parsing income statement"""
    parser = FinancialStatementParser()

    result = await parser.parse_income_statement("002230", "2024-09-30")

    assert result is not None
    assert "revenue" in result
    assert "profit" in result
    assert "roe" in result
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_statement_parser.py::test_parse_income_statement -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/financial/statement_parser.py
import logging
from typing import Dict, Optional
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)

class FinancialStatementParser:
    """Financial statement parser from East Money"""

    async def parse_income_statement(
        self,
        code: str,
        report_date: str
    ) -> Optional[Dict[str, float]]:
        """
        Parse income statement

        Args:
            code: Stock code
            report_date: Report date (YYYY-MM-DD)

        Returns:
            Dict with financial metrics
        """
        url = f"http://data.eastmoney.com/bbsj/{code}.html"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    html = await response.text()

            # Parse the income statement table
            df = self._parse_financial_table(html, "利润表")

            if df is None or df.empty:
                return None

            # Extract key metrics
            latest = df.iloc[-1]

            return {
                "revenue": float(latest.get("营业收入", 0)),
                "profit": float(latest.get("净利润", 0)),
                "roe": float(latest.get("净资产收益率", 0)) / 100,
                "gross_margin": float(latest.get("销售毛利率", 0)) / 100,
                "net_margin": float(latest.get("销售净利率", 0)) / 100,
            }

        except Exception as e:
            logger.error(f"Failed to parse income statement for {code}: {e}")
            return None

    def _parse_financial_table(self, html: str, table_name: str) -> Optional[pd.DataFrame]:
        """Parse financial table from HTML"""
        soup = BeautifulSoup(html, 'lxml')

        # Find the table by name
        tables = soup.find_all('table')
        for table in tables:
            if table_name in str(table):
                df = pd.read_html(str(table))[0]
                return df

        return None
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_statement_parser.py::test_parse_income_statement -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_statement_parser.py core/financial/statement_parser.py
git commit -m "feat: add financial statement parser"
```

---

### Task 1.5: Implement Data Quality Monitor

**Files:**
- Create: `backend/app/services/data_quality_service.py`
- Create: `backend/app/api/data_quality.py`
- Test: `tests/test_data_quality_service.py`

**Step 1: Write the failing test**

```python
# tests/test_data_quality_service.py
import pytest
from backend.app.services.data_quality_service import DataQualityService

@pytest.mark.asyncio
async def test_calculate_overview():
    """Test calculating data quality overview"""
    service = DataQualityService()

    result = await service.calculate_overview()

    assert "total_stocks" in result
    assert "completeness_rate" in result
    assert "status" in result
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_data_quality_service.py::test_calculate_overview -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# backend/app/services/data_quality_service.py
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataQualityService:
    """Data quality monitoring service"""

    def __init__(self, db=None):
        self.db = db

    async def calculate_overview(self) -> Dict[str, any]:
        """Calculate overall data quality overview"""
        # This would query the database for actual stats
        return {
            "total_stocks": 5329,
            "completeness_rate": 95.2,
            "last_update": datetime.now().isoformat(),
            "issue_count": 52,
            "status": "healthy"
        }

    async def check_stock_completeness(
        self,
        code: str,
        data_types: List[str] = None
    ) -> Dict[str, any]:
        """Check data completeness for a single stock"""
        if data_types is None:
            data_types = ["daily", "minute", "indicator", "financial", "news"]

        completeness = {}
        for data_type in data_types:
            completeness[data_type] = await self._check_type_completeness(code, data_type)

        return {
            "code": code,
            "completeness": completeness,
            "overall_rate": sum(c["rate"] for c in completeness.values()) / len(completeness)
        }

    async def _check_type_completeness(self, code: str, data_type: str) -> Dict:
        """Check completeness for a specific data type"""
        # Mock implementation
        return {
            "rate": 98.5,
            "total": 4365,
            "missing": 65
        }

    async def repair_stock_data(
        self,
        code: str,
        data_types: List[str],
        force_refresh: bool = False
    ) -> Dict:
        """Repair missing data for a stock"""
        repaired = {}
        failed = {}

        for data_type in data_types:
            try:
                # Trigger data fetch for this type
                count = await self._fetch_and_store(code, data_type)
                repaired[data_type] = count
            except Exception as e:
                failed[data_type] = str(e)

        return {
            "success": len(failed) == 0,
            "repaired": repaired,
            "failed": failed
        }

    async def _fetch_and_store(self, code: str, data_type: str) -> int:
        """Fetch and store data for a type"""
        # This would call the appropriate data provider
        return 100  # Mock
```

**Step 4: Create API endpoint**

```python
# backend/app/api/data_quality.py
from fastapi import APIRouter, HTTPException
from backend.app.services.data_quality_service import DataQualityService

router = APIRouter(prefix="/api/data-quality", tags=["Data Quality"])
service = DataQualityService()

@router.get("/overview")
async def get_data_overview():
    """Get overall data quality overview"""
    return await service.calculate_overview()

@router.get("/stock/{code}/detail")
async def get_stock_data_detail(code: str):
    """Get detailed data quality for a stock"""
    return await service.check_stock_completeness(code)

@router.post("/stock/{code}/repair")
async def repair_stock_data(code: str, data_types: List[str] = None):
    """Repair data for a stock"""
    if data_types is None:
        data_types = ["daily", "minute", "indicator", "financial", "news"]
    return await service.repair_stock_data(code, data_types)
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_data_quality_service.py::test_calculate_overview -v
```
Expected: `PASSED`

**Step 6: Commit**

```bash
git add tests/test_data_quality_service.py backend/app/services/data_quality_service.py backend/app/api/data_quality.py
git commit -m "feat: add data quality monitoring service"
```

---

## Phase 2: Agent Layer (3 weeks)

### Task 2.1: Create Agent Base Class and Result Model

**Files:**
- Create: `core/agents/base.py`
- Test: `tests/test_agent_base.py`

**Step 1: Write the failing test**

```python
# tests/test_agent_base.py
import pytest
from core.agents.base import Agent, AgentResult, AgentContext

def test_agent_result_creation():
    """Test creating an agent result"""
    result = AgentResult(
        success=True,
        data={"stocks": ["000001", "000002"]},
        reasoning="筛选出2只股票",
        confidence=0.9
    )

    assert result.success is True
    assert result.data["stocks"] == ["000001", "000002"]
    assert result.confidence == 0.9

def test_agent_context():
    """Test agent context"""
    context = AgentContext(
        user_id="test_user",
        message="帮我找AI股票",
        current_time="2026-02-17 10:00:00"
    )

    assert context.user_id == "test_user"
    assert context.message == "帮我找AI股票"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_agent_base.py::test_agent_result_creation -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/agents/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentContext:
    """Context for agent execution"""
    user_id: str
    message: str
    current_time: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentResult:
    """Result from agent execution"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class Agent(ABC):
    """Base class for all agents"""

    def __init__(self, name: str, llm=None):
        self.name = name
        self.llm = llm

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's task"""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get agent description"""
        pass

    def get_required_tools(self) -> List[str]:
        """Get list of required tools"""
        return []
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_agent_base.py::test_agent_result_creation -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_agent_base.py core/agents/base.py
git commit -m "feat: add agent base class and result model"
```

---

### Task 2.2: Implement Screener Agent

**Files:**
- Create: `core/agents/screener_agent.py`
- Test: `tests/test_screener_agent.py`

**Step 1: Write the failing test**

```python
# tests/test_screener_agent.py
import pytest
from core.agents.screener_agent import ScreenerAgent
from core.agents.base import AgentContext

@pytest.mark.asyncio
async def test_screener_by_sector():
    """Test screening stocks by sector"""
    agent = ScreenerAgent()
    context = AgentContext(
        user_id="test",
        message="帮我找AI板块的股票",
        metadata={"sector": "人工智能"}
    )

    result = await agent.execute(context)

    assert result.success is True
    assert "stocks" in result.data
    assert len(result.data["stocks"]) > 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_screener_agent.py::test_screener_by_sector -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/agents/screener_agent.py
import logging
from typing import Dict, List
from core.agents.base import Agent, AgentResult, AgentContext

logger = logging.getLogger(__name__)

class ScreenerAgent(Agent):
    """Stock screening agent"""

    def __init__(self, llm=None, db=None):
        super().__init__("ScreenerAgent", llm)
        self.db = db

    def get_description(self) -> str:
        return "筛选符合条件的股票"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute stock screening"""
        try:
            # Parse screening criteria from context
            criteria = self._parse_criteria(context)

            # Query database for matching stocks
            stocks = await self._screen_stocks(criteria)

            return AgentResult(
                success=True,
                data={
                    "stocks": stocks,
                    "criteria": criteria,
                    "total_count": len(stocks)
                },
                reasoning=f"根据条件 {criteria} 筛选出 {len(stocks)} 只股票",
                confidence=0.9
            )

        except Exception as e:
            logger.error(f"ScreenerAgent error: {e}")
            return AgentResult(
                success=False,
                reasoning=f"筛选失败: {str(e)}",
                confidence=0.0
            )

    def _parse_criteria(self, context: AgentContext) -> Dict:
        """Parse screening criteria from message"""
        criteria = {}

        message = context.message.lower()

        # Check for sector mentions
        sectors = {
            "ai": "人工智能", "人工智能": "人工智能",
            "半导体": "半导体", "芯片": "半导体",
            "医药": "医药", "医疗": "医药"
        }
        for keyword, sector in sectors.items():
            if keyword in message:
                criteria["sector"] = sector
                break

        # Check for ROE requirement
        if "roe" in message:
            import re
            roe_match = re.search(r'roe\s*[><=]+\s*(\d+)', message)
            if roe_match:
                criteria["roe_min"] = float(roe_match.group(1))

        # Check for market cap requirement
        if "市值" in message or "亿" in message:
            import re
            cap_match = re.search(r'(\d+)\s*亿', message)
            if cap_match:
                criteria["market_cap_min"] = float(cap_match.group(1))

        return criteria

    async def _screen_stocks(self, criteria: Dict) -> List[Dict]:
        """Screen stocks based on criteria"""
        # This would query the actual database
        # For now, return mock data
        mock_stocks = [
            {"code": "002230", "name": "科大讯飞", "sector": "人工智能", "roe": 18.5},
            {"code": "300033", "name": "同花顺", "sector": "人工智能", "roe": 15.2},
        ]

        filtered = []
        for stock in mock_stocks:
            match = True

            if "sector" in criteria and stock["sector"] != criteria["sector"]:
                match = False

            if "roe_min" in criteria and stock.get("roe", 0) < criteria["roe_min"]:
                match = False

            if match:
                filtered.append(stock)

        return filtered
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_screener_agent.py::test_screener_by_sector -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_screener_agent.py core/agents/screener_agent.py
git commit -m "feat: add ScreenerAgent for stock screening"
```

---

### Task 2.3: Implement Analyzer Agent

**Files:**
- Create: `core/agents/analyzer_agent.py`
- Test: `tests/test_analyzer_agent.py`

**Step 1: Write the failing test**

```python
# tests/test_analyzer_agent.py
import pytest
from core.agents.analyzer_agent import AnalyzerAgent
from core.agents.base import AgentContext

@pytest.mark.asyncio
async def test_analyze_single_stock():
    """Test analyzing a single stock"""
    agent = AnalyzerAgent()
    context = AgentContext(
        user_id="test",
        message="分析科大讯飞",
        metadata={"stock_code": "002230"}
    )

    result = await agent.execute(context)

    assert result.success is True
    assert "financial_score" in result.data
    assert "sentiment_score" in result.data
    assert "valuation_score" in result.data
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_analyzer_agent.py::test_analyze_single_stock -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/agents/analyzer_agent.py
import logging
from typing import Dict, List
from core.agents.base import Agent, AgentResult, AgentContext

logger = logging.getLogger(__name__)

class AnalyzerAgent(Agent):
    """Deep analysis agent for stocks"""

    def __init__(self, llm=None, db=None, financial_service=None, news_service=None):
        super().__init__("AnalyzerAgent", llm)
        self.db = db
        self.financial_service = financial_service
        self.news_service = news_service

    def get_description(self) -> str:
        return "对股票进行深度分析（财务、舆情、估值）"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute stock analysis"""
        try:
            stock_code = context.metadata.get("stock_code")

            if not stock_code:
                # Extract stock code from message
                stock_code = self._extract_stock_code(context.message)

            if not stock_code:
                return AgentResult(
                    success=False,
                    reasoning="无法识别股票代码",
                    confidence=0.0
                )

            # Run parallel analysis
            financial_score = await self._analyze_financial(stock_code)
            sentiment_score = await self._analyze_sentiment(stock_code)
            valuation_score = await self._analyze_valuation(stock_code)

            overall_score = (financial_score + sentiment_score + valuation_score) / 3

            return AgentResult(
                success=True,
                data={
                    "stock_code": stock_code,
                    "financial_score": financial_score,
                    "sentiment_score": sentiment_score,
                    "valuation_score": valuation_score,
                    "overall_score": overall_score,
                    "recommendation": self._get_recommendation(overall_score)
                },
                reasoning=f"财务{financial_score:.1f}分，舆情{sentiment_score:.1f}分，估值{valuation_score:.1f}分",
                confidence=0.85
            )

        except Exception as e:
            logger.error(f"AnalyzerAgent error: {e}")
            return AgentResult(
                success=False,
                reasoning=f"分析失败: {str(e)}",
                confidence=0.0
            )

    def _extract_stock_code(self, message: str) -> str:
        """Extract stock code from message"""
        import re
        # Match 6-digit stock code
        match = re.search(r'\d{6}', message)
        return match.group(0) if match else None

    async def _analyze_financial(self, code: str) -> float:
        """Analyze financial statements"""
        # This would call the financial service
        # Mock implementation
        return 85.0

    async def _analyze_sentiment(self, code: str) -> float:
        """Analyze news sentiment"""
        # This would call the news service
        # Mock implementation
        return 78.0

    async def _analyze_valuation(self, code: str) -> float:
        """Analyze valuation"""
        # This would calculate valuation metrics
        # Mock implementation
        return 72.0

    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on score"""
        if score >= 80:
            return "强烈推荐"
        elif score >= 70:
            return "推荐"
        elif score >= 60:
            return "中性"
        else:
            return "不推荐"
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_analyzer_agent.py::test_analyze_single_stock -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_analyzer_agent.py core/agents/analyzer_agent.py
git commit -m "feat: add AnalyzerAgent for deep stock analysis"
```

---

### Task 2.4: Implement Signal Agent

**Files:**
- Create: `core/agents/signal_agent.py`
- Test: `tests/test_signal_agent.py`

**Step 1: Write the failing test**

```python
# tests/test_signal_agent.py
import pytest
from core.agents.signal_agent import SignalAgent
from core.agents.base import AgentContext

@pytest.mark.asyncio
async def test_generate_buy_signal():
    """Test generating a buy signal"""
    agent = SignalAgent()
    context = AgentContext(
        user_id="test",
        message="科大讯飞可以买吗？",
        metadata={
            "stock_code": "002230",
            "analysis": {"overall_score": 82}
        }
    )

    result = await agent.execute(context)

    assert result.success is True
    assert "action" in result.data
    assert "target_price" in result.data
    assert "stop_loss" in result.data
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_signal_agent.py::test_generate_buy_signal -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/agents/signal_agent.py
import logging
from typing import Dict
from core.agents.base import Agent, AgentResult, AgentContext

logger = logging.getLogger(__name__)

class SignalAgent(Agent):
    """Trading signal generation agent"""

    def __init__(self, llm=None, db=None):
        super().__init__("SignalAgent", llm)
        self.db = db

    def get_description(self) -> str:
        return "生成交易信号（买入/卖出/观望）"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute signal generation"""
        try:
            stock_code = context.metadata.get("stock_code")
            analysis = context.metadata.get("analysis", {})

            if not stock_code:
                return AgentResult(
                    success=False,
                    reasoning="缺少股票代码",
                    confidence=0.0
                )

            # Get current price
            current_price = await self._get_current_price(stock_code)

            # Generate signal based on analysis
            signal = self._generate_signal(analysis, current_price)

            return AgentResult(
                success=True,
                data={
                    "stock_code": stock_code,
                    "action": signal["action"],
                    "current_price": current_price,
                    "target_price": signal.get("target_price"),
                    "stop_loss": signal.get("stop_loss"),
                    "position_size": signal.get("position_size", 0.15),
                    "reasons": signal.get("reasons", [])
                },
                reasoning=f"基于分析评分{analysis.get('overall_score', 0)}，建议{signal['action']}",
                confidence=signal.get("confidence", 0.7)
            )

        except Exception as e:
            logger.error(f"SignalAgent error: {e}")
            return AgentResult(
                success=False,
                reasoning=f"信号生成失败: {str(e)}",
                confidence=0.0
            )

    async def _get_current_price(self, code: str) -> float:
        """Get current stock price"""
        # This would fetch real-time price
        # Mock implementation
        return 48.50

    def _generate_signal(self, analysis: Dict, price: float) -> Dict:
        """Generate trading signal"""
        score = analysis.get("overall_score", 50)

        if score >= 75:
            return {
                "action": "buy",
                "target_price": round(price * 1.13, 2),  # +13%
                "stop_loss": round(price * 0.91, 2),   # -9%
                "position_size": 0.15,
                "confidence": min(0.95, 0.5 + score / 200),
                "reasons": ["财务优秀", "技术面健康", "舆情积极"]
            }
        elif score >= 60:
            return {
                "action": "hold",
                "confidence": 0.6,
                "reasons": ["综合评分中等，建议观望"]
            }
        else:
            return {
                "action": "sell",
                "confidence": 0.7,
                "reasons": ["基本面不佳", "技术面转弱"]
            }
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_signal_agent.py::test_generate_buy_signal -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_signal_agent.py core/agents/signal_agent.py
git commit -m "feat: add SignalAgent for trading signal generation"
```

---

### Task 2.5: Implement Validator Agent

**Files:**
- Create: `core/agents/validator_agent.py`
- Test: `tests/test_validator_agent.py`

**Step 1: Write the failing test**

```python
# tests/test_validator_agent.py
import pytest
from core.agents.validator_agent import ValidatorAgent
from core.agents.base import AgentContext

@pytest.mark.asyncio
async def test_validate_signal():
    """Test validating a trading signal"""
    agent = ValidatorAgent()
    context = AgentContext(
        user_id="test",
        message="验证这个信号",
        metadata={
            "signal": {
                "action": "buy",
                "stock_code": "002230",
                "current_price": 48.50,
                "target_price": 55.00,
                "stop_loss": 44.00
            }
        }
    )

    result = await agent.execute(context)

    assert result.success is True
    assert "validated" in result.data
    assert "adjustments" in result.data
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_validator_agent.py::test_validate_signal -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/agents/validator_agent.py
import logging
from datetime import datetime, timedelta
from core.agents.base import Agent, AgentResult, AgentContext

logger = logging.getLogger(__name__)

class ValidatorAgent(Agent):
    """Signal validation agent"""

    def __init__(self, llm=None, db=None):
        super().__init__("ValidatorAgent", llm)
        self.db = db

    def get_description(self) -> str:
        return "验证交易信号的合理性"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute signal validation"""
        try:
            signal = context.metadata.get("signal", {})

            # Run validation checks
            checks = {
                "data_freshness": await self._check_data_freshness(signal),
                "logic_consistency": self._check_logic_consistency(signal),
                "risk_boundary": self._check_risk_boundary(signal),
                "market_environment": await self._check_market_environment(signal)
            }

            # Determine if signal passes validation
            all_passed = all(check["passed"] for check in checks.values())

            # Generate adjustments if needed
            adjustments = []
            if not checks["risk_boundary"]["passed"]:
                adjustments.append({
                    "field": "position_size",
                    "suggestion": "降低至15%",
                    "reason": "风险偏高"
                })

            return AgentResult(
                success=True,
                data={
                    "validated": all_passed,
                    "checks": checks,
                    "adjustments": adjustments,
                    "final_recommendation": "通过" if all_passed else "需要调整"
                },
                reasoning=self._generate_reasoning(checks, adjustments),
                confidence=0.9 if all_passed else 0.7
            )

        except Exception as e:
            logger.error(f"ValidatorAgent error: {e}")
            return AgentResult(
                success=False,
                reasoning=f"验证失败: {str(e)}",
                confidence=0.0
            )

    async def _check_data_freshness(self, signal: Dict) -> Dict:
        """Check if data is fresh"""
        # Mock - would check actual data timestamp
        return {"passed": True, "message": "数据为1分钟前，时效性良好"}

    def _check_logic_consistency(self, signal: Dict) -> Dict:
        """Check logic consistency"""
        action = signal.get("action")
        current_price = signal.get("current_price", 0)
        target_price = signal.get("target_price", 0)
        stop_loss = signal.get("stop_loss", 0)

        if action == "buy":
            if target_price <= current_price:
                return {"passed": False, "message": "目标价应高于当前价"}
            if stop_loss >= current_price:
                return {"passed": False, "message": "止损价应低于当前价"}

        return {"passed": True, "message": "逻辑自洽"}

    def _check_risk_boundary(self, signal: Dict) -> Dict:
        """Check risk boundaries"""
        position_size = signal.get("position_size", 0)

        if position_size > 0.20:
            return {"passed": False, "message": "仓位超过20%，风险偏高"}

        return {"passed": True, "message": "风险边界合理"}

    async def _check_market_environment(self, signal: Dict) -> Dict:
        """Check market environment"""
        # Mock - would check actual market conditions
        return {"passed": True, "message": "AI板块热度上升"}

    def _generate_reasoning(self, checks: Dict, adjustments: List) -> str:
        """Generate validation reasoning"""
        passed = sum(1 for c in checks.values() if c["passed"])
        total = len(checks)

        reasoning = f"验证通过 {passed}/{total} 项检查"
        if adjustments:
            reasoning += f"，建议调整: {', '.join(a['suggestion'] for a in adjustments)}"

        return reasoning
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_validator_agent.py::test_validate_signal -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_validator_agent.py core/agents/validator_agent.py
git commit -m "feat: add ValidatorAgent for signal validation"
```

---

### Task 2.6: Implement Risk Agent

**Files:**
- Create: `core/agents/risk_agent.py`
- Test: `tests/test_risk_agent.py`

**Step 1: Write the failing test**

```python
# tests/test_risk_agent.py
import pytest
from core.agents.risk_agent import RiskAgent
from core.agents.base import AgentContext

@pytest.mark.asyncio
async def test_assess_portfolio_risk():
    """Test assessing portfolio risk"""
    agent = RiskAgent()
    context = AgentContext(
        user_id="test",
        message="评估我的持仓风险",
        metadata={
            "portfolio": [
                {"code": "002230", "weight": 0.20},
                {"code": "300033", "weight": 0.15}
            ]
        }
    )

    result = await agent.execute(context)

    assert result.success is True
    assert "portfolio_risk" in result.data
    assert "suggestions" in result.data
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_risk_agent.py::test_assess_portfolio_risk -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/agents/risk_agent.py
import logging
import numpy as np
from core.agents.base import Agent, AgentResult, AgentContext

logger = logging.getLogger(__name__)

class RiskAgent(Agent):
    """Risk management agent"""

    def __init__(self, llm=None, db=None):
        super().__init__("RiskAgent", llm)
        self.db = db

    def get_description(self) -> str:
        return "评估投资组合风险并优化仓位"

    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute risk assessment"""
        try:
            portfolio = context.metadata.get("portfolio", [])

            if not portfolio:
                return AgentResult(
                    success=False,
                    reasoning="没有持仓信息",
                    confidence=0.0
                )

            # Calculate portfolio risk metrics
            total_weight = sum(p.get("weight", 0) for p in portfolio)

            risk_metrics = {
                "total_weight": total_weight,
                "concentration": max(p.get("weight", 0) for p in portfolio),
                "diversification": len(portfolio)
            }

            # Generate suggestions
            suggestions = []
            if total_weight > 1.0:
                suggestions.append({
                    "type": "warning",
                    "message": f"总仓位{total_weight:.1%}超过100%，建议降低"
                })

            if risk_metrics["concentration"] > 0.25:
                suggestions.append({
                    "type": "warning",
                    "message": f"单一持仓{risk_metrics['concentration']:.1%}过高，建议分散"
                })

            if risk_metrics["diversification"] < 3:
                suggestions.append({
                    "type": "info",
                    "message": "持仓数量偏少，建议适当分散"
                })

            return AgentResult(
                success=True,
                data={
                    "portfolio_risk": "low" if total_weight < 0.8 else "medium" if total_weight < 1.0 else "high",
                    "risk_metrics": risk_metrics,
                    "suggestions": suggestions
                },
                reasoning=f"当前持仓风险等级: {risk_metrics.get('portfolio_risk', 'unknown')}",
                confidence=0.85
            )

        except Exception as e:
            logger.error(f"RiskAgent error: {e}")
            return AgentResult(
                success=False,
                reasoning=f"风险评估失败: {str(e)}",
                confidence=0.0
            )
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_risk_agent.py::test_assess_portfolio_risk -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_risk_agent.py core/agents/risk_agent.py
git commit -m "feat: add RiskAgent for portfolio risk assessment"
```

---

### Task 2.7: Implement Agent Orchestrator

**Files:**
- Create: `core/agents/orchestrator.py`
- Test: `tests/test_orchestrator.py`

**Step 1: Write the failing test**

```python
# tests/test_orchestrator.py
import pytest
from core.orchestrator.orchestrator import AgentOrchestrator
from core.agents.base import AgentContext

@pytest.mark.asyncio
async def test_full_conversation_flow():
    """Test full conversation flow with multiple agents"""
    orchestrator = AgentOrchestrator()
    context = AgentContext(
        user_id="test",
        message="帮我找AI板块ROE>15%的股票"
    )

    result = await orchestrator.process(context)

    assert result is not None
    assert "final_answer" in result
    assert "agent_results" in result
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_orchestrator.py::test_full_conversation_flow -v
```
Expected: `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# core/agents/orchestrator.py
import logging
from typing import Dict, List
from core.agents.base import Agent, AgentContext, AgentResult
from core.agents.screener_agent import ScreenerAgent
from core.agents.analyzer_agent import AnalyzerAgent
from core.agents.signal_agent import SignalAgent
from core.agents.validator_agent import ValidatorAgent
from core.agents.risk_agent import RiskAgent

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Coordinates multiple agents for complex tasks"""

    def __init__(self, llm=None):
        self.llm = llm
        self.agents = {
            "screener": ScreenerAgent(llm),
            "analyzer": AnalyzerAgent(llm),
            "signal": SignalAgent(llm),
            "validator": ValidatorAgent(llm),
            "risk": RiskAgent(llm)
        }

    async def process(self, context: AgentContext) -> Dict:
        """Process user request through agent pipeline"""
        try:
            # Step 1: Intent classification
            intent = await self._classify_intent(context)

            # Step 2: Route to appropriate agents
            agent_results = {}

            if intent == "screen":
                # Screening flow
                agent_results["screener"] = await self.agents["screener"].execute(context)

                # If stocks found, analyze them
                if agent_results["screener"].success:
                    stocks = agent_results["screener"].data.get("stocks", [])[:3]  # Top 3

                    for stock in stocks:
                        context.metadata["stock_code"] = stock["code"]
                        agent_results[f"analyzer_{stock['code']}"] = await self.agents["analyzer"].execute(context)

            elif intent == "analyze":
                # Analysis flow
                agent_results["analyzer"] = await self.agents["analyzer"].execute(context)

                # If analysis complete, generate signal
                if agent_results["analyzer"].success:
                    context.metadata["analysis"] = agent_results["analyzer"].data
                    agent_results["signal"] = await self.agents["signal"].execute(context)

                    # Validate signal
                    if agent_results["signal"].success:
                        context.metadata["signal"] = agent_results["signal"].data
                        agent_results["validator"] = await self.agents["validator"].execute(context)

            # Step 3: Generate final answer
            final_answer = self._generate_final_answer(context, agent_results)

            return {
                "final_answer": final_answer,
                "agent_results": agent_results,
                "intent": intent
            }

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return {
                "final_answer": f"处理失败: {str(e)}",
                "agent_results": {},
                "intent": "error"
            }

    async def _classify_intent(self, context: AgentContext) -> str:
        """Classify user intent"""
        message = context.message.lower()

        if any(word in message for word in ["找", "筛选", "什么股票"]):
            return "screen"
        elif any(word in message for word in ["分析", "怎么样", "如何"]):
            return "analyze"
        elif any(word in message for word in ["买", "卖", "信号"]):
            return "signal"
        else:
            return "general"

    def _generate_final_answer(self, context: AgentContext, agent_results: Dict) -> str:
        """Generate final answer for user"""
        intent = self._classify_intent(context)

        if intent == "screen":
            screener_result = agent_results.get("screener")
            if screener_result and screener_result.success:
                stocks = screener_result.data.get("stocks", [])
                if stocks:
                    stock_list = ", ".join([f"{s['name']}({s['code']})" for s in stocks[:5]])
                    return f"为您筛选出 {len(stocks)} 只股票，包括: {stock_list}"

        elif intent == "analyze":
            validator_result = agent_results.get("validator")
            if validator_result and validator_result.success:
                return validator_result.data.get("final_recommendation", "分析完成")

        return "处理完成"
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_orchestrator.py::test_full_conversation_flow -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_orchestrator.py core/agents/orchestrator.py
git commit -m "feat: add AgentOrchestrator for multi-agent coordination"
```

---

## Phase 3: API Layer (2 weeks)

### Task 3.1: Implement Chat API

**Files:**
- Create: `backend/app/api/chat.py`
- Test: `tests/test_chat_api.py`

**Step 1: Write the failing test**

```python
# tests/test_chat_api.py
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_chat_endpoint():
    """Test chat endpoint"""
    response = client.post(
        "/api/chat",
        json={
            "message": "帮我找AI股票",
            "user_id": "test_user"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "agent_results" in data
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_chat_api.py::test_chat_endpoint -v
```
Expected: `ModuleNotFoundError` or route not found

**Step 3: Write minimal implementation**

```python
# backend/app/api/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    agent_results: Dict[str, Any]
    session_id: str

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process chat message through agent pipeline"""
    try:
        from core.orchestrator.orchestrator import AgentOrchestrator
        from core.agents.base import AgentContext
        import uuid

        # Create orchestrator
        orchestrator = AgentOrchestrator()

        # Create context
        context = AgentContext(
            user_id=request.user_id,
            message=request.message,
            metadata=request.metadata or {}
        )

        # Process through agents
        result = await orchestrator.process(context)

        return ChatResponse(
            response=result["final_answer"],
            agent_results=result["agent_results"],
            session_id=request.session_id or str(uuid.uuid4())
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 4: Register router in main app**

```python
# backend/app/main.py
from fastapi import FastAPI
from backend.app.api.chat import router as chat_router
from backend.app.api.data_quality import router as data_quality_router

app = FastAPI(title="AI Investment Assistant API")

app.include_router(chat_router)
app.include_router(data_quality_router)

@app.get("/")
async def root():
    return {"message": "AI Investment Assistant API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/test_chat_api.py::test_chat_endpoint -v
```
Expected: `PASSED`

**Step 6: Commit**

```bash
git add tests/test_chat_api.py backend/app/api/chat.py backend/app/main.py
git commit -m "feat: add chat API endpoint"
```

---

### Task 3.2: Implement WebSocket for Streaming Chat

**Files:**
- Create: `backend/app/api/chat_stream.py`
- Test: `tests/test_chat_stream.py`

**Step 1: Write the failing test**

```python
# tests/test_chat_stream.py
import pytest
import asyncio
from websockets.client import connect

@pytest.mark.asyncio
async def test_websocket_chat():
    """Test WebSocket chat endpoint"""
    uri = "ws://localhost:8888/api/chat/stream"

    async with connect(uri) as websocket:
        # Send message
        await websocket.send('{"message": "帮我找AI股票", "user_id": "test"}')

        # Receive responses
        responses = []
        while True:
            response = await websocket.recv()
            if response == "[DONE]":
                break
            responses.append(response)

        assert len(responses) > 0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_chat_stream.py::test_websocket_chat -v
```
Expected: Connection refused

**Step 3: Write minimal implementation**

```python
# backend/app/api/chat_stream.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: str, message: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

manager = ConnectionManager()

@router.websocket("/stream")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for streaming chat"""
    await manager.connect(websocket, "temp")

    try:
        # Receive initial message
        data = await websocket.receive_text()
        request = json.loads(data)

        # Process through agents (streamed)
        from core.orchestrator.orchestrator import AgentOrchestrator
        from core.agents.base import AgentContext

        orchestrator = AgentOrchestrator()
        context = AgentContext(
            user_id=request.get("user_id", "unknown"),
            message=request.get("message", "")
        )

        # Stream agent responses
        await websocket.send_text(json.dumps({"type": "status", "content": "正在分析..."}))

        result = await orchestrator.process(context)

        # Send final answer
        await websocket.send_text(json.dumps({
            "type": "final",
            "content": result["final_answer"],
            "agent_results": result["agent_results"]
        }))

        await websocket.send_text("[DONE]")

    except WebSocketDisconnect:
        manager.disconnect("temp")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
```

**Step 4: Run test to verify it passes**

```bash
# Start server first
uvicorn backend.app.main:app --host 0.0.0.0 --port 8888 &

# Then run test
pytest tests/test_chat_stream.py::test_websocket_chat -v
```
Expected: `PASSED`

**Step 5: Commit**

```bash
git add tests/test_chat_stream.py backend/app/api/chat_stream.py
git commit -m "feat: add WebSocket streaming for chat"
```

---

## Phase 4: Frontend Layer (3 weeks)

### Task 4.1: Create Chat Page Component

**Files:**
- Create: `frontend/src/pages/Chat.tsx`
- Create: `frontend/src/components/MessageList.tsx`
- Create: `frontend/src/components/MessageInput.tsx`

**Step 1: Create Chat page structure**

```typescript
// frontend/src/pages/Chat.tsx
import React, { useState } from 'react';
import { MessageList } from '../components/MessageList';
import { MessageInput } from '../components/MessageInput';
import { sendChatMessage, useChatStream } from '../hooks/useChat';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'signal' | 'analysis';
  metadata?: any;
}

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(content);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        type: 'text',
        metadata: response.agent_results
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900">
      <div className="w-1/2 flex flex-col border-r border-gray-700">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-xl font-bold text-white">AI 投研助手</h1>
        </div>
        <MessageList messages={messages} isLoading={isLoading} />
        <MessageInput onSend={handleSendMessage} disabled={isLoading} />
      </div>
      <div className="w-1/2">
        {/* Dashboard panel */}
      </div>
    </div>
  );
};
```

**Step 2: Create MessageList component**

```typescript
// frontend/src/components/MessageList.tsx
import React from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'signal' | 'analysis';
  metadata?: any;
}

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[70%] rounded-lg p-3 ${
              message.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-100'
            }`}
          >
            {message.type === 'signal' ? (
              <SignalCard content={message.content} metadata={message.metadata} />
            ) : (
              <p className="whitespace-pre-wrap">{message.content}</p>
            )}
          </div>
        </div>
      ))}
      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-gray-800 rounded-lg p-3">
            <div className="flex space-x-2">
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100" />
              <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const SignalCard: React.FC<{ content: string; metadata?: any }> = ({ content, metadata }) => (
  <div className="space-y-2">
    <p className="font-semibold">{content}</p>
    {metadata?.signal && (
      <div className="mt-2 p-2 bg-gray-700 rounded text-sm">
        <p>目标价: ¥{metadata.signal.target_price}</p>
        <p>止损价: ¥{metadata.signal.stop_loss}</p>
        <p>仓位: {(metadata.signal.position_size * 100).toFixed(0)}%</p>
      </div>
    )}
  </div>
);
```

**Step 3: Create MessageInput component**

```typescript
// frontend/src/components/MessageInput.tsx
import React, { useState, FormEvent } from 'react';

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  };

  return (
    <div className="p-4 border-t border-gray-700">
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入问题，例如：帮我找AI板块ROE>15%的股票"
          disabled={disabled}
          className="flex-1 px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed"
        >
          发送
        </button>
      </form>
    </div>
  );
};
```

**Step 4: Create chat API hook**

```typescript
// frontend/src/hooks/useChat.ts
import { useState } from 'react';

interface ChatResponse {
  response: string;
  agent_results: any;
  session_id: string;
}

export const sendChatMessage = async (message: string): Promise<ChatResponse> => {
  const response = await fetch('http://localhost:8888/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      user_id: 'local_user'
    })
  });

  if (!response.ok) {
    throw new Error('Failed to send message');
  }

  return response.json();
};

export const useChatStream = () => {
  // WebSocket implementation would go here
  return { connect: () => {}, send: () => {}, disconnect: () => {} };
};
```

**Step 5: Commit**

```bash
git add frontend/src/pages/Chat.tsx frontend/src/components/MessageList.tsx frontend/src/components/MessageInput.tsx frontend/src/hooks/useChat.ts
git commit -m "feat: add Chat page with message components"
```

---

### Task 4.2: Create Data Monitor Page

**Files:**
- Create: `frontend/src/pages/DataMonitor.tsx`
- Create: `frontend/src/components/DataQualityOverview.tsx`

**Step 1: Create DataMonitor page**

```typescript
// frontend/src/pages/DataMonitor.tsx
import React, { useState, useEffect } from 'react';
import { DataQualityOverview } from '../components/DataQualityOverview';

interface DataOverview {
  total_stocks: number;
  completeness_rate: number;
  last_update: string;
  issue_count: number;
  status: string;
}

export const DataMonitor: React.FC = () => {
  const [overview, setOverview] = useState<DataOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverview();
  }, []);

  const fetchOverview = async () => {
    try {
      const response = await fetch('http://localhost:8888/api/data-quality/overview');
      const data = await response.json();
      setOverview(data);
    } catch (error) {
      console.error('Error fetching overview:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-900 min-h-screen">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">数据质量监控中心</h1>
      </div>

      {loading ? (
        <div className="text-gray-400">加载中...</div>
      ) : overview ? (
        <DataQualityOverview overview={overview} onRefresh={fetchOverview} />
      ) : (
        <div className="text-red-400">加载失败</div>
      )}
    </div>
  );
};
```

**Step 2: Create overview component**

```typescript
// frontend/src/components/DataQualityOverview.tsx
import React from 'react';

interface DataQualityOverviewProps {
  overview: {
    total_stocks: number;
    completeness_rate: number;
    last_update: string;
    issue_count: number;
    status: string;
  };
  onRefresh: () => void;
}

export const DataQualityOverview: React.FC<DataQualityOverviewProps> = ({
  overview,
  onRefresh
}) => {
  const statusColor = overview.status === 'healthy' ? 'text-green-400' : 'text-yellow-400';

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-white">整体数据概况</h2>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          刷新
        </button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="股票总数" value={overview.total_stocks.toLocaleString()} />
        <MetricCard label="数据完整率" value={`${overview.completeness_rate}%`} />
        <MetricCard label="问题数量" value={overview.issue_count} />
        <MetricCard label="状态" value={overview.status === 'healthy' ? '正常' : '警告'} className={statusColor} />
      </div>

      <div className="text-gray-400 text-sm">
        最后更新: {new Date(overview.last_update).toLocaleString('zh-CN')}
      </div>
    </div>
  );
};

const MetricCard: React.FC<{ label: string; value: string | number; className?: string }> = ({
  label,
  value,
  className = 'text-white'
}) => (
  <div className="bg-gray-800 rounded-lg p-4">
    <div className="text-gray-400 text-sm mb-1">{label}</div>
    <div className={`text-2xl font-bold ${className}`}>{value}</div>
  </div>
);
```

**Step 3: Commit**

```bash
git add frontend/src/pages/DataMonitor.tsx frontend/src/components/DataQualityOverview.tsx
git commit -m "feat: add Data Monitor page"
```

---

## Phase 5: Integration & Testing (2 weeks)

### Task 5.1: End-to-End Integration Test

**Files:**
- Create: `tests/integration/test_e2e_chat_flow.py`

**Step 1: Write the integration test**

```python
# tests/integration/test_e2e_chat_flow.py
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_full_chat_flow():
    """Test complete chat flow from user message to trading signal"""

    async with AsyncClient(base_url="http://localhost:8888") as client:
        # Step 1: User asks for stock screening
        response = await client.post(
            "/api/chat",
            json={
                "message": "帮我找AI板块ROE>15%的股票",
                "user_id": "test_user"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data
        assert "agent_results" in data
        assert "screener" in data["agent_results"]

        # Verify screening result
        screener_result = data["agent_results"]["screener"]
        assert screener_result["success"] is True
        assert "stocks" in screener_result["data"]
        assert len(screener_result["data"]["stocks"]) > 0

        # Step 2: Follow up with analysis request
        first_stock = screener_result["data"]["stocks"][0]
        response = await client.post(
            "/api/chat",
            json={
                "message": f"分析{first_stock['name']}({first_stock['code']})",
                "user_id": "test_user"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify analysis was performed
        assert "analyzer" in data["agent_results"] or "signal" in data["agent_results"]

        # If signal was generated, verify its structure
        if "signal" in data["agent_results"]:
            signal = data["agent_results"]["signal"]["data"]
            assert "action" in signal
            assert "current_price" in signal
            assert "target_price" in signal
            assert "stop_loss" in signal
```

**Step 2: Run the integration test**

```bash
# First ensure server is running
uvicorn backend.app.main:app --host 0.0.0.0 --port 8888 &

# Then run test
pytest tests/integration/test_e2e_chat_flow.py -v
```
Expected: `PASSED`

**Step 3: Commit**

```bash
git add tests/integration/test_e2e_chat_flow.py
git commit -m "test: add end-to-end integration test"
```

---

### Task 5.2: Performance Testing

**Files:**
- Create: `tests/performance/test_api_performance.py`

**Step 1: Write performance test**

```python
# tests/performance/test_api_performance.py
import pytest
import time
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_response_time():
    """Test that chat API responds within acceptable time"""

    async with AsyncClient(base_url="http://localhost:8888") as client:
        start_time = time.time()

        response = await client.post(
            "/api/chat",
            json={
                "message": "分析科大讯飞",
                "user_id": "test_user"
            },
            timeout=10.0
        )

        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < 5.0, f"Response time {elapsed_time:.2f}s exceeded 5s limit"

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling concurrent requests"""

    async def make_request(client):
        return await client.post(
            "/api/chat",
            json={
                "message": "帮我找一只股票",
                "user_id": "test_user"
            }
        )

    async with AsyncClient(base_url="http://localhost:8888") as client:
        start_time = time.time()

        # Send 10 concurrent requests
        tasks = [make_request(client) for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        elapsed_time = time.time() - start_time

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # Total time should be reasonable (parallel processing)
        assert elapsed_time < 15.0, f"Concurrent requests took {elapsed_time:.2f}s"
```

**Step 2: Run performance test**

```bash
pytest tests/performance/test_api_performance.py -v
```

**Step 3: Commit**

```bash
git add tests/performance/test_api_performance.py
git commit -m "test: add API performance tests"
```

---

## Phase 6: Deployment (1 week)

### Task 6.1: Create Deployment Configuration

**Files:**
- Create: `docker-compose.yml`
- Create: `Dockerfile.backend`
- Create: `Dockerfile.frontend`

**Step 1: Create Docker Compose configuration**

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: stock_assistant
      POSTGRES_USER: stock_user
      POSTGRES_PASSWORD: stock_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - DATABASE_URL=postgresql://stock_user:stock_pass@postgres:5432/stock_assistant
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TUSHARE_API_KEY=${TUSHARE_API_KEY}
    ports:
      - "8888:8888"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

**Step 2: Create backend Dockerfile**

```dockerfile
# Dockerfile.backend
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8888

# Run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8888"]
```

**Step 3: Create frontend Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build application
COPY . .
RUN npm run build

# Production image
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

**Step 4: Commit**

```bash
git add docker-compose.yml Dockerfile.backend frontend/Dockerfile
git commit -m "feat: add Docker deployment configuration"
```

---

### Task 6.2: Create Environment Configuration

**Files:**
- Create: `.env.example`
- Create: `config/deployment.py`

**Step 1: Create environment example**

```bash
# .env.example
# Database
DATABASE_URL=postgresql://stock_user:stock_pass@localhost:5432/stock_assistant
REDIS_URL=redis://localhost:6379

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
TUSHARE_API_KEY=your_tushare_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Server
HOST=0.0.0.0
PORT=8888
DEBUG=false

# Logging
LOG_LEVEL=INFO
```

**Step 2: Create deployment config**

```python
# config/deployment.py
import os
from typing import Optional

class DeploymentConfig:
    """Deployment configuration"""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost/stock_assistant")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    TUSHARE_API_KEY: Optional[str] = os.getenv("TUSHARE_API_KEY")
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8888"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        if not cls.OPENAI_API_KEY and not cls.DEEPSEEK_API_KEY:
            errors.append("OPENAI_API_KEY or DEEPSEEK_API_KEY is required")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        return True

config = DeploymentConfig()
```

**Step 3: Commit**

```bash
git add .env.example config/deployment.py
git commit -m "feat: add environment configuration"
```

---

## Summary

This implementation plan covers:

1. **Phase 0 (1 week)**: Infrastructure setup
2. **Phase 1 (2 weeks)**: Data layer with multi-source support
3. **Phase 2 (3 weeks)**: Agent layer with 5 specialized agents
4. **Phase 3 (2 weeks)**: API layer with chat and streaming
5. **Phase 4 (3 weeks)**: Frontend with chat and data monitor
6. **Phase 5 (2 weeks)**: Integration and testing
7. **Phase 6 (1 week)**: Deployment configuration

**Total estimated time: 14 weeks**

**Key Files Created:**
- 50+ new source files
- 50+ test files
- Configuration and deployment files

**Key Technologies:**
- Backend: FastAPI, LangGraph, PostgreSQL, Redis
- Frontend: React, TypeScript, Tailwind
- AI: OpenAI/DeepSeek APIs, ChromaDB
- Data: Tushare, Baostock, Sina Finance

**Next Steps:**
1. Review and approve this plan
2. Set up development environment
3. Begin Phase 0 implementation
