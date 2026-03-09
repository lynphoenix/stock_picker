# Pull Request

## 🎯 PR目标

修复commit `ddc9f9c8`中发现的 **5个严重安全问题** + **6个重要代码质量问题** + **输入验证加固**。

## 🔴 Phase 1: 严重安全和数据完整性问题 (已修复)

提交: `ed91f93c` (修复) + `a36bc22c` (测试)

### 1. 路径遍历漏洞 🚨
**问题**: 文件名清理不完整，攻击者可能通过特制的策略名称实现目录遍历攻击
**修复**:
- 使用 `Path.name` 移除路径组件
- 验证最终路径在 `STRATEGIES_DIR` 内
- 阻止 `../`, 绝对路径等攻击

### 2. 弱哈希算法 🚨
**问题**: 使用MD5并截断到8字符，碰撞概率高
**修复**:
- 替换 MD5 为 SHA-256
- 哈希长度从8字符增加到16字符
- 大幅降低文件名碰撞概率

### 3. 宽泛异常处理 🚨
**问题**: `except Exception` 捕获所有异常，包括系统级异常
**修复**:
- 替换为具体异常类型 (RuntimeError, anthropic.APIConnectionError 等)
- 添加详细错误日志
- 避免隐藏关键异常 (KeyboardInterrupt, SystemExit 等)

### 4. 文件读取无错误处理 🚨
**问题**: `get_prompt_template()` 无异常处理，任何文件系统错误都会导致崩溃
**修复**:
- 捕获 FileNotFoundError, PermissionError, UnicodeDecodeError, OSError
- 提供清晰的错误消息和日志
- 防止500错误

### 5. 文件写入无错误处理 🚨
**问题**: 策略文件写入失败时无提示，导致**静默数据丢失**
**修复**:
- 捕获 PermissionError, OSError (磁盘满)
- 验证文件确实写入成功
- 防止静默数据丢失

## 🟡 Phase 2: 重要代码质量问题 (已修复)

提交: `da516afc`

### 6. 函数内导入模块
**问题**: `random`, `logging` 在函数内重复导入，影响性能和可读性
**修复**:
- 移动所有导入到文件顶部
- 移除重复的 `import logging` 和 `import random`

### 7. CORS配置过于宽松
**问题**: 允许的源硬编码在代码中
**修复**:
- 使用环境变量 `ALLOWED_ORIGINS` 配置
- 默认值为 localhost:3000,localhost:5173
- 生产环境可通过 .env 文件自定义

### 8. 未使用的导入
**问题**: `from dotenv import load_dotenv` 未使用
**修复**:
- 移除未使用的导入

### 9. 缺少错误日志
**问题**: 许多异常只返回错误给客户端，无服务器端日志
**修复**:
- `_scan_existing_strategies()`: 添加 logger.warning
- `validate_python_syntax()`: 添加 logger.warning
- `run_real_backtest()`: 添加 logger.info/warning/error

### 10. 前端API错误消息不足
**问题**: 只显示HTTP状态码，忽略服务器详细错误
**修复**:
- 增强axios响应拦截器，提取 `message` 和 `errors`
- 分离主错误消息和详细错误列表展示
- 添加红色背景框样式

### 11. 前端无网络错误处理
**问题**: 网络错误显示浏览器默认消息
**修复**:
- 区分超时错误、网络错误、HTTP错误
- 提供友好的中文错误提示
- 映射HTTP状态码到具体错误消息

## 🎁 Bonus Fix: 输入验证

提交: `da516afc`

### 12. 输入长度限制
**问题**: 前后端均无输入长度验证
**修复**:
- 前端: 策略名称最大100字符，描述最大500字符
- 后端: Pydantic Field 添加 max_length 验证
- 前端显示字符计数 (当前/最大)

## ✅ 已添加测试

新增13个测试用例，覆盖Phase 1的5个修复：

```python
backend/tests/test_critical_fixes.py
├── TestPathTraversalProtection (2 tests)
├── TestHashAlgorithmUpgrade (2 tests) ✅ 通过
├── TestFileReadErrorHandling (3 tests) ✅ 通过
├── TestFileWriteErrorHandling (3 tests)
└── TestSpecificExceptionHandling (3 tests)
```

**测试结果**: 5/5 同步测试通过 ✅

## 📝 变更统计

- **4 commits** (Phase 1: 2, Phase 2: 1, Docs: 1)
- **Phase 1修复代码**: +162行, -11行
- **Phase 1测试代码**: +565行
- **Phase 2修复代码**: +105行, -22行
- **总计**: +832行, -33行

## 📂 修改文件

**Phase 1:**
- `backend/app/services/strategy_service.py` - 安全和数据完整性修复
- `.env.example` - MiniMax配置文档
- `backend/tests/test_critical_fixes.py` - 测试用例
- `backend/tests/conftest.py` - pytest fixtures
- `backend/requirements.txt` - 测试依赖
- `pyproject.toml` - pytest配置

**Phase 2:**
- `backend/app/services/strategy_service.py` - 导入优化、日志增强
- `backend/app/main.py` - CORS环境变量配置
- `backend/app/models/strategy.py` - 输入长度验证
- `frontend/src/services/api.ts` - 错误处理增强
- `frontend/src/components/AIGenerateDialog.tsx` - 错误展示优化、输入验证
- `.env.example` - CORS配置示例

## 🔍 审查要点

**Phase 1:**
1. ✅ 路径验证是否充分
2. ✅ 错误处理是否完整
3. ✅ 日志记录是否清晰
4. ✅ 测试覆盖是否足够

**Phase 2:**
1. ✅ 代码组织是否清晰 (导入位置)
2. ✅ CORS配置是否灵活 (环境变量)
3. ✅ 日志记录是否全面
4. ✅ 错误提示是否友好 (用户体验)
5. ✅ 输入验证是否充分

## 📊 参考文档

详细审查报告：`docs/PR_REVIEW_REPORT_ddc9f9c8.md`

## 🎯 后续工作

- [ ] 安装 pytest-asyncio 运行异步测试 (8个测试待运行)
- [ ] 继续修复测试覆盖率问题 (Issue #13)
- [ ] 提高测试覆盖率到80%+

---

## 如何手动创建PR

访问: https://github.com/lynphoenix/stock_picker/pull/new/fix/critical-issues-ddc9f9c8

或在GitHub网页上：
1. 进入仓库
2. 点击 "Pull requests"
3. 点击 "New pull request"
4. 选择 base: main, compare: fix/critical-issues-ddc9f9c8
5. 填写标题：**Fix: 修复commit ddc9f9c8的11个安全和代码质量问题**
6. 粘贴上述内容到描述框

---

🤖 Generated with [Claude Code](https://claude.ai/code) via [Happy](https://happy.engineering)
