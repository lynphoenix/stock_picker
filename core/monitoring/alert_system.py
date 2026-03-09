# -*- coding: utf-8 -*-
"""
告警系统
"""
from typing import Dict, Any, List
from datetime import datetime


class Alert:
    """告警"""

    def __init__(self, level: str, message: str):
        self.level = level
        self.message = message
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }


class AlertSystem:
    """告警系统"""

    def __init__(self):
        self.alerts: List[Alert] = []

    def send_alert(self, level: str, message: str) -> None:
        alert = Alert(level, message)
        self.alerts.append(alert)

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.alerts[-limit:]]


# 全局实例
alert_system = AlertSystem()
