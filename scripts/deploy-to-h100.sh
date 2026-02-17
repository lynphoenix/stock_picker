#!/bin/bash
# 部署脚本 - 本地到XW-H100服务器同步
# 使用方法: ./scripts/deploy-to-h100.sh

set -e

# 配置 (XW-H100服务器)
H100_SERVER="61.175.246.236"
H100_USER="root"
H100_PORT="22"
H100_PROJECT_DIR="/root/stock_picker"
H100_CONDA_ENV="/root/miniforge3/envs/stock_picker"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}============================================${NC}"
echo -e "${YELLOW}  智能投研助手 - 部署到XW-H100服务器${NC}"
echo -e "${YELLOW}============================================${NC}"
echo -e "服务器: ${H100_SERVER}"
echo -e "用户: ${H100_USER}"
echo -e "SSH端口: ${H100_PORT}"
echo ""

# 1. 检查本地代码
echo -e "${GREEN}[1/5]${NC} 检查本地代码..."
if [ ! -f "app_spec.txt" ]; then
    echo -e "${RED}错误: app_spec.txt 不存在${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} 本地代码检查通过"

# 2. 测试SSH连接
echo -e "\n${GREEN}[2/5]${NC} 测试SSH连接..."
if ssh -p ${H100_PORT} ${H100_USER}@${H100_SERVER} "echo '连接成功'" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} SSH连接正常"
else
    echo -e "${RED}✗${NC} SSH连接失败"
    echo -e "${YELLOW}尝试使用SSH config: ssh XW-H100${NC}"
    exit 1
fi

# 3. 创建服务器目录
echo -e "\n${GREEN}[3/5]${NC} 创建服务器项目目录..."
ssh -p ${H100_PORT} ${H100_USER}@${H100_SERVER} "mkdir -p ${H100_PROJECT_DIR}/{backend,frontend,data,logs,scripts}"
echo -e "${GREEN}✓${NC} 服务器目录已创建: ${H100_PROJECT_DIR}"

# 4. 同步代码
echo -e "\n${GREEN}[4/5]${NC} 同步代码到服务器..."
echo -e "${YELLOW}同步内容:${NC}"
echo "  - 后端代码 (backend/)"
echo "  - 前端代码 (frontend/)"
echo "  - 配置文件 (config.py, requirements.txt, docker-compose.yml)"
echo "  - 脚本文件 (scripts/)"

# 同步后端
echo -e "${YELLOW}同步后端...${NC}"
rsync -avz --progress \
  -e "ssh -p ${H100_PORT}" \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='*.db' \
  --exclude='.venv' \
  --exclude='node_modules' \
  backend/ ${H100_USER}@${H100_SERVER}:${H100_PROJECT_DIR}/backend/ 2>&1 | grep -v "file..." || true

# 同步前端
echo -e "${YELLOW}同步前端...${NC}"
rsync -avz --progress \
  -e "ssh -p ${H100_PORT}" \
  --exclude='node_modules' \
  --exclude='dist' \
  --exclude='.next' \
  frontend/ ${H100_USER}@${H100_SERVER}:${H100_PROJECT_DIR}/frontend/ 2>&1 | grep -v "file..." || true

# 同步根目录文件
echo -e "${YELLOW}同步配置文件...${NC}"
rsync -avz \
  -e "ssh -p ${H100_PORT}" \
  config.py requirements.txt docker-compose.yml app_spec.txt docs/ \
  ${H100_USER}@${H100_SERVER}:${H100_PROJECT_DIR}/ 2>&1 | grep -v "file..." || true

echo -e "${GREEN}✓${NC} 代码同步完成"

# 5. 安装依赖
echo -e "\n${GREEN}[5/6]${NC} 安装服务器依赖..."
ssh -p ${H100_PORT} ${H100_USER}@${H100_SERVER} << 'ENDSSH'
cd ${H100_PROJECT_DIR}

# 检查conda环境
if [ -f "/root/miniforge3/bin/activate" ]; then
    echo "使用miniforge3环境"
    source /root/miniforge3/bin/activate stock_picker
elif [ -f "/root/anaconda3/bin/activate" ]; then
    echo "使用anaconda3环境"
    source /root/anaconda3/bin/activate stock_picker
else
    echo "创建新的conda环境"
    conda create -n stock_picker python=3.10 -y
    source ~/miniforge3/bin/activate stock_picker
fi

# 安装Python依赖
echo "安装Python依赖..."
pip install -r requirements.txt -q

# 安装前端依赖
echo "安装前端依赖..."
cd frontend && npm install && cd ..
ENDSSH

echo -e "${GREEN}✓${NC} 依赖安装完成"

# 6. 启动服务
echo -e "\n${GREEN}[6/7]${NC} 启动服务..."
ssh -p ${H100_PORT} ${H100_USER}@${H100_SERVER} << 'ENDSSH'
cd ${H100_PROJECT_DIR}

# 激活环境
source ~/miniforge3/bin/activate stock_picker || source /root/miniforge3/bin/activate stock_picker

# 停止旧服务
pkill -f "uvicorn backend.app.main:app" || true

# 启动新服务
echo "启动后端API服务..."
nohup python -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8888 \
  > logs/backend.log 2>&1 &

echo "服务已启动，PID: $!"
sleep 2

# 检查服务状态
if curl -s http://localhost:8888/health > /dev/null; then
    echo "✓ 后端服务启动成功"
else
    echo "✗ 后端服务启动失败，检查日志"
    tail -20 logs/backend.log
fi
ENDSSH

echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "后端API: http://${H100_SERVER}:8888"
echo -e "API文档: http://${H100_SERVER}:8888/docs"
echo -e "SSH登录: ssh ${H100_USER}@${H100_SERVER} (或使用: ssh XW-H100)"
echo ""
echo -e "${YELLOW}常用命令:${NC}"
echo -e "  查看日志: ssh XW-H100 'tail -f ${H100_PROJECT_DIR}/logs/backend.log'"
echo -e "  重启服务: ssh XW-H100 'cd ${H100_PROJECT_DIR} && ./scripts/restart.sh'"
echo -e "  同步代码: ./scripts/deploy-to-h100.sh"
