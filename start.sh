#!/usr/bin/env bash
set -e

# 学生票 Agent — 一键启动脚本（Linux / macOS）
# 用法: ./start.sh [port]
# 默认端口: 8080

PORT="${1:-8080}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  学生票 Agent — 启动中..."
echo "============================================"
echo "工作目录: $DIR"
echo "端口:     $PORT"
echo ""

cd "$DIR"

# 检查依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "[*] 正在安装依赖..."
    pip3 install -r requirements.txt
fi

echo "[*] 启动 Web 服务: http://localhost:${PORT}"
echo ""

exec python3 -m uvicorn src.web_app:app --host 0.0.0.0 --port "${PORT}" --reload
