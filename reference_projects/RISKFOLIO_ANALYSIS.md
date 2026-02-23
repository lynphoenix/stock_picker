# Riskfolio-Lib 项目技术分析文档

## 1. 项目概述

**项目名称**: Riskfolio-Lib
**GitHub**: https://github.com/danielfoechkn/Riskfolio-Lib
**主要语言**: Python
**Star**: 3,500+
**许可证**: MIT

Riskfolio-Lib 是**现代投资组合优化库**，支持均值-方差、风险平价、Black-Litterman等多种优化方法。

---

## 2. 项目结构

```
Riskfolio-Lib/
├── riskfolio/               # 核心包
│   ├── src/                # 源代码
│   │   ├── Portfolio.py    # 组合优化主类
│   │   ├── RiskFunctions.py  # 风险函数
│   │   ├── HierarchicalRiskParity.py  # HRP
│   │   ├── BlackLitterman.py  # BL模型
│   │   └── ...
│   ├── tests/              # 测试
│   └── notebooks/          # Jupyter教程
├── docs/                    # 文档
└── setup.py                # 项目配置
```

---

## 3. 核心功能模块

### 3.1 优化模型
- **均值-方差优化 (Mean-Variance)**
- **最小方差组合 (Minimum Variance)**
- **最大夏普组合 (Maximum Sharpe)**
- **风险平价 (Risk Parity)**
- **层次风险平价 (HRP)**
- **Black-Litterman (BL)**
- **均值-CVaR (Mean-CVaR)**
- **梯度优化 (Gradient)**

### 3.2 风险度量
- **MV** - 均值-方差
- **CVaR** - 条件风险价值
- **CDaR** - 条件下行风险
- **MDD** - 最大回撤
- **EVaR** - 熵风险价值
- **UL** - 溃疡指数

### 3.3 约束条件
- 权重上下限
- 行业/板块中性
- 因子暴露
- 交易成本

---

## 4. 技术架构

### 4.1 核心技术栈
```
CVXPY           # 凸优化求解器
scipy.optimize  # 数值优化
scikit-learn    # 协方差估计
pandas          # 数据处理
numpy           # 数值计算
```

### 4.2 优化器实现
```python
import riskfolio as rp

# 构建组合
port = rp.Portfolio(returns=returns_df)
port.assets_stats(method='hist')

# 均值-方差优化
weights_mv = port.optimization(
    model='Classic',
    rm='MV',  # Mean-Variance
    obj='Sharpe',
    hist=True
)

# 风险平价
weights_rp = port.optimization(
    model='Classic',
    rm='CVaR',
    obj='MinRisk'
)

# 层次风险平价
weights_hrp = port.optimization(
    model='HRP',
    codependence='pearson',
    linkage='ward'
)
```

---

## 5. 核心算法

### 5.1 均值-方差优化 (Markowitz)
```python
# 目标: 最小化 w^T Σ w
# 约束: w^T μ = r, w^T 1 = 1
minimize: w^T Σ w
subject to: w^T μ = target_return
            sum(w) = 1
            w_i >= 0 (可选)
```

### 5.2 层次风险平价 (HRP)
1. 计算资产距离矩阵
2. 使用层次聚类 (ward linkage)
3. 递归分配风险权重

### 5.3 Black-Litterman
1. 市值加权作为先验
2. 融合主观观点
3. 后验期望收益

---

## 6. 使用示例

```python
import riskfolio as rp

# 1. 构建组合
port = rp.Portfolio(returns=returns_df)

# 2. 设置参数
port.assets_stats(method_mu='hist', method_cov='hist')

# 3. 优化
weights = port.optimization(
    model='Classic',
    rm='CVaR',
    obj='Sharpe',
    rf=0,
    hist=True
)

# 4. 可视化有效前沿
rp.plot_frontier(port)
```

---

## 7. 技术特点

| 特点 | 说明 |
|------|------|
| **算法丰富** | 10+ 种优化模型 |
| **约束灵活** | 支持复杂约束条件 |
| **学术级实现** | 符合现代投资组合理论 |
| **可视化** | 有效前沿、权重图表 |
| **快速开发** | 一行代码完成优化 |

---

## 8. 可借鉴的设计

1. **Portfolio类** - 统一的组合构建接口
2. **优化模型** - 多种优化目标
3. **风险度量** - CVaR/CDaR等高级度量
4. **约束系统** - 灵活的约束配置

---

*文档生成时间: 2026-02-21*
