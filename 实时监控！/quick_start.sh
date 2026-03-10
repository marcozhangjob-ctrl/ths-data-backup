#!/bin/bash
# 股票交易系统快捷启动脚本

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 快捷启动股票交易系统${NC}"

# 检查系统是否运行
if ! pgrep -f "股票组合模拟交易_同花顺实时.py" > /dev/null; then
    echo -e "${YELLOW}系统未运行，正在启动...${NC}"
    "/home/openclaw/.openclaw/workspace/★★模拟交易测试/manage_trading.sh" start
    sleep 3
else
    echo -e "${GREEN}✓ 系统已在运行${NC}"
fi

# 打开网页
echo -e "${YELLOW}正在打开网页...${NC}"
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:5002 2>/dev/null &
elif command -v gnome-open > /dev/null; then
    gnome-open http://localhost:5002 2>/dev/null &
else
    echo -e "${YELLOW}请手动打开浏览器访问: http://localhost:5002${NC}"
fi

echo -e "${GREEN}✓ 完成！${NC}"
