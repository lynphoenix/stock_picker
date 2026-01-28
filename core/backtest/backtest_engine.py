# -*- coding: utf-8 -*-
"""
回测引擎
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
import pandas as pd
import numpy as np

from core.strategies import Strategy
from core.data import DataManager
from .portfolio import Portfolio
from .risk_manager import RiskManager


@dataclass
class BacktestResult:
    """回测结果"""
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    win_rate: float
    max_drawdown: float
    avg_hold_days: float
    profit_factor: float
    trades_df: pd.DataFrame
    daily_values_df: pd.DataFrame

    # 最佳/最差交易
    best_trade: Dict = None
    worst_trade: Dict = None


class BacktestEngine:
    """
    回测引擎 - 策略无关

    负责执行回测流程，与具体策略解耦
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        risk_config: Dict = None
    ):
        """
        Args:
            initial_capital: 初始资金
            risk_config: 风险管理配置
        """
        self.initial_capital = initial_capital
        self.portfolio = Portfolio(initial_capital)
        self.risk_manager = RiskManager(risk_config)
        self.data_manager = DataManager()

    def run(
        self,
        strategy: Strategy,
        stock_pool: List[str],
        start_date: str,
        end_date: str,
        check_interval: int = 3
    ) -> BacktestResult:
        """
        运行回测

        Args:
            strategy: 策略对象
            stock_pool: 股票池（股票代码列表）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            check_interval: 检查信号的间隔天数

        Returns:
            回测结果
        """
        print(f"\n{'='*60}")
        print(f"回测引擎 - {strategy.name} 策略")
        print(f"{'='*60}")
        print(f"时间范围: {start_date} ~ {end_date}")
        print(f"股票池: {len(stock_pool)} 只")
        print(f"初始资金: {self.initial_capital:,.0f} 元")
        print(f"风控配置: {self.risk_manager}")

        # 1. 加载历史数据
        print(f"\n[1/4] 加载历史数据...")
        data_dict = self._load_data(stock_pool, strategy, start_date, end_date)
        print(f"    成功加载 {len(data_dict)} 只股票数据")

        if not data_dict:
            print("❌ 无可用数据，回测终止")
            return self._empty_result()

        # 2. 执行回测主循环
        print(f"\n[2/4] 执行回测模拟...")
        self._backtest_loop(data_dict, strategy, start_date, end_date, check_interval)

        # 3. 平仓剩余持仓
        print(f"\n[3/4] 平仓剩余持仓...")
        self._close_remaining_positions(data_dict, end_date)

        # 4. 计算回测指标
        print(f"\n[4/4] 计算回测指标...")
        result = self._calculate_results()

        return result

    def _load_data(
        self,
        stock_pool: List[str],
        strategy: Strategy,
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """加载并准备数据"""
        data_dict = {}

        # 获取策略需要的指标
        required_indicators = strategy.get_required_indicators()

        for code in stock_pool:
            try:
                # 获取历史数据
                df = self.data_manager.get_data(
                    code,
                    mode="historical",
                    start_date=start_date,
                    end_date=end_date
                )

                if df.empty or len(df) < 60:
                    continue

                # 添加指标
                df = self.data_manager.add_indicators(df, required_indicators)

                data_dict[code] = df

            except Exception as e:
                print(f"    加载 {code} 失败: {e}")
                continue

        return data_dict

    def _backtest_loop(
        self,
        data_dict: Dict[str, pd.DataFrame],
        strategy: Strategy,
        start_date: str,
        end_date: str,
        check_interval: int
    ):
        """回测主循环"""
        # 生成交易日列表
        dates = pd.date_range(start=start_date, end=end_date, freq="B")

        for i, date in enumerate(dates):
            # 获取当日价格
            current_prices = {}
            for code, df in data_dict.items():
                day_data = df[df["date"].dt.date == date.date()]
                if not day_data.empty:
                    current_prices[code] = day_data.iloc[0]["close"]

            # 更新每日资产价值
            self.portfolio.update_daily_value(date, current_prices)

            # 按间隔检查信号
            if i % check_interval != 0:
                continue

            # 检查卖出信号
            self._check_sell_signals(data_dict, date, strategy)

            # 检查买入信号
            self._check_buy_signals(data_dict, date, strategy)

    def _check_sell_signals(
        self,
        data_dict: Dict[str, pd.DataFrame],
        date: datetime,
        strategy: Strategy
    ):
        """检查卖出信号"""
        for code in list(self.portfolio.positions.keys()):
            if code not in data_dict:
                continue

            position = self.portfolio.positions[code]

            # 获取截止到当前日期的数据
            df = data_dict[code]
            hist = df[df["date"] <= date].copy()

            if hist.empty:
                continue

            # 获取当前价格
            latest = hist.iloc[-1]
            current_price = latest["close"]

            # 更新持仓价格
            position.update_price(current_price)

            # 生成技术信号
            signal_result = strategy.generate_signals(hist)
            technical_signal = signal_result.reasons[0] if signal_result.action == "sell" else ""

            # 风控检查
            should_sell, sell_shares, reason = self.risk_manager.check_sell_signals(
                position,
                technical_signal
            )

            if should_sell:
                self.portfolio.sell(
                    code=code,
                    price=current_price,
                    shares=sell_shares,
                    date=date,
                    reason=reason
                )

    def _check_buy_signals(
        self,
        data_dict: Dict[str, pd.DataFrame],
        date: datetime,
        strategy: Strategy
    ):
        """检查买入信号"""
        # 如果持仓已满，不再买入
        if len(self.portfolio.positions) >= self.risk_manager.config["max_positions"]:
            return

        for code, df in data_dict.items():
            # 已持仓的跳过
            if code in self.portfolio.positions:
                continue

            # 获取截止到当前日期的数据
            hist = df[df["date"] <= date].copy()

            if hist.empty or len(hist) < 60:
                continue

            # 生成信号
            signal_result = strategy.generate_signals(hist)

            # 检查买入信号
            if signal_result.action != "buy":
                continue

            # 获取当前价格
            latest = hist.iloc[-1]
            current_price = latest["close"]

            # 计算买入数量
            shares = self.risk_manager.calculate_position_size(
                self.portfolio,
                current_price
            )

            if shares <= 0:
                continue

            amount = shares * current_price

            # 风控检查
            if not self.risk_manager.can_buy(self.portfolio, code, amount):
                continue

            # 执行买入
            success = self.portfolio.buy(
                code=code,
                name=code,  # 实际应该传入股票名称
                price=current_price,
                shares=shares,
                date=date,
                reason=f"{signal_result.score:.0f}分: {', '.join(signal_result.reasons)}",
                buy_score=signal_result.score
            )

            # 如果持仓已满，停止
            if success and len(self.portfolio.positions) >= self.risk_manager.config["max_positions"]:
                break

    def _close_remaining_positions(
        self,
        data_dict: Dict[str, pd.DataFrame],
        end_date: str
    ):
        """平仓剩余持仓"""
        end_dt = pd.to_datetime(end_date)

        for code in list(self.portfolio.positions.keys()):
            if code not in data_dict:
                continue

            df = data_dict[code]
            final_price = df.iloc[-1]["close"]

            self.portfolio.sell(
                code=code,
                price=final_price,
                shares=None,
                date=end_dt,
                reason="回测结束"
            )

    def _calculate_results(self) -> BacktestResult:
        """计算回测结果"""
        summary = self.portfolio.get_summary()
        trades_df = self.portfolio.get_trades_df()
        daily_values_df = self.portfolio.get_daily_values_df()

        # 卖出交易
        sell_trades = trades_df[trades_df["action"] == "sell"] if not trades_df.empty else pd.DataFrame()

        # 胜率
        if not sell_trades.empty:
            win_trades = sell_trades[sell_trades["profit_pct"] > 0]
            win_rate = len(win_trades) / len(sell_trades) * 100
        else:
            win_rate = 0

        # 平均持仓天数
        if not sell_trades.empty and "holding_days" in sell_trades.columns:
            avg_hold_days = sell_trades["holding_days"].mean()
        else:
            avg_hold_days = 0

        # 盈亏比
        if not sell_trades.empty:
            total_profit = sell_trades[sell_trades["profit_pct"] > 0]["profit_pct"].sum()
            total_loss = abs(sell_trades[sell_trades["profit_pct"] <= 0]["profit_pct"].sum())
            profit_factor = total_profit / total_loss if total_loss > 0 else 0
        else:
            profit_factor = 0

        # 最大回撤
        if not daily_values_df.empty:
            values = daily_values_df["total_value"].values
            peak = values[0]
            max_drawdown = 0
            for v in values:
                if v > peak:
                    peak = v
                drawdown = (peak - v) / peak * 100 if peak > 0 else 0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        else:
            max_drawdown = 0

        # 最佳/最差交易
        best_trade = None
        worst_trade = None
        if not sell_trades.empty:
            best_idx = sell_trades["profit_pct"].idxmax()
            worst_idx = sell_trades["profit_pct"].idxmin()
            best_trade = sell_trades.loc[best_idx].to_dict()
            worst_trade = sell_trades.loc[worst_idx].to_dict()

        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=summary["total_value"],
            total_return=summary["total_return"],
            total_trades=len(sell_trades),
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            avg_hold_days=avg_hold_days,
            profit_factor=profit_factor,
            trades_df=trades_df,
            daily_values_df=daily_values_df,
            best_trade=best_trade,
            worst_trade=worst_trade
        )

    def _empty_result(self) -> BacktestResult:
        """返回空结果"""
        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return=0,
            total_trades=0,
            win_rate=0,
            max_drawdown=0,
            avg_hold_days=0,
            profit_factor=0,
            trades_df=pd.DataFrame(),
            daily_values_df=pd.DataFrame()
        )

    def print_results(self, result: BacktestResult):
        """打印回测结果"""
        print(f"\n{'='*60}")
        print(f"回测结果汇总")
        print(f"{'='*60}")
        print(f"初始资金: {result.initial_capital:>15,.2f} 元")
        print(f"最终资金: {result.final_capital:>15,.2f} 元")
        print(f"总收益率: {result.total_return:>15.2f} %")
        print(f"交易次数: {result.total_trades:>15} 次")
        print(f"胜率:     {result.win_rate:>15.2f} %")
        print(f"平均持仓: {result.avg_hold_days:>15.1f} 天")
        print(f"盈亏比:   {result.profit_factor:>15.2f}")
        print(f"最大回撤: {result.max_drawdown:>15.2f} %")

        if result.best_trade:
            print(f"\n最佳交易: {result.best_trade['name']}({result.best_trade['code']}) "
                  f"+{result.best_trade['profit_pct']:.2f}%")

        if result.worst_trade:
            print(f"最差交易: {result.worst_trade['name']}({result.worst_trade['code']}) "
                  f"{result.worst_trade['profit_pct']:.2f}%")

        # 显示最近交易
        if not result.trades_df.empty:
            print(f"\n{'='*60}")
            print(f"最近20笔交易")
            print(f"{'='*60}")
            cols = ["date", "code", "action", "price", "shares", "profit_pct", "reason"]
            available_cols = [c for c in cols if c in result.trades_df.columns]
            print(result.trades_df[available_cols].tail(20).to_string(index=False))
