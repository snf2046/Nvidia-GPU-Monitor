#!/bin/bash
# GPU 监控程序启动脚本

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3"
    exit 1
fi

# 检查是否安装了依赖
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 运行程序
python3 gpu_monitor.py

