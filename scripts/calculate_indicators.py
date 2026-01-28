# -*- coding: utf-8 -*-
"""
计算技术指标
支持：MA, MACD, KDJ, RSI, BOLL
"""

import sys
from pathlib import Path
import pickle
import pandas as pd
import numpy as np
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))

from settings import CACHE_DIR


def calculate_ma(df, periods=[5, 10, 20, 60, 120, 250]):
    """计算移动平均线"""
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period).mean()
    return df


def calculate_macd(df, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    # 计算EMA
    df['EMA_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['EMA_slow'] = df['close'].ewm(span=slow, adjust=False).mean()

    # DIF = EMA_fast - EMA_slow
    df['DIF'] = df['EMA_fast'] - df['EMA_slow']

    # DEA = EMA(DIF, signal)
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()

    # MACD = 2 * (DIF - DEA)
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])

    # 删除中间列
    df.drop(['EMA_fast', 'EMA_slow'], axis=1, inplace=True)

    return df


def calculate_kdj(df, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    low_list = df['low'].rolling(window=n, min_periods=1).min()
    high_list = df['high'].rolling(window=n, min_periods=1).max()

    rsv = (df['close'] - low_list) / (high_list - low_list) * 100

    df['K'] = rsv.ewm(com=m1 - 1, adjust=False).mean()
    df['D'] = df['K'].ewm(com=m2 - 1, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']

    return df


def calculate_rsi(df, periods=[6, 12, 24]):
    """计算RSI指标"""
    for period in periods:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        df[f'RSI{period}'] = 100 - (100 / (1 + rs))

    return df


def calculate_boll(df, n=20, k=2):
    """计算布林带"""
    df['BOLL_MID'] = df['close'].rolling(window=n).mean()
    std = df['close'].rolling(window=n).std()

    df['BOLL_UP'] = df['BOLL_MID'] + k * std
    df['BOLL_LOW'] = df['BOLL_MID'] - k * std

    return df


def calculate_atr(df, n=14):
    """计算ATR（真实波幅）"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df[f'ATR{n}'] = tr.rolling(window=n).mean()

    return df


def calculate_indicators_for_file(file_path):
    """为单个文件计算所有指标"""
    try:
        # 读取数据
        with open(file_path, 'rb') as f:
            df = pickle.load(f)

        if df is None or df.empty:
            return False, "空文件"

        original_len = len(df)

        # 按日期排序
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # 计算指标
        df = calculate_ma(df)
        df = calculate_macd(df)
        df = calculate_kdj(df)
        df = calculate_rsi(df)
        df = calculate_boll(df)
        df = calculate_atr(df)

        # 保存
        with open(file_path, 'wb') as f:
            pickle.dump(df, f)

        return True, f"{original_len}条"

    except Exception as e:
        return False, str(e)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="计算技术指标")
    parser.add_argument("--year", type=int, default=None, help="只计算指定年份")
    parser.add_argument("--code", type=str, default=None, help="只计算指定股票")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已有指标文件")

    args = parser.parse_args()

    cache_dir = CACHE_DIR

    # 获取需要处理的文件
    if args.code and args.year:
        # 指定股票和年份
        files = [cache_dir / f'stock_hist_{args.code}_{args.year}0101_{args.year}1231_qfq.pkl']
    elif args.code:
        # 指定股票
        files = list(cache_dir.glob(f'stock_hist_{args.code}_*_qfq.pkl'))
    elif args.year:
        # 指定年份
        files = list(cache_dir.glob(f'stock_hist_*_{args.year}0101_{args.year}1231_qfq.pkl'))
    else:
        # 全部文件
        files = list(cache_dir.glob('stock_hist_*_qfq.pkl'))

    print(f"{'='*80}")
    print(f"计算技术指标")
    print(f"{'='*80}")
    print(f"待处理文件: {len(files)}")
    print(f"指标: MA5/10/20/60/120/250, MACD, KDJ, RSI6/12/24, BOLL, ATR14")
    print()

    success = 0
    failed = 0
    skipped = 0

    for file_path in tqdm(files, desc="处理进度"):
        ok, msg = calculate_indicators_for_file(file_path)

        if ok:
            success += 1
        elif "空文件" in msg:
            skipped += 1
        else:
            failed += 1

    print(f"\n{'='*80}")
    print("完成")
    print(f"{'='*80}")
    print(f"成功: {success}")
    print(f"跳过: {skipped}")
    print(f"失败: {failed}")


if __name__ == '__main__':
    main()
