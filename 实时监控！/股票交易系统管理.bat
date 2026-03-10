@echo off
title 股票交易系统管理工具
chcp 65001 >nul

echo ========================================
echo    股票组合模拟交易系统管理工具
echo ========================================
echo.
echo 1. 启动系统
echo 2. 停止系统  
echo 3. 重启系统
echo 4. 查看状态
echo 5. 查看日志
echo 6. 打开网页
echo 7. 退出
echo.
set /p choice=请选择操作 (1-7): 

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto status
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto open_web
if "%choice%"=="7" goto exit
goto menu

:start
echo.
echo 正在启动股票交易系统...
wsl "/home/openclaw/.openclaw/workspace/★★模拟交易测试/manage_trading.sh" start
echo.
echo 启动完成！按任意键返回菜单...
pause >nul
goto menu

:stop
echo.
echo 正在停止股票交易系统...
wsl "/home/openclaw/.openclaw/workspace/★★模拟交易测试/manage_trading.sh" stop
echo.
echo 停止完成！按任意键返回菜单...
pause >nul
goto menu

:restart
echo.
echo 正在重启股票交易系统...
wsl "/home/openclaw/.openclaw/workspace/★★模拟交易测试/manage_trading.sh" restart
echo.
echo 重启完成！按任意键返回菜单...
pause >nul
goto menu

:status
echo.
echo 系统状态：
wsl "/home/openclaw/.openclaw/workspace/★★模拟交易测试/manage_trading.sh" status
echo.
echo 按任意键返回菜单...
pause >nul
goto menu

:logs
echo.
echo 最近日志：
wsl "/home/openclaw/.openclaw/workspace/★★模拟交易测试/manage_trading.sh" logs
echo.
echo 按任意键返回菜单...
pause >nul
goto menu

:open_web
echo.
echo 正在打开网页...
start http://localhost:5002
echo.
echo 按任意键返回菜单...
pause >nul
goto menu

:exit
echo.
echo 感谢使用！
exit /b 0

:menu
cls
goto :eof
