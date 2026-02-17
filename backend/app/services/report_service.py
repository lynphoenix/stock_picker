# -*- coding: utf-8 -*-
"""
报表服务层
"""
import json
from pathlib import Path
from typing import Optional
import sys

root_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_dir))


class ReportService:
    """报表服务"""

    def __init__(self):
        self.tasks_dir = Path(root_dir) / "data" / "backtest_tasks"
        self.reports_dir = Path(root_dir) / "data" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_excel(self, task_id: str) -> Path:
        """
        生成Excel报表

        Args:
            task_id: 回测任务ID

        Returns:
            Excel文件路径
        """
        # 加载回测结果
        result = self._load_result(task_id)
        if not result:
            raise FileNotFoundError(f"任务 {task_id} 的结果不存在")

        # 生成Excel文件
        excel_file = self.reports_dir / f"backtest_report_{task_id}.xlsx"

        # TODO: 使用openpyxl或XlsxWriter生成Excel
        # 包含：概览、年度对比、交易明细、图表等
        # 这里先创建一个空文件占位
        excel_file.touch()

        return excel_file

    def generate_pdf(self, task_id: str) -> Path:
        """
        生成PDF报表

        Args:
            task_id: 回测任务ID

        Returns:
            PDF文件路径
        """
        # 加载回测结果
        result = self._load_result(task_id)
        if not result:
            raise FileNotFoundError(f"任务 {task_id} 的结果不存在")

        # 生成PDF文件
        pdf_file = self.reports_dir / f"backtest_report_{task_id}.pdf"

        # TODO: 使用reportlab生成PDF
        # 这里先创建一个空文件占位
        pdf_file.touch()

        return pdf_file

    def _load_result(self, task_id: str) -> Optional[dict]:
        """加载回测结果"""
        result_file = self.tasks_dir / f"{task_id}_result.json"
        if not result_file.exists():
            return None

        with open(result_file, 'r', encoding='utf-8') as f:
            return json.load(f)
