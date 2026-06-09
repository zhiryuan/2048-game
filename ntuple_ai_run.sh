#!/bin/bash
cd "$(dirname "$0")/cpp_ai"

echo "=== 2048 AI Launcher ==="

# 等待游戏启动
SOCK="/tmp/2048game.sock"
if [ ! -S "$SOCK" ]; then
    echo "Waiting for game at $SOCK ..."
    while [ ! -S "$SOCK" ]; do sleep 0.5; done
fi

echo "Starting AI (depth=2, 256MB TT)..."
./2048_ai play --depth 2 --tt-size 256 --load cpp_ai_15min.bin
