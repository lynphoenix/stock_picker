# PyOD 项目技术分析文档

## 1. 项目概述

**项目名称**: PyOD (Python Outlier Detection)
**GitHub**: https://github.com/yzhao062/pyod
**主要语言**: Python
**Star**: 8,500+
**许可证**: GPL-2.0

PyOD 是 **Python 异常检测库**，包含 50+ 种异常检测算法，从传统统计到深度学习。

---

## 2. 项目结构

```
pyod/
├── pyod/                    # 核心代码
│   ├── models/              # 50+ 异常检测算法
│   ├── utils/               # 工具函数
│   ├── test/                # 测试用例
│   └── version.py           # 版本信息
├── examples/                # 示例代码
├── notebooks/               # Jupyter notebooks
└── setup.py                 # 项目配置
```

---

## 3. 核心功能模块

### 3.1 模型模块 (50+ 算法)

| 类别 | 算法 |
|------|------|
| **基于密度** | LOF, KDE, COF, SOD, LOCI |
| **基于距离** | KNN, OCSVM |
| **基于树** | IForest (Isolation Forest), INNE |
| **基于统计** | ECOD, MAD, HBOS, COPOD |
| **基于集成** | Feature Bagging, LSCP, XGBOD, SUOD |
| **基于深度学习** | AutoEncoder, VAE, Deep SVDD, AnoGAN, ALAD, DevNet |

### 3.2 工具模块
- `utility.py` - 通用工具函数
- `stat_models.py` - 统计模型工具
- `data.py` - 数据生成工具
- `auto_model_selector.py` - LLM 驱动的自动模型选择

---

## 4. 技术架构

### 4.1 统一接口设计 (BaseDetector)

```python
class BaseDetector(BaseEstimator, metaclass=abc.ABCMeta):
    # 核心方法
    @abc.abstractmethod
    def fit(self, X, y=None): pass

    @abc.abstractmethod
    def decision_function(self, X): pass

    # 预测方法
    def predict(self, X, return_confidence=False)
    def predict_proba(self, X, method='linear')
```

### 4.2 核心属性
- `decision_scores_` - 异常分数 (越高越异常)
- `threshold_` - 基于 contamination 的阈值
- `labels_` - 二元标签 (0=正常, 1=异常)

### 4.3 依赖
```
numpy >= 1.19
scipy >= 1.5.1
scikit-learn >= 0.22.0
joblib          # 并行处理
numba >= 0.51  # JIT 编译
matplotlib      # 可视化
torch           # 深度学习 (可选)
```

---

## 5. 算法详解

### 5.1 ECOD (Empirical Cumulative Distribution Functions)
```python
# 左尾 ECDF
self.U_l = -1 * np.log(column_ecdf(X))
# 右尾 ECDF
self.U_r = -1 * np.log(column_ecdf(-X))
# 最终异常分数
decision_scores_ = np.maximum(U_l, U_r).sum(axis=1)
```

### 5.2 Isolation Forest
- 随机选择特征和切分点
- 异常点更容易被隔离 (路径更短)
- 平均路径长度作为异常分数

### 5.3 AutoEncoder
- 学习数据的压缩表示
- 重建误差作为异常分数
- 支持 PyTorch GPU 加速

---

## 6. 使用示例

```python
from pyod.models.ecod import ECOD
from pyod.models.iforest import IForest

# 训练
clf = ECOD(contamination=0.1)
clf.fit(X_train)

# 预测
y_train_scores = clf.decision_scores_  # 异常分数
y_pred = clf.predict(X_test)           # 二元标签
```

---

## 7. 技术特点

| 特点 | 说明 |
|------|------|
| **统一API** | 所有算法遵循相同接口 |
| **丰富算法** | 50+ 算法涵盖传统到深度学习 |
| **高性能** | numba JIT + joblib 并行 |
| **易于扩展** | 清晰的基类设计 |
| **LLM集成** | PyOD 2.0 自动模型选择 |

---

## 8. 可借鉴的设计

1. **BaseDetector基类** - 统一的接口设计
2. **算法覆盖** - 从传统统计到深度学习
3. **性能优化** - JIT + 并行处理
4. **contamination参数** - 异常比例控制

---

*文档生成时间: 2026-02-21*
