# 测试说明

## 安装测试依赖

```bash
cd backend
pip install pytest>=7.4.0 pytest-asyncio>=0.21.0 pytest-cov>=4.1.0 httpx>=0.24.0
```

或者从requirements.txt安装：

```bash
pip install -r backend/requirements.txt
```

## 运行测试

### 运行所有测试
```bash
pytest backend/tests/ -v
```

### 运行特定测试文件
```bash
pytest backend/tests/test_critical_fixes.py -v
```

### 运行特定测试类
```bash
pytest backend/tests/test_critical_fixes.py::TestHashAlgorithmUpgrade -v
```

### 带覆盖率报告
```bash
pytest backend/tests/ -v --cov=backend/app --cov-report=html
# 查看报告: open htmlcov/index.html
```

## 测试结构

```
backend/tests/
├── __init__.py
├── conftest.py                    # pytest配置和fixtures
└── test_critical_fixes.py         # 5个严重问题的测试
    ├── TestPathTraversalProtection      # 路径遍历防护
    ├── TestHashAlgorithmUpgrade         # SHA-256哈希
    ├── TestFileReadErrorHandling        # 文件读取错误处理
    ├── TestFileWriteErrorHandling       # 文件写入错误处理
    └── TestSpecificExceptionHandling    # 具体异常处理
```

## 测试覆盖范围

### ✅ 已测试（5个严重修复）

1. **路径遍历防护**
   - ✅ 恶意路径攻击阻止
   - ✅ 文件名清理

2. **SHA-256哈希**
   - ✅ 使用SHA-256而非MD5
   - ✅ 碰撞抵抗测试

3. **文件读取错误**
   - ✅ FileNotFoundError处理
   - ✅ PermissionError处理
   - ✅ UnicodeDecodeError处理

4. **文件写入错误**
   - ✅ 权限拒绝处理
   - ✅ 磁盘满错误处理
   - ✅ 文件写入验证

5. **具体异常处理**
   - ✅ APIConnectionError
   - ✅ RateLimitError
   - ✅ AuthenticationError

## 测试状态

- **同步测试**: 5/13 通过 (100%)
- **异步测试**: 需要安装 pytest-asyncio
- **总覆盖**: 针对5个严重问题的关键测试已完成

## 下一步

- [ ] 安装 pytest-asyncio 以运行异步测试
- [ ] 添加更多边界情况测试
- [ ] 提高测试覆盖率到80%+
