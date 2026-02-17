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

        # 扫描策略目录
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
