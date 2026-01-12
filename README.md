# A股智能选股系统

基于Python的A股智能选股系统，采用科学筛选方法，结合基本面分析、技术指标和回测验证。

## 核心特性

### 科学股票池筛选
- **申万行业分类**：使用标准A股行业分类，剔除蹭热点的非科技公司
- **基本面评分**：ROE、营收增速、利润增速、市盈率多维度评分
- **市值过滤**：剔除小盘股，降低流动性风险
- **缓存机制**：高效批量查询，避免重复API调用

### 技术分析
- **技术指标**：MACD、RSI、MA、成交量比率等
- **买卖信号**：综合多维度信号评分
- **风险控制**：止损、止盈、移动止损策略

### 回测系统
- **历史回测**：验证策略有效性
- **风险指标**：收益率、胜率、最大回撤、盈亏比
- **策略优化**：多版本策略迭代

## 项目结构

```
stock_picker/
├── data/
│   └── stock_pools.json      # 科学筛选的股票池
├── src/
│   ├── data_fetcher.py       # AKShare数据获取
│   ├── fundamentals.py       # 基本面筛选
│   ├── sector_heat.py        # 板块热度分析
│   ├── technical.py          # 技术指标计算
│   ├── signal_engine.py      # 买卖信号引擎
│   ├── stock_screener.py     # 原始筛选器
│   ├── optimized_screener.py # 优化筛选器（带缓存）
│   └── notifier.py           # 微信通知
├── ui/
│   └── app.py                # Streamlit Web界面
├── archive/                  # 历史版本归档
├── config.py                 # 配置文件
├── main.py                   # 主程序入口
├── backtest.py               # 回测引擎（V4最新版）
└── requirements.txt          # 依赖包
```

## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/stock-picker.git
cd stock-picker

# 安装依赖
pip install -r requirements.txt
```

### 依赖包

- `akshare` - A股数据获取
- `pandas` - 数据处理
- `numpy` - 数值计算
- `streamlit` - Web界面
- `requests` - HTTP请求
- `tqdm` - 进度条显示

## 使用方法

### 1. 生成科学股票池

```bash
# 运行优化筛选器（首次运行会建立缓存）
python src/optimized_screener.py
```

筛选标准：
- 概念板块 → 申万科技行业 → 市值>30亿 → 基本面评分

当前股票池：
- **AI软件**：30只（从680只AI概念股筛选）
- **机器人**：7只（从84只工业母机概念股筛选）

### 2. 运行回测

```bash
# 使用科学股票池回测
python backtest.py
```

回测策略（V4）：
- 买入阈值：55分
- 仓位管理：每只10%，最多5只
- 止损：-10%
- 移动止损：从高点回落4%
- 分批止盈：+8%卖出1/3，+18%再卖出1/3

### 3. 命令行选股

```bash
# 测试系统
python main.py --test

# 完整选股流程
python main.py

# 选股并发送微信通知
python main.py --notify

# 查看板块热度
python main.py --heat
```

### 4. Web界面

```bash
python main.py --web
# 或
streamlit run ui/app.py
```

访问 http://localhost:8501

## 配置

### 微信通知（可选）

编辑 `config.py`：

```python
SERVERCHAN_SENDKEY = "你的SendKey"
```

获取SendKey：https://sct.ftqq.com/

### 基本面筛选参数

```python
FUNDAMENTAL_FILTERS = {
    "roe_min": 8.0,              # ROE最小值(%)
    "pe_max": 50,                # 市盈率最大值
    "revenue_growth_min": 5.0,   # 营收增速最小值(%)
    "profit_growth_min": 5.0,    # 利润增速最小值(%)
}
```

### 股票池配置

`data/stock_pools.json` 存储科学筛选的股票池：

```json
{
  "AI软件": ["688256", "300689", ...],
  "机器人": ["000988", "300124", ...]
}
```

## 回测结果示例

```
============================================================
Backtest V4 Results
============================================================
Initial Capital:    100,000.00 CNY
Final Capital:      111,570.00 CNY
Total Return:           11.57%
Total Trades:               59
Win Rate:               33.90%
Profit Factor:           2.19
Max Drawdown:           38.89%

Best Trade: 华工科技(000988) +53.01%
Worst Trade: -9.55%
```

## 技术指标说明

### 买入信号
- MACD金叉（30分）
- RSI未超买/超卖反弹（15分）
- 均线多头排列（20分）
- 成交量放大（15分）
- 价格接近支撑均线（10分）

### 卖出信号
- 硬止损：-10%
- 移动止损：从高点回落4%
- 分批止盈：+8%、+18%
- 技术面恶化：MACD死叉、跌破均线

## 数据来源

- **行情数据**：AKShare（东方财经数据接口）
- **行业分类**：申万行业分级标准
- **财务数据**：东方财富财务数据

## 注意事项

1. **风险提示**：本系统仅供学习研究，不构成投资建议
2. **数据时效**：历史数据可能存在延迟，实际使用需注意
3. **策略风险**：历史表现不代表未来收益
4. **股市有风险**：投资需谨慎，建议结合自身判断

## 版本历史

### V4 - 科学筛选版本
- 引入申万行业分类
- 优化股票池筛选逻辑
- 添加缓存机制提高性能
- 改进风险控制和仓位管理

### V3 - 基本面优化
- 增强基本面筛选
- 添加板块热度分析

### V2 - 技术信号引擎
- MACD、RSI等技术指标
- 综合信号评分系统

### V1 - 初始版本
- 基本面筛选
- 简单技术分析

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题或建议，欢迎讨论。
