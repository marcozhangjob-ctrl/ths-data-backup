#!/bin/bash
# 股票交易系统启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="/home/openclaw/.openclaw/workspace/★★模拟交易测试"
PYTHON_SCRIPT="股票组合模拟交易_同花顺实时.py"
LOG_FILE="$SCRIPT_DIR/trading_system.log"
PID_FILE="$SCRIPT_DIR/trading_system.pid"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    股票组合模拟交易系统管理工具${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查脚本是否存在
check_script() {
    if [ ! -f "$SCRIPT_DIR/$PYTHON_SCRIPT" ]; then
        echo -e "${RED}错误: 找不到Python脚本 $PYTHON_SCRIPT${NC}"
        echo -e "${RED}请确保脚本位于: $SCRIPT_DIR${NC}"
        exit 1
    fi
}

# 启动服务
start_service() {
    echo -e "${YELLOW}正在启动股票交易系统...${NC}"
    
    # 检查是否已经运行
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}系统已经在运行中 (PID: $PID)${NC}"
            echo -e "${GREEN}访问地址: http://localhost:5002${NC}"
            return
        else
            echo -e "${YELLOW}发现旧的PID文件，正在清理...${NC}"
            rm -f "$PID_FILE"
        fi
    fi
    
    # 启动Python脚本
    cd "$SCRIPT_DIR"
    
    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # 后台启动并记录PID
    nohup python3 "$PYTHON_SCRIPT" > "$LOG_FILE" 2>&1 &
    PID=$!
    
    # 保存PID
    echo $PID > "$PID_FILE"
    
    # 等待一下确认启动成功
    sleep 3
    
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 系统启动成功!${NC}"
        echo -e "${GREEN}  PID: $PID${NC}"
        echo -e "${GREEN}  访问地址: http://localhost:5002${NC}"
        echo -e "${GREEN}  日志文件: $LOG_FILE${NC}"
        echo -e "${YELLOW}  使用 '$0 stop' 可以停止服务${NC}"
        echo -e "${YELLOW}  使用 '$0 status' 可以查看状态${NC}"
        echo -e "${YELLOW}  使用 '$0 logs' 可以查看日志${NC}"
    else
        echo -e "${RED}✗ 系统启动失败!${NC}"
        echo -e "${RED}请检查日志文件: $LOG_FILE${NC}"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# 停止服务
stop_service() {
    echo -e "${YELLOW}正在停止股票交易系统...${NC}"
    
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}系统未运行${NC}"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        sleep 2
        
        # 如果进程还在，强制杀死
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${YELLOW}正在强制停止...${NC}"
            kill -9 $PID
        fi
        
        echo -e "${GREEN}✓ 系统已停止${NC}"
    else
        echo -e "${YELLOW}进程不存在，清理PID文件${NC}"
    fi
    
    rm -f "$PID_FILE"
}

# 查看状态
check_status() {
    echo -e "${BLUE}系统状态:${NC}"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 系统正在运行${NC}"
            echo -e "${GREEN}  PID: $PID${NC}"
            echo -e "${GREEN}  访问地址: http://localhost:5002${NC}"
            echo -e "${GREEN}  运行时间: $(ps -o etime= -p $PID | tr -d ' ')${NC}"
            
            # 检查端口是否监听
            if netstat -tuln 2>/dev/null | grep -q ":5002 "; then
                echo -e "${GREEN}  端口5002正在监听${NC}"
            else
                echo -e "${YELLOW}  警告: 端口5002未监听${NC}"
            fi
        else
            echo -e "${RED}✗ 系统未运行 (PID文件存在但进程不存在)${NC}"
            echo -e "${YELLOW}清理PID文件...${NC}"
            rm -f "$PID_FILE"
        fi
    else
        echo -e "${RED}✗ 系统未运行${NC}"
    fi
}

# 查看日志
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo -e "${BLUE}最近50行日志:${NC}"
        echo -e "${BLUE}----------------------------------------${NC}"
        tail -n 50 "$LOG_FILE"
        echo -e "${BLUE}----------------------------------------${NC}"
        echo -e "${YELLOW}完整日志文件: $LOG_FILE${NC}"
    else
        echo -e "${YELLOW}日志文件不存在${NC}"
    fi
}

# 重启服务
restart_service() {
    echo -e "${YELLOW}正在重启系统...${NC}"
    stop_service
    sleep 2
    start_service
}

# 创建快捷方式
create_shortcuts() {
    echo -e "${YELLOW}创建桌面快捷方式...${NC}"
    
    DESKTOP_DIR="$HOME/Desktop"
    if [ ! -d "$DESKTOP_DIR" ]; then
        DESKTOP_DIR="$HOME/桌面"
    fi
    
    if [ -d "$DESKTOP_DIR" ]; then
        # 创建启动脚本
        cat > "$DESKTOP_DIR/启动股票交易系统.sh" << 'EOF'
#!/bin/bash
/home/openclaw/.openclaw/workspace/★★模拟交易测试/manage_trading.sh start
sleep 2
xdg-open http://localhost:5002 2>/dev/null || echo "请手动打开浏览器访问: http://localhost:5002"
EOF
        chmod +x "$DESKTOP_DIR/启动股票交易系统.sh"
        
        # 创建停止脚本
        cat > "$DESKTOP_DIR/停止股票交易系统.sh" << 'EOF'
#!/bin/bash
/home/openclaw/.openclaw/workspace/★★模拟交易测试/manage_trading.sh stop
EOF
        chmod +x "$DESKTOP_DIR/停止股票交易系统.sh"
        
        echo -e "${GREEN}✓ 桌面快捷方式已创建${NC}"
        echo -e "${GREEN}  启动: $DESKTOP_DIR/启动股票交易系统.sh${NC}"
        echo -e "${GREEN}  停止: $DESKTOP_DIR/停止股票交易系统.sh${NC}"
    else
        echo -e "${YELLOW}未找到桌面目录，跳过快捷方式创建${NC}"
    fi
}

# 开机自启动设置
setup_autostart() {
    echo -e "${YELLOW}设置开机自启动...${NC}"
    
    # 创建systemd服务文件
    SERVICE_FILE="$HOME/.config/systemd/user/trading-system.service"
    
    mkdir -p "$(dirname "$SERVICE_FILE")"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=股票组合模拟交易系统
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 "$SCRIPT_DIR/$PYTHON_SCRIPT"
Restart=always
RestartSec=10
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE

[Install]
WantedBy=default.target
EOF
    
    # 重新加载systemd并启用服务
    systemctl --user daemon-reload
    systemctl --user enable trading-system.service
    
    echo -e "${GREEN}✓ 开机自启动已设置${NC}"
    echo -e "${GREEN}  使用 'systemctl --user start trading-system' 启动${NC}"
    echo -e "${GREEN}  使用 'systemctl --user stop trading-system' 停止${NC}"
    echo -e "${GREEN}  使用 'systemctl --user status trading-system' 查看状态${NC}"
    echo -e "${YELLOW}  注意: 需要用户登录后才会自动启动${NC}"
}

# 显示帮助
show_help() {
    echo -e "${BLUE}用法: $0 [命令]${NC}"
    echo ""
    echo -e "${GREEN}命令:${NC}"
    echo -e "  start     启动股票交易系统"
    echo -e "  stop      停止股票交易系统"
    echo -e "  restart   重启股票交易系统"
    echo -e "  status    查看系统状态"
    echo -e "  logs      查看系统日志"
    echo -e "  shortcuts 创建桌面快捷方式"
    echo -e "  autostart 设置开机自启动"
    echo -e "  help      显示此帮助信息"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo -e "  $0 start      # 启动系统"
    echo -e "  $0 status     # 查看状态"
    echo -e "  $0 stop       # 停止系统"
}

# 主程序
main() {
    check_script
    
    case "${1:-help}" in
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        shortcuts)
            create_shortcuts
            ;;
        autostart)
            setup_autostart
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 运行主程序
main "$@"
