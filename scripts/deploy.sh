#!/bin/bash

# 1. 进入项目根目录
cd "$(dirname "$0")/.."

# 2. 拉取最新代码
# echo "🚀 拉取最新代码..."
# git pull || { echo "❌ git pull 失败，请检查网络或权限"; exit 1; }

# 3. 构建 Docker 镜像
echo "🔨 构建 Docker 镜像..."
docker compose build || { echo "❌ Docker 构建失败"; exit 1; }

# 4. 启动/重启服务
echo "�� 启动/重启服务..."
docker compose up -d || { echo "❌ Docker 启动失败"; exit 1; }

# 5. 健康检查函数
check_health() {
  local service=$1
  local port=$2
  local retries=10
  local wait=2
  echo "⏳ 检查 $service 健康状态 (端口 $port)..."
  for ((i=1; i<=retries; i++)); do
    status=$(curl -s "http://localhost:$port/health" | grep -o '"status": *"ok"')
    if [[ $status == '"status": "ok"' ]]; then
      echo "✅ $service 健康检查通过"
      return 0
    fi
    sleep $wait
  done
  echo "❌ $service 健康检查失败"
  return 1
}

# 6. 检查 doc_service 和 ocr_service 健康
check_health "doc_service" 4000 || exit 1
check_health "ocr_service" 4001 || exit 1

# 7. 显示服务状态
echo "📋 当前服务状态："
docker compose ps

# 8. 日志收集与输出（可选：只显示最近100行）
echo "📑 doc_service 日志（最近100行）："
docker compose logs --tail=100 doc_service

echo "📑 ocr_service 日志（最近100行）："
docker compose logs --tail=100 ocr_service

echo "🎉 部署完成！所有服务已启动并通过健康检查。"
