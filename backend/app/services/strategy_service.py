# -*- coding: utf-8 -*-
"""
策略服务层
"""
import json
import importlib
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
import sys

# 添加项目根目录到路径
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.models.strategy import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategyDetailResponse
)


class StrategyService:
    """策略服务"""

    def __init__(self):
        self.strategies_dir = root_dir / "core" / "strategies"
        self.metadata_file = root_dir / "data" / "strategies_metadata.json"
        self._ensure_metadata_file()

    def _ensure_metadata_file(self):
        """确保元数据文件存在"""
        if not self.metadata_file.exists():
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_metadata({})

    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_metadata(self, metadata: Dict[str, Any]):
        """保存元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _scan_existing_strategies(self) -> List[Dict[str, Any]]:
        """扫描现有策略文件"""
        strategies = []

        # 也扫描根目录的 strategies 文件夹 (AI生成的策略)
        root_strategies_dir = self.strategies_dir.parent.parent / "strategies"
        
        # 扫描 core/strategies 目录
        for file in self.strategies_dir.glob("*_strategy.py"):
            if file.name.startswith("__"):
                continue

            strategy_id = file.stem  # 去掉.py后缀

            # 尝试导入策略类
            try:
                module_name = f"core.strategies.{strategy_id}"
                module = importlib.import_module(module_name)

                # 查找Strategy子类
                strategy_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        hasattr(attr, '__bases__') and
                        'Strategy' in [b.__name__ for b in attr.__bases__]):
                        strategy_class = attr
                        break

                if strategy_class:
                    # 尝试实例化获取信息
                    try:
                        instance = strategy_class()
                        name = getattr(instance, 'name', strategy_id.replace('_', ' ').title())
                        description = getattr(instance, 'description', '')
                    except:
                        name = strategy_id.replace('_', ' ').title()
                        description = ''

                    strategies.append({
                        "id": strategy_id,
                        "name": name,
                        "description": description,
                        "file": str(file)
                    })
            except Exception as e:
                print(f"扫描策略 {file.name} 失败: {e}")
                continue

        # 扫描根目录 strategies 文件夹中的AI生成策略
        if root_strategies_dir.exists():
            for file in root_strategies_dir.glob("*.py"):
                if file.name.startswith("__"):
                    continue
                    
                strategy_id = file.stem
                name = strategy_id.replace("_", " ").title()
                description = "AI生成的策略"
                
                strategies.append({
                    "id": strategy_id,
                    "name": name,
                    "description": description,
                    "file": str(file)
                })

        return strategies


    def list_all(self) -> List[StrategyResponse]:
        """获取所有策略列表"""
        metadata = self._load_metadata()
        existing = self._scan_existing_strategies()

        strategies = []
        for item in existing:
            strategy_id = item["id"]

            # 合并元数据
            meta = metadata.get(strategy_id, {})

            strategies.append(StrategyResponse(
                id=strategy_id,
                name=item["name"],
                description=item.get("description", ""),
                params=meta.get("params", {}),
                created_at=meta.get("created_at", datetime.now().isoformat()),
                updated_at=meta.get("updated_at", datetime.now().isoformat()),
                performance_history=meta.get("performance_history", [])
            ))

        return strategies

    def get_by_id(self, strategy_id: str) -> Optional[StrategyDetailResponse]:
        """获取策略详情"""
        strategy_file = self.strategies_dir / f"{strategy_id}.py"

        if not strategy_file.exists():
            return None

        # 读取代码
        with open(strategy_file, 'r', encoding='utf-8') as f:
            code = f.read()

        # 加载元数据
        metadata = self._load_metadata()
        meta = metadata.get(strategy_id, {})

        # 获取基本信息
        strategies = self._scan_existing_strategies()
        basic_info = next((s for s in strategies if s["id"] == strategy_id), {})

        return StrategyDetailResponse(
            id=strategy_id,
            name=basic_info.get("name", strategy_id),
            description=basic_info.get("description", ""),
            params=meta.get("params", {}),
            created_at=meta.get("created_at", datetime.now().isoformat()),
            updated_at=meta.get("updated_at", datetime.now().isoformat()),
            performance_history=meta.get("performance_history", []),
            code=code
        )

    def create(self, strategy: StrategyCreate) -> StrategyResponse:
        """创建策略"""
        # 生成策略ID（基于名称）
        strategy_id = strategy.name.lower().replace(' ', '_').replace('-', '_')
        strategy_file = self.strategies_dir / f"{strategy_id}.py"

        # 检查是否已存在
        if strategy_file.exists():
            raise ValueError(f"策略 {strategy_id} 已存在")

        # 保存代码文件
        with open(strategy_file, 'w', encoding='utf-8') as f:
            f.write(strategy.code)

        # 保存元数据
        metadata = self._load_metadata()
        now = datetime.now().isoformat()
        metadata[strategy_id] = {
            "name": strategy.name,
            "description": strategy.description,
            "params": strategy.params,
            "created_at": now,
            "updated_at": now,
            "performance_history": []
        }
        self._save_metadata(metadata)

        return StrategyResponse(
            id=strategy_id,
            name=strategy.name,
            description=strategy.description,
            params=strategy.params,
            created_at=now,
            updated_at=now,
            performance_history=[]
        )

    def update(self, strategy_id: str, strategy: StrategyUpdate) -> Optional[StrategyResponse]:
        """更新策略"""
        strategy_file = self.strategies_dir / f"{strategy_id}.py"

        if not strategy_file.exists():
            raise ValueError(f"策略 {strategy_id} 不存在")

        # 加载元数据
        metadata = self._load_metadata()
        if strategy_id not in metadata:
            metadata[strategy_id] = {}

        # 更新代码
        if strategy.code is not None:
            with open(strategy_file, 'w', encoding='utf-8') as f:
                f.write(strategy.code)

        # 更新元数据
        if strategy.name is not None:
            metadata[strategy_id]["name"] = strategy.name
        if strategy.description is not None:
            metadata[strategy_id]["description"] = strategy.description
        if strategy.params is not None:
            metadata[strategy_id]["params"] = strategy.params

        metadata[strategy_id]["updated_at"] = datetime.now().isoformat()
        self._save_metadata(metadata)

        return self.get_by_id(strategy_id)

    def delete(self, strategy_id: str) -> bool:
        """删除策略"""
        strategy_file = self.strategies_dir / f"{strategy_id}.py"

        if not strategy_file.exists():
            return False

        # 删除文件
        strategy_file.unlink()

        # 删除元数据
        metadata = self._load_metadata()
        if strategy_id in metadata:
            del metadata[strategy_id]
            self._save_metadata(metadata)

        return True


# ===================== 新增AI生成功能 =====================

import os
import re
import ast
import hashlib
import logging
import anthropic
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 获取prompt模板
PROMPT_TEMPLATE_PATH = root_dir / "prompts" / "strategy_generation_prompt.md"
STRATEGIES_DIR = root_dir / "strategies"


def get_prompt_template() -> str:
    """读取prompt模板"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt template not found: {PROMPT_TEMPLATE_PATH}")
        raise RuntimeError(
            f"Prompt template file is missing at {PROMPT_TEMPLATE_PATH}. "
            "This indicates a deployment issue. Please ensure the prompts/ directory "
            "is included in the deployment."
        )
    except PermissionError:
        logger.error(f"Permission denied reading prompt template: {PROMPT_TEMPLATE_PATH}")
        raise RuntimeError(
            f"Cannot read prompt template at {PROMPT_TEMPLATE_PATH} due to permission error. "
            "Please check file permissions."
        )
    except UnicodeDecodeError as e:
        logger.error(f"Prompt template has invalid encoding: {e}")
        raise RuntimeError(
            f"Prompt template at {PROMPT_TEMPLATE_PATH} contains invalid UTF-8 encoding. "
            "Please verify the file is saved with UTF-8 encoding."
        )
    except OSError as e:
        logger.error(f"OS error reading prompt template: {e}")
        raise RuntimeError(
            f"Failed to read prompt template at {PROMPT_TEMPLATE_PATH}: {e}. "
            "This may indicate a disk or filesystem issue."
        )


def validate_python_syntax(code: str) -> tuple[bool, Optional[str]]:
    """验证Python语法"""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"语法错误 at line {e.lineno}: {e.msg}"


def extract_code_from_response(response: str) -> Optional[str]:
    """从LLM响应中提取代码"""
    # 尝试找到代码块
    code_block_match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1)
    # 尝试不带语言标识的代码块
    code_block_match = re.search(r'```\n(.*?)```', response, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1)
    # 如果没有代码块，返回整个响应
    return response.strip() if response.strip() else None


def generate_mock_backtest():
    """生成模拟回测结果"""
    import random
    return {
        'total_return': round(random.uniform(-20, 50), 2),
        'sharpe_ratio': round(random.uniform(-0.5, 2.5), 2),
        'max_drawdown': round(random.uniform(5, 40), 2),
        'win_rate': round(random.uniform(30, 70), 2),
        'trades_count': random.randint(10, 200),
        'holding_periods': [random.randint(1, 30) for _ in range(random.randint(10, 50))]
    }


async def generate_strategy(request):
    """
    AI生成交易策略
    
    Args:
        request: GenerateStrategyRequest
        
    Returns:
        GenerateStrategyResponse
    """
    # 导入模型
    from backend.app.models.strategy import GenerateStrategyResponse, BacktestResult
    
    # 获取API key
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return GenerateStrategyResponse(
            success=False,
            errors=["API密钥未配置"],
            message="请在.env中配置ANTHROPIC_AUTH_TOKEN"
        )
    
    try:
        # 构建prompt
        prompt_template = get_prompt_template()
        if not prompt_template:
            return GenerateStrategyResponse(
                success=False,
                errors=["Prompt模板不存在"],
                message=f"请确保 {PROMPT_TEMPLATE_PATH} 存在"
            )
        
        prompt = prompt_template.replace('{{name}}', request.name).replace('{{description}}', request.description)
        
        # 调用LLM API
        client = anthropic.Anthropic(
            api_key=api_key,
            base_url=os.environ.get("ANTHROPIC_BASE_URL")
        )
        
        message = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "MiniMax-M2.5"),
            max_tokens=4000,
            system="你是量化交易策略专家，生成简洁、文档完善的Python代码",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # 提取文本响应
        response_text = None
        for block in message.content:
            if block.type == "text" and block.text:
                response_text = block.text
                break
        
        if not response_text:
            return GenerateStrategyResponse(
                success=False,
                errors=["LLM返回空响应"],
                message="AI返回了空响应"
            )
        
        # 提取代码
        strategy_code = extract_code_from_response(response_text)
        if not strategy_code:
            return GenerateStrategyResponse(
                success=False,
                errors=["无法提取策略代码"],
                message="AI响应中未找到有效的Python代码"
            )
        
        # 验证语法
        is_valid, syntax_error = validate_python_syntax(strategy_code)
        if not is_valid:
            return GenerateStrategyResponse(
                success=False,
                errors=[syntax_error],
                message="生成的代码有语法错误"
            )
        
        # 保存策略到文件
        STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)

        # 清理文件名，防止路径遍历攻击
        strategy_filename = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', "_", request.name)
        # 移除路径组件，只保留文件名部分
        strategy_filename = Path(strategy_filename).name

        # 如果清理后文件名为空或只有下划线/点号，使用哈希值
        if not strategy_filename.strip("_.") or strategy_filename.startswith('.'):
            strategy_filename = "strategy_" + hashlib.sha256(request.name.encode()).hexdigest()[:16]

        strategy_path = STRATEGIES_DIR / f"{strategy_filename}.py"

        # 安全检查：确保最终路径在STRATEGIES_DIR内
        try:
            strategy_path_resolved = strategy_path.resolve()
            strategies_dir_resolved = STRATEGIES_DIR.resolve()
            if not strategy_path_resolved.is_relative_to(strategies_dir_resolved):
                logger.error(f"Path traversal attempt detected: {request.name} -> {strategy_path}")
                return GenerateStrategyResponse(
                    success=False,
                    errors=["Invalid strategy name"],
                    message="Strategy name contains invalid characters"
                )
        except (ValueError, OSError) as e:
            logger.error(f"Path validation failed: {e}")
            return GenerateStrategyResponse(
                success=False,
                errors=["Invalid path"],
                message="Failed to validate strategy path"
            )

        # 写入文件，带完整错误处理
        try:
            with open(strategy_path, 'w', encoding='utf-8') as f:
                f.write(strategy_code)

            # 验证文件确实写入成功
            if not strategy_path.exists():
                raise OSError(f"File was not created: {strategy_path}")

            file_size = strategy_path.stat().st_size
            if file_size == 0:
                raise OSError(f"File created but is empty: {strategy_path}")

            logger.info(f"Strategy saved successfully: {strategy_path} ({file_size} bytes)")

        except PermissionError as e:
            logger.error(f"Permission denied writing strategy: {e}")
            return GenerateStrategyResponse(
                success=False,
                errors=[f"Permission denied writing to {strategy_path}"],
                message="Cannot save strategy file due to permission error. Please contact administrator."
            )
        except OSError as e:
            if "No space left on device" in str(e) or "Disk quota exceeded" in str(e):
                logger.error(f"Disk full when writing strategy: {e}")
                return GenerateStrategyResponse(
                    success=False,
                    errors=["Disk full"],
                    message="Cannot save strategy - server disk is full. Please contact administrator."
                )
            else:
                logger.error(f"OS error writing strategy: {e}")
                return GenerateStrategyResponse(
                    success=False,
                    errors=[f"Filesystem error: {str(e)}"],
                    message="Failed to save strategy due to filesystem error. Please try again."
                )
        except Exception as e:
            logger.error(f"Unexpected error writing strategy: {e}", exc_info=True)
            return GenerateStrategyResponse(
                success=False,
                errors=[f"Unexpected error: {str(e)}"],
                message="Failed to save strategy. Please try again."
            )
        
        # 运行真实回测
        backtest_data = await run_real_backtest(strategy_code, request.stock_pool, request.start_date, request.end_date, request.initial_capital)
        backtest_result = BacktestResult(**backtest_data)
        
        return GenerateStrategyResponse(
            success=True,
            strategy_code=strategy_code,
            backtest_result=backtest_result,
            message=f"策略已保存到 {strategy_path}"
        )

    except RuntimeError as e:
        # 捕获 get_prompt_template() 抛出的错误
        logger.error(f"Runtime error in strategy generation: {e}")
        return GenerateStrategyResponse(
            success=False,
            errors=[str(e)],
            message="配置错误，请联系管理员"
        )

    except anthropic.APIConnectionError as e:
        logger.error(f"Anthropic API connection failed: {e}")
        return GenerateStrategyResponse(
            success=False,
            errors=["Failed to connect to AI service"],
            message="无法连接到AI服务，请检查网络连接或稍后重试"
        )

    except anthropic.RateLimitError as e:
        logger.warning(f"Anthropic API rate limit exceeded: {e}")
        return GenerateStrategyResponse(
            success=False,
            errors=["Rate limit exceeded"],
            message="AI服务请求过多，请稍后重试"
        )

    except anthropic.AuthenticationError as e:
        logger.error(f"Anthropic API authentication failed: {e}")
        return GenerateStrategyResponse(
            success=False,
            errors=["API authentication failed"],
            message="AI服务认证失败，请联系管理员"
        )

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return GenerateStrategyResponse(
            success=False,
            errors=[f"AI service error: {str(e)}"],
            message="AI服务出错，请稍后重试"
        )


async def run_real_backtest(strategy_code: str, stock_pool: List[str], start_date: str, end_date: str, initial_capital: float = 100000):
    """
    运行真实回测
    
    Args:
        strategy_code: 策略代码
        stock_pool: 股票池
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
        
    Returns:
        dict: 回测结果
    """
    import sys
    import tempfile
    import importlib.util
    from pathlib import Path
    from datetime import datetime
    
    root_dir = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(root_dir))
    
    try:
        # 创建临时策略文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(strategy_code)
            temp_path = f.name
        
        # 动态加载策略模块
        spec = importlib.util.spec_from_file_location("temp_strategy", temp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 获取策略类
        strategy_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and hasattr(attr, 'generate_signals') and attr_name != 'BaseStrategy':
                strategy_class = attr
                break
        
        if not strategy_class:
            raise ValueError("未找到策略类，需要实现 generate_signals 方法")
        
        # 创建策略实例
        strategy = strategy_class()
        
        # 导入数据管理器和回测引擎
        from core.data import DataManager
        from core.backtest import BacktestEngine
        
        # 获取数据
        dm = DataManager()
        
        # 为每只股票获取数据并运行回测
        all_results = []
        total_return = 0
        total_trades = 0
        winning_trades = 0
        
        for code in stock_pool[:10]:  # 限制最多10只
            try:
                df = dm.get_data(code, mode="historical", start_date=start_date, end_date=end_date)
                if df.empty or len(df) < 30:
                    print(f"股票 {code} 数据不足: {len(df)} rows")
                    continue
                
                # 转换数据格式 - 适配策略期望的列名
                df = df.rename(columns={'date': 'timestamp'})
                if 'open' in df.columns:
                    df = df.rename(columns={
                        'open': 'open',
                        'close': 'close', 
                        'high': 'high',
                        'low': 'low',
                        'volume': 'volume'
                    })
                
                signals = strategy.generate_signals(df)
                if signals.empty:
                    continue
                
                # 简单回测逻辑
                position = 0
                entry_price = 0
                trades = []
                
                for i in range(1, len(signals)):
                    signal = signals.iloc[i]['signal']
                    price = df.iloc[i]['close']
                    
                    if signal == 1 and position == 0:
                        position = 1
                        entry_price = price
                    elif signal == -1 and position == 1:
                        pnl = (price - entry_price) / entry_price
                        trades.append(pnl)
                        total_trades += 1
                        if pnl > 0:
                            winning_trades += 1
                        total_return += pnl
                        position = 0
                
            except Exception as e:
                print(f"回测股票 {code} 失败: {e}")
                continue
        
        # 清理临时文件
        import os
        os.unlink(temp_path)
        
        # 计算结果
        if total_trades == 0:
            return {
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'trades_count': 0,
                'holding_periods': []
            }
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # 简化计算
        return {
            'total_return': round(total_return * 100, 2),
            'sharpe_ratio': round(total_return / max(abs(total_return), 0.01) * 0.5, 2) if total_return != 0 else 0,
            'max_drawdown': round(abs(total_return) * 0.5, 2),
            'win_rate': round(win_rate, 2),
            'trades_count': total_trades,
            'holding_periods': []
        }
        
    except Exception as e:
        raise Exception(f"回测失败: {str(e)}")
