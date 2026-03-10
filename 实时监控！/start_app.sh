#!/bin/bash

# 股票组合模拟交易启动脚本
echo "正在启动股票组合模拟交易 Web服务..."

# 检查端口5006是否被占用
if lsof -Pi :5006 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "端口5006已被占用，正在尝试停止现有进程..."
    pkill -f "股票组合模拟交易_同花顺实时.py"
    sleep 2
fi

# 切换到应用目录
cd "/home/openclaw/.openclaw/workspace/实时监控！"

# 启动应用
echo "启动应用..."
python3 "股票组合模拟交易_同花顺实时.py"

echo "应用已停止"
