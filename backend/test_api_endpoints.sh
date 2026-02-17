#!/bin/bash
# API端点测试脚本

BASE_URL="http://localhost:8888"

echo "========================================="
echo "  FastAPI 端点测试"
echo "========================================="

echo -e "\n1. 根路径"
curl -s "$BASE_URL/" | python -m json.tool

echo -e "\n\n2. 策略列表 (前2个)"
curl -s "$BASE_URL/api/strategies" | python -m json.tool | head -30

echo -e "\n\n3. 数据总览"
curl -s "$BASE_URL/api/data/overview" | python -m json.tool

echo -e "\n\n4. 股票列表 (科创板前3只)"
curl -s "$BASE_URL/api/data/stocks?market=sh_star&page=1&page_size=3" | python -m json.tool

echo -e "\n\n5. API文档 (Swagger UI)"
echo "访问: $BASE_URL/docs"

echo -e "\n\n========================================="
echo "  测试完成!"
echo "========================================="
