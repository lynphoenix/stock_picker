#!/bin/bash

# 智能投研助手系统 - 环境初始化脚本
# AI Investment Assistant System - Environment Setup Script

set -e  # 遇到错误立即退出

echo "================================"
echo "智能投研助手系统 - 环境初始化"
echo "AI Investment Assistant - Setup"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装
echo -e "${YELLOW}检查依赖...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装。请先安装 Docker。${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装。请先安装 Docker Compose。${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 已安装${NC}"

# 检查 Python 版本
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION 已安装${NC}"
else
    echo -e "${YELLOW}警告: Python3 未找到。某些功能可能需要 Python。${NC}"
fi

# 检查 Node.js 版本
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION 已安装${NC}"
else
    echo -e "${YELLOW}警告: Node.js 未找到。前端开发需要 Node.js。${NC}"
fi

echo ""
echo -e "${YELLOW}创建环境配置文件...${NC}"

# 创建 .env 文件（如果不存在）
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# 数据库配置
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=investment_assistant
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_password

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# 后端配置
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8888
BACKEND_DEBUG=true

# 前端配置
FRONTEND_PORT=3000

# API Keys (需要用户配置)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
TUSHARE_TOKEN=your_tushare_token_here

# JWT 配置
JWT_SECRET=your_jwt_secret_here_change_in_production

# CORS 配置
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# 日志配置
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
    echo -e "${YELLOW}  请编辑 .env 文件并填入您的 API Keys${NC}"
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi

echo ""
echo -e "${YELLOW}启动 Docker 服务...${NC}"

# 启动 Docker Compose 服务
docker-compose up -d postgres redis

echo -e "${GREEN}✓ Docker 服务已启动${NC}"

# 等待数据库就绪
echo ""
echo -e "${YELLOW}等待数据库就绪...${NC}"
sleep 5

# 检查服务状态
echo ""
echo -e "${YELLOW}检查服务状态...${NC}"
docker-compose ps

echo ""
echo "================================"
echo -e "${GREEN}环境初始化完成！${NC}"
echo "================================"
echo ""
echo "下一步操作："
echo ""
echo "1. 配置 API Keys:"
echo "   编辑 .env 文件，填入以下配置："
echo "   - DEEPSEEK_API_KEY"
echo "   - TUSHARE_TOKEN"
echo ""
echo "2. 安装后端依赖:"
echo "   cd backend && pip install -r requirements.txt"
echo ""
echo "3. 安装前端依赖:"
echo "   cd frontend && npm install"
echo ""
echo "4. 初始化数据库:"
echo "   cd backend && python scripts/init_db.py"
echo ""
echo "5. 启动开发服务器:"
echo "   后端: cd backend && uvicorn main:app --reload --port 8888"
echo "   前端: cd frontend && npm run dev"
echo ""
echo "6. 访问应用:"
echo "   前端: http://localhost:3000"
echo "   后端 API: http://localhost:8888"
echo "   API 文档: http://localhost:8888/docs"
echo ""
echo "管理命令:"
echo "   停止服务: docker-compose down"
echo "   查看日志: docker-compose logs -f"
echo "   重启服务: docker-compose restart"
echo ""
