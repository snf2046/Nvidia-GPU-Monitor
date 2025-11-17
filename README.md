# WatchGPU - GPU Monitor Desktop Widget

# WatchGPU - GPU 监控桌面小组件

A lightweight, real-time GPU monitoring desktop widget built with PyQt6, providing an elegant and informative display of GPU status similar to nvitop.

一个轻量级的实时 GPU 监控桌面小组件，基于 PyQt6 构建，提供优雅且信息丰富的 GPU 状态显示，功能类似 nvitop。

---

## Features / 功能特性

### Core Features / 核心功能

- **Real-time GPU Monitoring / 实时 GPU 监控**
  - GPU utilization / GPU 利用率
  - VRAM usage / 显存使用情况
  - Temperature / 温度
  - Power consumption / 功耗
  - Fan speeds / 风扇转速

- **Multi-GPU Support / 多 GPU 支持**
  - Automatically detects and displays all available GPUs / 自动检测并显示所有可用 GPU
  - Horizontal scrolling layout for multiple cards / 横向滚动布局支持多张卡片

- **Smart Visual Effects / 智能视觉特效**
  - Temperature-triggered rainbow color cycling animation / 温度触发的彩虹色循环动画
  - Animation activates when temperature rises ≥5°C continuously or ≥3°C suddenly / 温度连续上升≥5°C或突然上升≥3°C时启动动画
  - Animation stops when temperature drops ≥5°C continuously or ≥3°C suddenly / 温度连续下降≥5°C或突然下降≥3°C时停止动画
  - Smooth color interpolation for seamless transitions / 平滑颜色插值实现无缝过渡

- **User-Friendly Interface / 用户友好界面**
  - Frameless window design / 无边框窗口设计
  - Auto-hide title bar after 10 seconds / 10秒后自动隐藏标题栏
  - 75% window opacity / 75%窗口透明度
  - Draggable window / 可拖拽窗口
  - Right-click context menu / 右键上下文菜单
  - Detailed tooltips on hover / 悬停显示详细工具提示

- **Memory Monitoring / 内存监控**
  - Displays application's own memory usage / 显示程序自身内存占用
  - Updates every 2 seconds / 每2秒更新一次

- **Color-Coded Indicators / 颜色编码指示器**
  - Green: Low usage (<50%) / 绿色：低使用率（<50%）
  - Orange: Medium usage (50-80%) / 橙色：中等使用率（50-80%）
  - Red: High usage (>80%) / 红色：高使用率（>80%）

---

## System Requirements / 系统要求

### Required / 必需

- **Python 3.8+** / Python 3.8 或更高版本
- **NVIDIA GPU** with NVIDIA drivers installed / 已安装 NVIDIA 驱动的 NVIDIA GPU
- **NVIDIA Management Library (NVML)** / NVIDIA 管理库（NVML）

### Supported Platforms / 支持平台

- **Linux** (tested on Ubuntu/Debian-based distributions) / Linux（已在基于 Ubuntu/Debian 的发行版上测试）
- **Windows** (Windows 10/11) / Windows（Windows 10/11）

---

## Installation / 安装

### 1. Clone or Download / 克隆或下载

```bash
git clone <repository-url>
cd watchGPU
```

或直接下载项目文件。

### 2. Install Dependencies / 安装依赖

#### Linux / Linux

```bash
pip3 install -r requirements.txt
```

#### Windows / Windows

```bash
pip install -r requirements.txt
```

### 3. Optional: Install nvitop for Consistent VRAM Display / 可选：安装 nvitop 以获得一致的显存显示

For consistent VRAM readings with nvitop, install nvitop:

为了与 nvitop 的显存显示保持一致，可以安装 nvitop：

```bash
pip install nvitop
```

The program will automatically use nvitop's API if available, otherwise falls back to standard NVML API.

如果可用，程序会自动使用 nvitop 的 API，否则回退到标准 NVML API。

---

## Usage / 使用方法

### Quick Start / 快速开始

#### Linux / Linux

```bash
chmod +x run.sh
./run.sh
```

Or directly / 或直接运行：

```bash
python3 gpu_monitor.py
```

#### Windows / Windows

Double-click `run.bat` or run in Command Prompt:

双击 `run.bat` 或在命令提示符中运行：

```cmd
run.bat
```

Or directly / 或直接运行：

```cmd
python gpu_monitor.py
```

### Interface Guide / 界面指南

- **GPU Cards / GPU 卡片**: Each card displays GPU name, utilization, VRAM, temperature, and power / 每张卡片显示 GPU 名称、利用率、显存、温度和功耗
- **Progress Bars / 进度条**: Hover over any progress bar to see detailed tooltips / 悬停在任意进度条上可查看详细工具提示
- **Status Bar / 状态栏**: Shows detected GPU count, application memory usage, and last update time / 显示检测到的 GPU 数量、应用程序内存占用和最后更新时间
- **Window Controls / 窗口控制**:
  - **Drag / 拖拽**: Click and drag the window (outside GPU cards) to move / 点击并拖拽窗口（GPU 卡片外）以移动
  - **Close / 关闭**: Right-click (outside GPU cards) and select "关闭程序" / 右键点击（GPU 卡片外）选择"关闭程序"
  - **Title Bar / 标题栏**: Automatically hides after 10 seconds, hover to show / 10秒后自动隐藏，悬停显示

---

## Technical Details / 技术细节

### Dependencies / 依赖项

- **PyQt6** (≥6.5.0): GUI framework / GUI 框架
- **nvidia-ml-py** (≥12.0.0): Python bindings for NVIDIA Management Library / NVIDIA 管理库的 Python 绑定
- **psutil** (≥5.9.0): Process and system monitoring / 进程和系统监控
- **nvitop** (optional): For consistent VRAM readings / 可选，用于一致的显存读数

### Architecture / 架构

- **Main Thread / 主线程**: UI rendering and event handling / UI 渲染和事件处理
- **Monitor Thread / 监控线程**: GPU data collection (runs every 1 second) / GPU 数据收集（每1秒运行一次）
- **Memory Timer / 内存定时器**: Updates application memory usage every 2 seconds / 每2秒更新应用程序内存占用
- **Animation Timer / 动画定时器**: Updates color cycling animation every 20ms / 每20ms更新颜色循环动画

### Key Components / 关键组件

- **GPUInfo**: Data class for GPU information / GPU 信息数据类
- **GPUMonitorThread**: Background thread for GPU monitoring / GPU 监控后台线程
- **GPUCard**: Individual GPU card widget with animation support / 支持动画的单个 GPU 卡片组件
- **GPUMonitorWidget**: Main window widget / 主窗口组件

---

## Features in Detail / 详细功能说明

### Temperature Animation / 温度动画

The rainbow color cycling animation is triggered based on temperature changes:

彩虹色循环动画根据温度变化触发：

- **Start Condition / 启动条件**:
  - Temperature rises ≥5°C from base temperature AND / 温度从基准温度上升≥5°C 且
  - (Continuous rise detected OR sudden increase ≥3°C) / （检测到连续上升或突然上升≥3°C）

- **Stop Condition / 停止条件**:
  - Temperature drops ≥5°C from base temperature AND / 温度从基准温度下降≥5°C 且
  - (Continuous fall detected OR sudden decrease ≥3°C) / （检测到连续下降或突然下降≥3°C）

The animation cycles through 7 rainbow colors (red, orange, yellow, green, cyan, blue, purple) with smooth interpolation.

动画循环显示7种彩虹色（红、橙、黄、绿、青、蓝、紫），并带有平滑插值。

### VRAM Display Consistency / 显存显示一致性

The program prioritizes nvitop's API for VRAM readings to ensure consistency with nvitop's display. If nvitop is not available, it falls back to the standard NVML API.

程序优先使用 nvitop 的 API 读取显存，以确保与 nvitop 的显示一致。如果 nvitop 不可用，则回退到标准 NVML API。

---

## Troubleshooting / 故障排除

### Common Issues / 常见问题

1. **Import Error: Cannot import pynvml / 导入错误：无法导入 pynvml**
   - **Solution / 解决方案**: Install nvidia-ml-py: `pip install nvidia-ml-py` / 安装 nvidia-ml-py：`pip install nvidia-ml-py`

2. **No GPU Detected / 未检测到 GPU**
   - **Solution / 解决方案**: Ensure NVIDIA drivers are installed and NVML is accessible / 确保已安装 NVIDIA 驱动且 NVML 可访问

3. **VRAM Display Inconsistency / 显存显示不一致**
   - **Solution / 解决方案**: Install nvitop for consistent readings: `pip install nvitop` / 安装 nvitop 以获得一致读数：`pip install nvitop`

4. **Window Not Draggable / 窗口无法拖拽**
   - **Solution / 解决方案**: Click and drag outside the GPU cards area / 在 GPU 卡片区域外点击并拖拽

---

## License / 许可证

This project is provided as-is for educational and personal use.

本项目按原样提供，用于教育和个人用途。

---

## Contributing / 贡献

Contributions are welcome! Please feel free to submit issues or pull requests.

欢迎贡献！请随时提交问题或拉取请求。

---

## Acknowledgments / 致谢

- Built with PyQt6 / 基于 PyQt6 构建
- Uses nvidia-ml-py for GPU monitoring / 使用 nvidia-ml-py 进行 GPU 监控
- Inspired by nvitop / 受 nvitop 启发

---

## Version / 版本

Current version: 1.0.0

当前版本：1.0.0

---

## Contact / 联系方式

For issues, questions, or suggestions, please open an issue on the repository.

如有问题、疑问或建议，请在仓库中提交 issue。

