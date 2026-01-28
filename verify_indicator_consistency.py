# -*- coding: utf-8 -*-
"""
验证指标计算一致性
对比缓存中的指标 vs IndicatorFactory重新计算的指标
"""
import sys
import pandas as pd
import pickle
from pathlib import Path

sys.path.insert(0, '.')
from core.indicators import IndicatorFactory


def load_cached_data(code="000001", year="2024"):
    """从缓存加载数据"""
    cache_file = Path(f"data/cache/stock_hist_{code}_{year}0101_{year}1231_qfq.pkl")

    with open(cache_file, 'rb') as f:
        df = pickle.load(f)
    return df


def main():
    print("="*70)
    print("验证指标计算一致性")
    print("="*70)

    # 加载缓存数据（已包含指标）
    df_cached = load_cached_data("000001", "2024")

    print(f"\n1. 缓存数据:")
    print(f"   行数: {len(df_cached)}")
    print(f"   包含的指标: {[col for col in df_cached.columns if col in ['MA5', 'MA20', 'DIF', 'DEA', 'MACD', 'RSI6', 'RSI12']]}")

    # 提取原始OHLCV数据（不含指标）
    df_raw = df_cached[['date', 'open', 'high', 'low', 'close', 'volume']].copy()

    print(f"\n2. 原始OHLCV数据:")
    print(f"   列名: {list(df_raw.columns)}")

    # 使用IndicatorFactory重新计算
    print(f"\n3. 使用IndicatorFactory重新计算指标...")
    df_recalc = IndicatorFactory.calculate_multiple(df_raw, ["MA", "MACD", "RSI"])

    print(f"   计算后列名: {list(df_recalc.columns)}")

    # 对比最后10天的数据
    print(f"\n4. 对比最后10天的指标值:")
    print("="*70)

    # MA5对比
    print(f"\n▸ MA5 对比:")
    print(f"{'日期':<12} {'缓存MA5':>10} {'重算MA5':>10} {'差异':>10}")
    print("-"*50)
    for i in range(-10, 0):
        date = df_cached.iloc[i]['date']
        cached_ma5 = df_cached.iloc[i]['MA5']

        # 找到重新计算数据中对应的行
        recalc_row = df_recalc[df_recalc['date'] == date]
        if not recalc_row.empty:
            recalc_ma5 = recalc_row.iloc[0]['MA5']
            diff = abs(cached_ma5 - recalc_ma5)
            status = "✓" if diff < 0.01 else "✗"
            print(f"{str(date)[:10]:<12} {cached_ma5:>10.4f} {recalc_ma5:>10.4f} {diff:>9.4f} {status}")

    # MACD对比
    print(f"\n▸ MACD DIF 对比:")
    print(f"{'日期':<12} {'缓存DIF':>10} {'重算DIF':>10} {'差异':>10}")
    print("-"*50)
    for i in range(-10, 0):
        date = df_cached.iloc[i]['date']
        cached_dif = df_cached.iloc[i]['DIF']

        recalc_row = df_recalc[df_recalc['date'] == date]
        if not recalc_row.empty:
            recalc_dif = recalc_row.iloc[0]['MACD_DIF']
            diff = abs(cached_dif - recalc_dif)
            status = "✓" if diff < 0.01 else "✗"
            print(f"{str(date)[:10]:<12} {cached_dif:>10.4f} {recalc_dif:>10.4f} {diff:>9.4f} {status}")

    # RSI对比（注意缓存用RSI12，新的用RSI14）
    print(f"\n▸ RSI 对比:")
    print(f"  注意: 缓存使用RSI12(12日), 重算使用RSI(14日)")
    print(f"  这两个参数不同，所以值会有差异，这是正常的")
    print(f"\n{'日期':<12} {'缓存RSI12':>12} {'重算RSI14':>12}")
    print("-"*50)
    for i in range(-5, 0):
        date = df_cached.iloc[i]['date']
        cached_rsi = df_cached.iloc[i]['RSI12']

        recalc_row = df_recalc[df_recalc['date'] == date]
        if not recalc_row.empty:
            recalc_rsi = recalc_row.iloc[0]['RSI']
            print(f"{str(date)[:10]:<12} {cached_rsi:>12.4f} {recalc_rsi:>12.4f}")

    # 统计一致性
    print(f"\n5. 一致性统计:")
    print("="*70)

    # MA5一致性
    ma5_diffs = []
    for i in range(len(df_cached)):
        date = df_cached.iloc[i]['date']
        cached_ma5 = df_cached.iloc[i]['MA5']
        recalc_row = df_recalc[df_recalc['date'] == date]
        if not recalc_row.empty and not pd.isna(cached_ma5):
            recalc_ma5 = recalc_row.iloc[0]['MA5']
            if not pd.isna(recalc_ma5):
                ma5_diffs.append(abs(cached_ma5 - recalc_ma5))

    if ma5_diffs:
        avg_diff = sum(ma5_diffs) / len(ma5_diffs)
        max_diff = max(ma5_diffs)
        print(f"  MA5 平均差异: {avg_diff:.6f}")
        print(f"  MA5 最大差异: {max_diff:.6f}")
        print(f"  MA5 一致性: {'✓ 完全一致' if max_diff < 0.01 else '✗ 存在差异'}")

    # MACD一致性
    macd_diffs = []
    for i in range(len(df_cached)):
        date = df_cached.iloc[i]['date']
        cached_dif = df_cached.iloc[i]['DIF']
        recalc_row = df_recalc[df_recalc['date'] == date]
        if not recalc_row.empty and not pd.isna(cached_dif):
            recalc_dif = recalc_row.iloc[0]['MACD_DIF']
            if not pd.isna(recalc_dif):
                macd_diffs.append(abs(cached_dif - recalc_dif))

    if macd_diffs:
        avg_diff = sum(macd_diffs) / len(macd_diffs)
        max_diff = max(macd_diffs)
        print(f"\n  MACD DIF 平均差异: {avg_diff:.6f}")
        print(f"  MACD DIF 最大差异: {max_diff:.6f}")
        print(f"  MACD DIF 一致性: {'✓ 完全一致' if max_diff < 0.01 else '✗ 存在差异'}")

    print("\n" + "="*70)
    print("结论:")
    print("  如果差异 < 0.01，说明指标计算逻辑完全一致 ✓")
    print("  如果差异 > 0.01，可能是:")
    print("    1. 计算逻辑不同")
    print("    2. 参数不同（如RSI周期）")
    print("    3. 浮点数精度问题")
    print("="*70)


if __name__ == "__main__":
    main()
