# 股票交易系统管理工具

## 📋 功能说明

已为你创建了简便的自动运行脚本管理工具：

### 🚀 Linux管理脚本 (`manage_trading.sh`)
- **启动系统**: `./manage_trading.sh start`
- **停止系统**: `./manage_trading.sh stop`  
- **重启系统**: `./manage_trading.sh restart`
- **查看状态**: `./manage_trading.sh status`
- **查看日志**: `./manage_trading.sh logs`
- **开机自启**: `./manage_trading.sh autostart`

### 🖥️ Windows管理界面 (`股票交易系统管理.bat`)
双击运行即可在Windows环境下管理WSL中的交易系统

## 🎯 使用方法

### 方法1: Windows批处理文件 (推荐)
1. 双击 `股票交易系统管理.bat`
2. 选择对应操作即可

### 方法2: WSL命令行
```bash
# 进入目录
cd "/home/openclaw/.openclaw/workspace/★★模拟交易测试"

# 启动系统
./manage_trading.sh start

# 查看状态
./manage_trading.sh status

# 停止系统
./manage_trading.sh stop
```

## ✨ 特性

- **一键启动**: 自动启动Python脚本并后台运行
- **状态监控**: 实时查看系统运行状态和端口监听情况
- **日志管理**: 自动记录启动和运行日志
- **进程管理**: 自动处理PID文件，防止重复启动
- **开机自启**: 可设置开机自动启动 (需要用户登录)
- **安全停止**: 优雅停止进程，避免数据丢失

## 🔧 系统已启动

当前系统状态:
- ✅ **运行中**: PID 6482
- 🌐 **访问地址**: http://localhost:5002
- 📝 **日志文件**: `/home/openclaw/.openclaw/workspace/★★模拟交易测试/trading_system.log`

## 📱 日常使用建议

1. **每天使用**: 双击 `股票交易系统管理.bat` → 选择"启动系统"
2. **查看状态**: 选择"查看状态"确认系统正常运行
3. **打开网页**: 选择"打开网页"或直接访问 http://localhost:5002
4. **停止系统**: 不使用时选择"停止系统"释放资源

现在你可以通过简单的图形界面管理股票交易系统了！
