# -*- coding: utf-8 -*-
"""
全市场多年度回测 - 涨停回调策略
按年度分别计算收益率
"""

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_fetcher import DataFetcher
from src.technical import TechnicalIndicators


class MultiYearBacktest:
    """多年度回测类"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []

        # 策略参数
        self.limit_up_days = 10
        self.max_continuous_limit_up = 3
        self.ma_period = 20
        self.volume_ratio = 1.5

    def get_limit_up_stocks(self, code: str, hist: pd.DataFrame, check_date: str) -> bool:
        """检查指定日期前N天内是否有过涨停"""
        try:
            check_dt = pd.to_datetime(check_date)
            hist['date_dt'] = pd.to_datetime(hist['date'])
            before_data = hist[hist['date_dt'] <= check_dt].copy()

            if len(before_data) < self.limit_up_days:
                return False

            recent_data = before_data.tail(self.limit_up_days)
            has_limit_up = (recent_data['涨跌幅'] >= 9.5).any()

            if not has_limit_up:
                return False

            max_consecutive = 0
            current_consecutive = 0
            for change_pct in recent_data['涨跌幅']:
                if change_pct >= 9.5:
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0

            return max_consecutive < self.max_continuous_limit_up
        except Exception as e:
            pass

        return False

    def check_buy_signal(self, hist: pd.DataFrame, date_idx: int) -> bool:
        """检查买入信号"""
        if date_idx < self.ma_period:
            return False

        current = hist.iloc[date_idx]
        prev = hist.iloc[date_idx - 1]

        # 计算MA20
        ma20 = hist.iloc[date_idx - self.ma_period:date_idx + 1]['close'].mean()

        # 条件1：股价接近MA20（±2%）
        if abs(current['close'] - ma20) / ma20 > 0.02:
            return False

        # 条件2：阳线
        if current['close'] <= current['open']:
            return False

        # 条件3：放量
        if date_idx >= 5:
            avg_volume = hist.iloc[date_idx - 5:date_idx]['volume'].mean()
        else:
            avg_volume = hist.iloc[:date_idx + 1]['volume'].mean()

        if current['volume'] < avg_volume * self.volume_ratio:
            return False

        return True

    def run_single_year(
        self,
        stock_history: dict,
        start_date: str,
        end_date: str,
        initial_cash: float
    ) -> dict:
        """单年度回测"""
        self.cash = initial_cash
        self.positions = {}
        self.trades = []
        self.daily_values = []

        # 获取所有交易日期
        all_dates = set()
        for code, hist in stock_history.items():
            for date in hist['date']:
                date_str = pd.to_datetime(date).strftime('%Y%m%d')
                if start_date <= date_str <= end_date:
                    all_dates.add(date_str)

        all_dates = sorted(list(all_dates))

        for date_str in all_dates:
            date_obj = datetime.strptime(date_str, '%Y%m%d')

            # 检查卖出
            codes_to_sell = []
            for code, pos in self.positions.items():
                if code not in stock_history:
                    continue

                hist = stock_history[code]
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

                profit_pct = (close_price - pos['entry_price']) / pos['entry_price'] * 100

                # 卖出条件1：跌破MA20
                if close_price < ma20:
                    codes_to_sell.append((code, close_price, "跌破MA20"))
                    continue

                # 卖出条件2：次日跌破MA20止损
                days_held = (date_obj - datetime.strptime(pos['entry_date'], '%Y%m%d')).days
                if days_held == 1 and close_price < ma20:
                    codes_to_sell.append((code, close_price, "次日跌破MA20止损"))
                    continue

                # 分批止盈
                if profit_pct >= 50 and pos.get('tp30_taken', False):
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
                    del self.positions[code]

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

            # 检查买入
            if len(self.positions) < 5:
                for code in stock_history.keys():
                    if code in self.positions:
                        continue

                    hist = stock_history[code]
                    day_data = hist[hist['date'].dt.strftime('%Y%m%d') == date_str]

                    if day_data.empty:
                        continue

                    day_data = day_data.iloc[0]
                    date_idx = hist.index.get_loc(day_data.name)

                    if self.check_buy_signal(hist, date_idx):
                        buy_price = day_data['close']
                        buy_amount = self.cash * 0.2

                        if buy_amount > 1000:
                            shares = int(buy_amount / buy_price / 100) * 100
                            if shares > 0:
                                self.cash -= shares * buy_price

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

        # 平掉剩余持仓
        final_date = all_dates[-1] if all_dates else end_date
        for code, pos in list(self.positions.items()):
            if code in stock_history:
                hist = stock_history[code]
                day_data = hist[hist['date'].dt.strftime('%Y%m%d') == final_date]
                if not day_data.empty:
                    final_price = day_data.iloc[0]['close']
                    profit_pct = (final_price - pos['entry_price']) / pos['entry_price'] * 100

                    self.cash += pos['shares'] * final_price
                    del self.positions[code]

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

        # 计算结果
        trades_df = pd.DataFrame(self.trades)
        if not trades_df.empty:
            buy_trades = trades_df[trades_df['action'] == 'buy']
            sell_trades = trades_df[trades_df['action'] == 'sell']

            total_return = (self.cash - initial_cash) / initial_cash * 100

            profit_trades = sell_trades[sell_trades['profit_pct'] > 0]
            loss_trades = sell_trades[sell_trades['profit_pct'] <= 0]
            win_rate = len(profit_trades) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0

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
                'daily_values_df': pd.DataFrame(self.daily_values) if self.daily_values else pd.DataFrame(),
            }

        return {
            'total_return': 0,
            'final_capital': initial_cash,
            'total_trades': 0,
            'win_rate': 0,
            'max_drawdown': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'trades_df': trades_df,
            'daily_values_df': pd.DataFrame(),
        }


def main():
    """主函数 - 全市场多年度回测"""
    print("=" * 70)
    print("全市场多年度回测 - 涨停回调策略 (2019-2025)")
    print("=" * 70)

    fetcher = DataFetcher()

    # 回测参数
    years = [
        ('2019', '20190101', '20191231'),
        ('2020', '20200101', '20201231'),
        ('2021', '20210101', '20211231'),
        ('2022', '20220101', '20221231'),
        ('2023', '20230101', '20231231'),
        ('2024', '20240101', '20241231'),
        ('2025', '20250101', '20251231'),
    ]

    # 获取所有股票
    print("\n[1] 获取股票列表...")
    all_stocks = fetcher.get_stock_list()
    print(f"    总股票数: {len(all_stocks)}")
    print(f"    ⚠️  全市场回测：{len(all_stocks)} 只股票")

    # 准备历史数据（一次性获取2018-2025的数据，避免重复请求）
    print(f"\n[2] 获取历史行情数据（2018-2025）...")
    stock_history = {}

    # 限制股票数量以控制时间（或者分批处理）
    # 全市场需要很长时间，这里先处理前2000只作为示例
    max_stocks = min(len(all_stocks), 2000)
    sample_stocks = all_stocks.head(max_stocks)
    print(f"    回测股票数: {len(sample_stocks)}")

    for i, (_, stock) in enumerate(sample_stocks.iterrows()):
        code = stock['code']
        name = stock['name']

        try:
            hist = fetcher.get_stock_history(
                symbol=code,
                start_date="20180101",  # 多取1年用于计算指标
                end_date="20251231",
                adjust="qfq"
            )

            if hist is not None and not hist.empty:
                hist['code'] = code
                hist['name'] = name
                hist['涨跌幅'] = hist['close'].pct_change() * 100
                stock_history[code] = hist

        except Exception as e:
            continue

        if (i + 1) % 200 == 0:
            print(f"    进度: {i+1}/{len(sample_stocks)} ({(i+1)/len(sample_stocks)*100:.1f}%)")

    print(f"    成功获取: {len(stock_history)} 只股票")

    # 按年度回测
    print(f"\n[3] 按年度回测...")
    yearly_results = {}

    current_cash = 100000

    for year_name, start_date, end_date in years:
        print(f"\n{'='*70}")
        print(f"回测年度: {year_name}")
        print(f"{'='*70}")

        backtest = MultiYearBacktest()

        results = backtest.run_single_year(
            stock_history=stock_history,
            start_date=start_date,
            end_date=end_date,
            initial_cash=current_cash
        )

        # 更新下一年度的初始资金
        current_cash = results['final_capital']

        yearly_results[year_name] = results

        print(f"\n{year_name}年度结果:")
        print(f"  初始资金: {results['final_capital']/1.0000:,.2f} 元" if results['total_return'] == 0 else f"  初始资金: {results['final_capital']/1.0000:,.2f} 元")
        print(f"  收益率: {results['total_return']:.2f}%")
        print(f"  交易次数: {results['total_trades']}")
        print(f"  胜率: {results['win_rate']:.2f}%")
        print(f"  最大回撤: {results['max_drawdown']:.2f}%")

    # 保存结果
    print(f"\n[4] 保存回测数据...")
    import json
    from datetime import datetime

    output_dir = "data/backtest_results"
    os.makedirs(output_dir, exist_ok=True)

    # 保存年度结果
    summary = {
        'backtest_period': '2019-01-01 to 2025-12-31',
        'stocks_tested': len(stock_history),
        'initial_capital': 100000,
        'final_capital': current_cash,
        'total_return': (current_cash - 100000) / 100000 * 100,
        'years': yearly_results
    }

    # 简化年度结果用于保存
    summary_simple = {
        'backtest_period': '2019-01-01 to 2025-12-31',
        'stocks_tested': len(stock_history),
        'initial_capital': 100000,
        'final_capital': current_cash,
        'total_return': (current_cash - 100000) / 100000 * 100,
        'years': {}
    }

    # Get year list for proper indexing
    year_list = list(yearly_results.keys())
    for i, year in enumerate(year_list):
        prev_year_final_capital = 100000 if i == 0 else yearly_results[year_list[i-1]]['final_capital']
        summary_simple['years'][year] = {
            'initial_capital': prev_year_final_capital,
            'final_capital': yearly_results[year]['final_capital'],
            'total_return': yearly_results[year]['total_return'],
            'total_trades': yearly_results[year]['total_trades'],
            'win_rate': yearly_results[year]['win_rate'],
            'max_drawdown': yearly_results[year]['max_drawdown'],
        }

    summary_file = os.path.join(output_dir, "multi_year_summary_2019_2025.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_simple, f, ensure_ascii=False, indent=2)
    print(f"    年度结果已保存: {summary_file}")

    # 打印汇总表格
    print(f"\n{'='*70}")
    print("年度回测汇总")
    print(f"{'='*70}")
    print(f"{'年度':<8} {'收益率':>12} {'交易次数':>10} {'胜率':>10} {'最大回撤':>12}")
    print(f"{'-'*70}")

    for year in years:
        year_name = year[0]
        r = summary_simple['years'][year_name]
        print(f"{year_name:<8} {r['total_return']:>10.2f}%     {r['total_trades']:>10} {r['win_rate']:>9.1f}%   {r['max_drawdown']:>10.2f}%")

    print(f"{'-'*70}")
    total_return = summary_simple['total_return']
    print(f"{'总计':<8} {total_return:>10.2f}%     {summary_simple['stocks_tested']}只股票")

    print(f"\n回测完成！")


if __name__ == "__main__":
    main()
