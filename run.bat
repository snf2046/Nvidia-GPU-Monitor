@echo off
REM GPU 监控程序启动脚本 (Windows)

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3
    pause
    exit /b 1
)

REM 检查是否安装了依赖
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

REM 运行程序
python gpu_monitor.py

pause

