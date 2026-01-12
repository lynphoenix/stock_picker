# -*- coding: utf-8 -*-
"""
通知模块 - 使用Server酱推送微信通知
"""
import requests
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class Notifier:
    """通知类"""

    def __init__(self):
        self.sendkey = config.SERVERCHAN_SENDKEY
        self.base_url = "https://sctapi.ftqq.com/{}.send"

    def send_wechat(
        self,
        title: str,
        content: str,
        sendkey: Optional[str] = None
    ) -> bool:
        """
        发送微信通知（通过Server酱）

        Args:
            title: 标题
            content: 内容
            sendkey: Server酱SendKey（可选，默认使用配置中的）

        Returns:
            是否发送成功
        """
        key = sendkey or self.sendkey

        if not key:
            print("未配置Server酱SendKey，跳过微信通知")
            print(f"【标题】{title}")
            print(f"【内容】\n{content}")
            return False

        try:
            url = self.base_url.format(key)

            # Server酱API
            data = {
                "title": title,
                "desp": content,  # 内容
            }

            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    print("微信通知发送成功")
                    return True
                else:
                    print(f"微信通知发送失败: {result.get('message')}")
                    return False
            else:
                print(f"微信通知请求失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"微信通知异常: {e}")
            return False

    def send_stock_signals(
        self,
        buy_list: list,
        sell_list: list,
        summary: str = ""
    ) -> bool:
        """
        发送选股信号通知

        Args:
            buy_list: 买入股票列表
            sell_list: 卖出股票列表
            summary: 汇总信息

        Returns:
            是否发送成功
        """
        # 构建标题
        title = f"📊 选股信号 - 买入{len(buy_list)}只 卖出{len(sell_list)}只"

        # 构建内容
        content_parts = []

        if summary:
            content_parts.append(summary)

        # 买入列表
        if buy_list:
            content_parts.append("## 🟢 买入信号\n")
            for stock in buy_list[:15]:
                reasons = " | ".join(stock.get("reasons", []))
                content_parts.append(
                    f"**{stock['name']}({stock['code']})** "
                    f"¥{stock.get('price', 0):.2f} "
                    f"强度:{stock.get('signal_strength', 0)}\n"
                    f"理由: {reasons}\n"
                )

        # 卖出列表
        if sell_list:
            content_parts.append("\n## 🔴 卖出信号\n")
            for stock in sell_list[:15]:
                reasons = " | ".join(stock.get("reasons", []))
                content_parts.append(
                    f"**{stock['name']}({stock['code']})** "
                    f"¥{stock.get('price', 0):.2f} "
                    f"强度:{stock.get('signal_strength', 0)}\n"
                    f"理由: {reasons}\n"
                )

        content = "\n".join(content_parts)

        return self.send_wechat(title, content)

    def send_simple_message(self, title: str, message: str) -> bool:
        """
        发送简单文本消息

        Args:
            title: 标题
            message: 消息内容

        Returns:
            是否发送成功
        """
        return self.send_wechat(title, message)

    def send_test_message(self) -> bool:
        """发送测试消息"""
        title = "🤖 选股系统测试"
        content = "这是一条测试消息，如果你的微信收到这条消息，说明通知功能配置正确！"
        return self.send_wechat(title, content)


# 便捷函数
def send_notification(title: str, content: str) -> bool:
    """快捷发送通知"""
    notifier = Notifier()
    return notifier.send_wechat(title, content)


if __name__ == "__main__":
    # 测试发送
    notifier = Notifier()

    print("=== 测试发送消息 ===")
    success = notifier.send_test_message()

    if success:
        print("请检查微信是否收到测试消息")

    # 测试选股信号
    print("\n=== 测试选股信号 ===")
    buy_list = [
        {"code": "000001", "name": "平安银行", "price": 10.5, "signal_strength": 75, "reasons": ["MACD金叉", "RSI超卖"]},
        {"code": "000002", "name": "万科A", "price": 8.3, "signal_strength": 65, "reasons": ["站上20日均线"]},
    ]
    sell_list = [
        {"code": "600000", "name": "浦发银行", "price": 7.2, "signal_strength": 80, "reasons": ["MACD死叉"]},
    ]

    notifier.send_stock_signals(buy_list, sell_list, "今日大盘震荡，板块轮动明显。")
