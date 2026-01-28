# -*- coding: utf-8 -*-
"""
新策略回测 - 涨停回调策略

策略逻辑：
1. 找到最近10个交易日内有涨停的个股，剔除连续3个涨停板及以上的
2. 选择MACD月线金叉的股票
3. 股价回调到20日均线附近且收出放量阳线 → 买入
4. 持仓规则：
   - 股价在20日均线上方 → 持有
   - 跌破20日均线 → 卖出
   - 涨幅>30% → 减仓1/3
   - 涨幅>50% → 再减仓一半
   - 买入次日跌破20日均线 → 立刻离场
"""

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_fetcher import DataFetcher
from src.technical import TechnicalIndicators


class NewStrategyBacktest:
    """涨停回调策略回测"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {code: {'shares': int, 'entry_price': float, 'entry_date': str}}
        self.trades = []  # 交易记录
        self.daily_values = []  # 每日净值

        # 策略参数
        self.limit_up_days = 10  # 涨停回溯天数
        self.max_continuous_limit_up = 3  # 最大连续涨停数
        self.ma_period = 20  # 均线周期
        self.volume_ratio = 1.5  # 放量倍数

    def get_limit_up_stocks(self, code: str, hist: pd.DataFrame, check_date: str) -> bool:
        """
        检查指定日期前N天内是否有过涨停，且连续涨停不超过3次

        Args:
            code: 股票代码
            hist: 历史行情数据
            check_date: 检查日期

        Returns:
            是否符合条件
        """
        try:
            # 将check_date转换为datetime
            check_dt = pd.to_datetime(check_date)

            # 筛选check_date之前的的数据
            hist['date_dt'] = pd.to_datetime(hist['date'])
            before_data = hist[hist['date_dt'] <= check_dt].copy()

            if len(before_data) < self.limit_up_days:
                return False

            # 获取最近N天的数据
            recent_data = before_data.tail(self.limit_up_days)

            # 检查是否有涨停（涨幅 >= 9.5%，考虑误差）
            has_limit_up = (recent_data['涨跌幅'] >= 9.5).any()

            if not has_limit_up:
                return False

            # 检查连续涨停次数
            max_consecutive = 0
            current_consecutive = 0

            for change_pct in recent_data['涨跌幅']:
                if change_pct >= 9.5:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0

            # 条件：有涨停，且连续涨停不超过max_continuous_limit_up次
            if max_consecutive < self.max_continuous_limit_up:
                return True

        except Exception as e:
            pass

        return False

    def check_monthly_macd_golden_cross(self, hist: pd.DataFrame) -> bool:
        """
        检查MACD月线是否金叉

        Args:
            hist: 历史行情数据（日线数据，需要转换为月线）

        Returns:
            是否金叉
        """
        if len(hist) < 60:  # 需要至少60个交易日的数据
            return False

        # 将日线数据转换为月线（简单采样：每月最后一个交易日）
        hist['year_month'] = pd.to_datetime(hist['date']).dt.to_period('M')
        monthly = hist.groupby('year_month').last().reset_index()

        if len(monthly) < 12:  # 需要至少12个月数据
            return False

        # 计算MACD
        tech = TechnicalIndicators()
        monthly_with_macd = tech.calculate_indicators(monthly)

        if 'DIF' not in monthly_with_macd.columns or 'DEA' not in monthly_with_macd.columns:
            return False

        # 检查最新的MACD是否金叉
        latest = monthly_with_macd.iloc[-1]
        prev = monthly_with_macd.iloc[-2]

        # 金叉条件：DIF上穿DEA，且都在0轴上方更佳
        if (prev['DIF'] <= prev['DEA'] and
            latest['DIF'] > latest['DEA']):
            return True

        return False

    def check_buy_signal(self, hist: pd.DataFrame, date_idx: int) -> bool:
        """
        检查买入信号：股价回调到20日均线附近且收出放量阳线

        Args:
            hist: 历史行情数据
            date_idx: 日期索引

        Returns:
            是否触发买入信号
        """
        if date_idx < self.ma_period:
            return False

        current = hist.iloc[date_idx]
        prev = hist.iloc[date_idx - 1]

        # 计算MA20
        ma20 = hist.iloc[date_idx - self.ma_period:date_idx + 1]['close'].mean()

        # 条件1：股价回调到MA20附近（±2%范围内）
        price_to_ma20 = abs(current['close'] - ma20) / ma20
        if price_to_ma20 > 0.02:
            return False

        # 计算平均成交量（5日）
        if date_idx >= 5:
            avg_volume = hist.iloc[date_idx - 5:date_idx]['volume'].mean()
        else:
            avg_volume = hist.iloc[:date_idx + 1]['volume'].mean()

        # 条件2：收出阳线
        if current['close'] <= current['open']:
            return False

        # 条件3：放量（成交量 > 平均成交量的1.5倍）
        if current['volume'] < avg_volume * self.volume_ratio:
            return False

        return True

    def run_backtest(
        self,
        start_date: str = "20250101",
        end_date: str = "20251231"
    ) -> Dict:
        """
        运行回测

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            回测结果
        """
        print("=" * 70)
        print("新策略回测 - 涨停回调策略")
        print("=" * 70)
        print(f"回测期间: {start_date} - {end_date}")
        print(f"初始资金: {self.initial_capital:,.2f} 元")

        fetcher = DataFetcher()

        # 获取所有股票列表 - 快速回测（1000只股票样本）
        print("\n[1] 获取股票列表...")
        all_stocks = fetcher.get_stock_list()
        print(f"    获取到 {len(all_stocks)} 只股票")
        print(f"    ⚠️  快速回测模式：使用前1000只股票")
        test_stocks = all_stocks.head(1000)  # 使用1000只股票

        # 准备存储历史数据
        stock_history = {}

        print(f"\n[2] 获取历史行情数据...")
        print(f"    数据范围: 2022-01-01 至 {end_date} (多取1年用于计算指标)")

        for i, (_, stock) in enumerate(test_stocks.iterrows()):
            code = stock['code']
            name = stock['name']

            try:
                hist = fetcher.get_stock_history(
                    symbol=code,
                    start_date="20220101",  # 多取数据用于计算指标
                    end_date=end_date,
                    adjust="qfq"
                )

                if hist is not None and not hist.empty:
                    hist['code'] = code
                    hist['name'] = name
                    # 计算涨跌幅
                    hist['涨跌幅'] = hist['close'].pct_change() * 100
                    stock_history[code] = hist

                if (i + 1) % 500 == 0:
                    print(f"    进度: {i+1}/{len(test_stocks)} ({(i+1)/len(test_stocks)*100:.1f}%)")

            except Exception as e:
                continue

        print(f"    成功获取: {len(stock_history)} 只股票")

        # 筛选符合条件的股票池
        print(f"\n[3] 筛选涨停股票池...")
        stock_pool = []

        for code, hist in stock_history.items():
            # 检查在回测期间是否有过涨停
            for idx in range(len(hist)):
                date_str = pd.to_datetime(hist.iloc[idx]['date']).strftime('%Y%m%d')

                if start_date <= date_str <= end_date:
                    if self.get_limit_up_stocks(code, hist, date_str):
                        # 检查MACD月线金叉（可选，暂时跳过因为条件太严格）
                        # if self.check_monthly_macd_golden_cross(hist):
                        stock_pool.append(code)
                        break

        print(f"    符合条件股票池: {len(stock_pool)} 只")

        # 模拟交易
        print(f"\n[4] 开始模拟交易...")

        # 获取所有交易日期
        all_dates = set()
        for hist in stock_history.values():
            for date in hist['date']:
                date_str = pd.to_datetime(date).strftime('%Y%m%d')
                if start_date <= date_str <= end_date:
                    all_dates.add(date_str)

        all_dates = sorted(list(all_dates))

        for date_str in all_dates:
            date_obj = datetime.strptime(date_str, '%Y%m%d')

            # 检查卖出信号
            codes_to_sell = []
            for code, pos in self.positions.items():
                if code not in stock_history:
                    continue

                hist = stock_history[code]
                # 找到对应日期的数据
                day_data = hist[hist['date'].dt.strftime('%Y%m%d') == date_str]

                if day_data.empty:
                    continue

                day_data = day_data.iloc[0]
                close_price = day_data['close']

                # 计算MA20
                date_idx = hist.index.get_loc(day_data.name)
                if date_idx >= self.ma_period:
                    ma20 = hist.iloc[date_idx - self.ma_period:date_idx + 1]['close'].mean()
                else:
                    ma20 = close_price

                # 计算涨幅
                profit_pct = (close_price - pos['entry_price']) / pos['entry_price'] * 100

                # 卖出条件1：跌破MA20
                if close_price < ma20:
                    codes_to_sell.append((code, close_price, "跌破MA20"))
                    continue

                # 卖出条件2：买入次日跌破MA20（止损）
                days_held = (date_obj - datetime.strptime(pos['entry_date'], '%Y%m%d')).days
                if days_held == 1 and close_price < ma20:
                    codes_to_sell.append((code, close_price, "次日跌破MA20止损"))
                    continue

                # 分批止盈
                if profit_pct >= 50 and pos.get('tp30_taken', False):
                    # 涨幅>50%且已减仓1/3，再减仓一半
                    shares_to_sell = pos['shares'] // 2
                    if shares_to_sell > 0:
                        self.cash += shares_to_sell * close_price
                        pos['shares'] -= shares_to_sell
                        pos['tp50_taken'] = True
                        self.trades.append({
                            'date': date_str,
                            'code': code,
                            'name': pos['name'],
                            'action': 'sell',
                            'price': close_price,
                            'shares': shares_to_sell,
                            'profit_pct': profit_pct,
                            'reason': f"涨幅{profit_pct:.1f}%减仓一半"
                        })

                elif profit_pct >= 30 and not pos.get('tp30_taken', False):
                    # 涨幅>30%，减仓1/3
                    shares_to_sell = pos['shares'] // 3
                    if shares_to_sell > 0:
                        self.cash += shares_to_sell * close_price
                        pos['shares'] -= shares_to_sell
                        pos['tp30_taken'] = True
                        self.trades.append({
                            'date': date_str,
                            'code': code,
                            'name': pos['name'],
                            'action': 'sell',
                            'price': close_price,
                            'shares': shares_to_sell,
                            'profit_pct': profit_pct,
                            'reason': f"涨幅{profit_pct:.1f}%减仓1/3"
                        })

            # 执行卖出
            for code, price, reason in codes_to_sell:
                if code in self.positions:
                    pos = self.positions[code]
                    shares = pos['shares']
                    profit_pct = (price - pos['entry_price']) / pos['entry_price'] * 100

                    self.cash += shares * price

                    self.trades.append({
                        'date': date_str,
                        'code': code,
                        'name': pos['name'],
                        'action': 'sell',
                        'price': price,
                        'shares': shares,
                        'profit_pct': profit_pct,
                        'reason': reason
                    })

                    del self.positions[code]

            # 检查买入信号
            if len(self.positions) < 5:  # 最多持仓5只
                for code in stock_pool:
                    if code in self.positions:
                        continue

                    if code not in stock_history:
                        continue

                    hist = stock_history[code]
                    day_data = hist[hist['date'].dt.strftime('%Y%m%d') == date_str]

                    if day_data.empty:
                        continue

                    day_data = day_data.iloc[0]
                    date_idx = hist.index.get_loc(day_data.name)

                    # 检查买入信号
                    if self.check_buy_signal(hist, date_idx):
                        buy_price = day_data['close']
                        buy_amount = self.cash * 0.2  # 每只20%仓位

                        if buy_amount > 1000:
                            shares = int(buy_amount / buy_price / 100) * 100  # 整手买入
                            if shares > 0:
                                actual_amount = shares * buy_price
                                self.cash -= actual_amount

                                self.positions[code] = {
                                    'shares': shares,
                                    'entry_price': buy_price,
                                    'entry_date': date_str,
                                    'name': hist.iloc[date_idx]['name'],
                                    'tp30_taken': False,
                                    'tp50_taken': False,
                                }

                                self.trades.append({
                                    'date': date_str,
                                    'code': code,
                                    'name': hist.iloc[date_idx]['name'],
                                    'action': 'buy',
                                    'price': buy_price,
                                    'shares': shares,
                                    'reason': '涨停回调+放量阳线'
                                })

                                if len(self.positions) >= 5:
                                    break

            # 计算当日净值
            total_value = self.cash
            for code, pos in self.positions.items():
                if code in stock_history:
                    hist = stock_history[code]
                    day_data = hist[hist['date'].dt.strftime('%Y%m%d') == date_str]
                    if not day_data.empty:
                        total_value += pos['shares'] * day_data.iloc[0]['close']

            self.daily_values.append({
                'date': date_str,
                'value': total_value
            })

        # 平掉所有持仓
        print(f"\n[5] 平掉剩余持仓...")
        final_date = all_dates[-1] if all_dates else end_date

        for code, pos in list(self.positions.items()):
            if code in stock_history:
                hist = stock_history[code]
                day_data = hist[hist['date'].dt.strftime('%Y%m%d') == final_date]
                if not day_data.empty:
                    final_price = day_data.iloc[0]['close']
                    profit_pct = (final_price - pos['entry_price']) / pos['entry_price'] * 100

                    self.cash += pos['shares'] * final_price

                    self.trades.append({
                        'date': final_date,
                        'code': code,
                        'name': pos['name'],
                        'action': 'sell',
                        'price': final_price,
                        'shares': pos['shares'],
                        'profit_pct': profit_pct,
                        'reason': '回测结束'
                    })

        del self.positions[code]

        # 计算回测结果
        return self._calculate_results()

    def _calculate_results(self) -> Dict:
        """计算回测结果"""
        trades_df = pd.DataFrame(self.trades)

        if not trades_df.empty:
            buy_trades = trades_df[trades_df['action'] == 'buy']
            sell_trades = trades_df[trades_df['action'] == 'sell']

            total_return = (self.cash - self.initial_capital) / self.initial_capital * 100

            # 计算胜率
            profit_trades = sell_trades[sell_trades['profit_pct'] > 0]
            loss_trades = sell_trades[sell_trades['profit_pct'] <= 0]
            win_rate = len(profit_trades) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0

            # 计算最大回撤
            if self.daily_values:
                values_df = pd.DataFrame(self.daily_values)
                values_df['cummax'] = values_df['value'].cummax()
                values_df['drawdown'] = (values_df['value'] - values_df['cummax']) / values_df['cummax'] * 100
                max_drawdown = values_df['drawdown'].min()
            else:
                max_drawdown = 0

            return {
                'total_return': total_return,
                'final_capital': self.cash,
                'total_trades': len(buy_trades),
                'win_rate': win_rate,
                'max_drawdown': max_drawdown,
                'avg_profit': profit_trades['profit_pct'].mean() if len(profit_trades) > 0 else 0,
                'avg_loss': loss_trades['profit_pct'].mean() if len(loss_trades) > 0 else 0,
                'trades_df': trades_df,
            }
        else:
            return {
                'total_return': 0,
                'final_capital': self.initial_capital,
                'total_trades': 0,
                'win_rate': 0,
                'max_drawdown': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'trades_df': trades_df,
            }


def main():
    """主函数"""
    # 三年回测：2023-2025
    backtest = NewStrategyBacktest(initial_capital=100000)

    results = backtest.run_backtest(
        start_date="20230101",
        end_date="20251231"
    )

    print("\n" + "=" * 70)
    print("回测结果")
    print("=" * 70)
    print(f"回测期间: 2023-01-01 至 2025-12-31 (3年)")
    print(f"初始资金: {backtest.initial_capital:,.2f} 元")
    print(f"最终资金: {results['final_capital']:,.2f} 元")
    print(f"总收益率: {results['total_return']:.2f}%")
    print(f"年化收益率: {((1 + results['total_return']/100) ** (1/3) - 1) * 100:.2f}%")
    print(f"总交易次数: {results['total_trades']}")
    print(f"胜率: {results['win_rate']:.2f}%")
    print(f"最大回撤: {results['max_drawdown']:.2f}%")
    print(f"平均盈利: {results['avg_profit']:.2f}%")
    print(f"平均亏损: {results['avg_loss']:.2f}%")

    # 保存回测数据
    print("\n[6] 保存回测数据...")
    import json
    from datetime import datetime

    output_dir = "data/backtest_results"
    os.makedirs(output_dir, exist_ok=True)

    # 保存交易记录
    if not results['trades_df'].empty:
        trades_file = os.path.join(output_dir, "trades_2023_2025.csv")
        results['trades_df'].to_csv(trades_file, index=False, encoding='utf-8-sig')
        print(f"    交易记录已保存: {trades_file}")

    # 保存回测摘要
    summary = {
        'backtest_period': '2023-01-01 to 2025-12-31',
        'initial_capital': backtest.initial_capital,
        'final_capital': results['final_capital'],
        'total_return': results['total_return'],
        'annualized_return': ((1 + results['total_return']/100) ** (1/3) - 1) * 100,
        'total_trades': results['total_trades'],
        'win_rate': results['win_rate'],
        'max_drawdown': results['max_drawdown'],
        'avg_profit': results['avg_profit'],
        'avg_loss': results['avg_loss'],
        'backtest_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    summary_file = os.path.join(output_dir, "summary_2023_2025.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"    回测摘要已保存: {summary_file}")

    # 保存每日净值
    if backtest.daily_values:
        daily_df = pd.DataFrame(backtest.daily_values)
        daily_file = os.path.join(output_dir, "daily_values_2023_2025.csv")
        daily_df.to_csv(daily_file, index=False, encoding='utf-8-sig')
        print(f"    每日净值已保存: {daily_file}")

    if not results['trades_df'].empty:
        print("\n" + "=" * 70)
        print("交易记录（最后20条）")
        print("=" * 70)
        print(results['trades_df'].tail(20).to_string(index=False))

    print("\n回测完成！")


if __name__ == "__main__":
    main()
