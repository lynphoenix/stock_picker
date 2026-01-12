# -*- coding: utf-8 -*-
"""
科学筛选方法演示

对比两种股票池选择方法：
1. 概念板块方法（有问题）
2. 科学筛选方法（推荐）
"""

import akshare as ak
import pandas as pd

# ===================== 科学筛选标准 =====================
SW_INDUSTRIES = ['计算机应用', '计算机设备', '半导体', '电子', '通信', '软件开发']
AI_KEYWORDS = ['人工智能', 'AI', 'AIGC', '大模型', '机器学习', '深度学习', '云计算', '大数据']

print("="*80)
print("科学筛选方法演示")
print("="*80)

# ===================== 方法1：概念板块（有问题）=====================
print("\n【方法1】概念板块方法（AKShare的'人工智能'概念）")
print("-"*80)

# 获取AI概念板块
ai_concept_stocks = ak.stock_board_concept_cons_em(symbol="人工智能")
print(f"总股票数: {len(ai_concept_stocks)}")
print("\n随机抽样10只股票:")
for _, row in ai_concept_stocks.head(10).iterrows():
    code = row.get('代码', '')
    name = row.get('名称', '')

    # 检查实际行业
    try:
        info = ak.stock_individual_info_em(symbol=code)
        industry = ''
        for _, r in info.iterrows():
            if '行业' in str(r['item']):
                industry = r['value']
                break
        print(f"  {code} {name:10s} - 行业: {industry}")
    except:
        print(f"  {code} {name:10s} - 查询失败")

# ===================== 方法2：科学筛选 =====================
print("\n" + "="*80)
print("【方法2】科学筛选方法（申万行业 + 主营业务关键词）")
print("-"*80)

# 取同样的股票池
codes_to_check = ai_concept_stocks['代码'].head(50).tolist()

step1 = []
step2 = []

for code in codes_to_check:
    try:
        info = ak.stock_individual_info_em(symbol=code)
        if info.empty:
            continue

        name = ''
        industry = ''
        main_business = ''

        for _, row in info.iterrows():
            item = str(row['item'])
            value = str(row['value'])

            if '简称' in item:
                name = value
            elif '行业' in item:
                industry = value
            elif '主营业务' in item:
                main_business = value

        # Step 1: 申万行业筛选
        if any(sw in industry for sw in SW_INDUSTRIES):
            step1.append((code, name, industry))

            # Step 2: 主营业务关键词筛选
            match_count = sum(1 for kw in AI_KEYWORDS if kw in main_business)
            if match_count >= 1 or any(kw in main_business for kw in ['人工智能', 'AI', 'AIGC']):
                step2.append((code, name, industry, main_business[:30]))
    except:
        continue

print(f"\nStep 1 - 申万行业筛选: {len(step1)}只")
for code, name, industry in step1[:10]:
    print(f"  {code} {name:12s} - {industry}")

print(f"\nStep 2 - 主营业务关键词筛选: {len(step2)}只")
for code, name, industry, business in step2[:10]:
    print(f"  {code} {name:12s} - {industry}")

# ===================== 对比总结 =====================
print("\n" + "="*80)
print("对比总结")
print("="*80)
print(f"概念板块方法: {len(ai_concept_stocks)}只股票（包含很多非科技公司）")
print(f"科学筛选方法: {len(step2)}只真正的AI/TMT公司")
print(f"\n科学筛选的优势:")
print("  1. 使用申万行业分类，确保是真正的科技行业")
print("  2. 主营业务关键词验证，确保业务相关")
print("  3. 可重复、可验证的数据驱动方法")
print("  4. 避免徐工机械、人民网等蹭热点的公司")
