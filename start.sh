#!/bin/sh
# tju-notify 启动脚本
#
# 用法：
#   ./start.sh                 # 启动调度（启动即检查一次，之后每小时检查）
#   ./start.sh --once          # 只检查一次
#   ./start.sh --bootstrap     # 静默灌入历史通知后退出
#   ./start.sh --recent 5      # 查看最新 5 条
set -e

cd "$(dirname "$0")"

# 优先使用项目内的虚拟环境，找不到则退回系统 python
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif command -v uv >/dev/null 2>&1; then
    echo "[start] 使用 uv run"
    exec uv run python main.py "$@"
else
    PYTHON="python3"
fi

echo "[start] 使用解释器: $PYTHON"
exec "$PYTHON" main.py "$@"
