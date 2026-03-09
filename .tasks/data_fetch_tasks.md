# 数据采集模块开发任务列表
# 每个 task 是 Claude Code 一次调用的工作单元

## Task 1: 代码重构 - 整合散落的数据采集代码
- 整理散落在 src/ 和 core/data/ 的数据采集相关代码
- 将 src/data_source_manager.py 集成到 core/data/ 流程
- 将 src/sqlite_cache_manager.py 集成到 core/data/ 流程
- 清理重复代码，确保单一职责
- 整理 import 路径

## Task 2: 完善 AutoDataFetcher 采集核心
- 实现 should_fetch_today() 方法（判断交易日）
- 实现 get_stock_list() 方法（获取股票列表）
- 实现 is_cache_valid() 方法（检查缓存）
- 实现 fetch_daily_data() 主方法框架
- 实现 _fetch_with_retry() 重试逻辑

## Task 3: 测试 Baostock 单股票采集
- 测试 baostock 登录/登出
- 测试单只股票历史数据采集
- 验证数据格式正确
- 修复发现的问题

## Task 4: 启用 SQLiteCacheManager
- 配置 SQLiteCacheManager 替代 JSON 缓存
- 实现缓存读写逻辑
- 测试缓存有效性检查
- 验证增量采集跳过逻辑

## Task 5: 启用 CircuitBreaker 熔断器
- 集成 DataSourceCircuitBreaker
- 测试熔断触发（连续失败）
- 测试熔断恢复（连续成功）
- 验证多源 fallback 逻辑

## Task 6: 完善后端 API
- 完善 /api/data/fetch-now 接口
- 实现 /api/data/fetch/status 接口
- 实现 /api/data/fetch/stats 接口
- 添加任务状态管理

## Task 7: 前端采集控制面板
- 创建 FetchControlPanel 组件
- 集成到 DataMonitoring 页面
- 实现进度条展示
- 实现统计卡片

## Task 8: 集成测试
- 测试 API 触发采集
- 测试增量采集逻辑
- 测试采集统计正确性
- 修复发现的问题

## Task 9: E2E 测试
- 手动采集流程测试
- 进度显示测试
- 错误处理测试
- 验收确认

## Task 10: 全量采集测试
- 触发全量 5000+ 股票采集
- 监控采集进度
- 解决采集问题
- 最终验收

## Task 11: 代码整理和提交
- 代码审查和优化
- 编写测试用例
- Git commit 提交
- 更新文档
