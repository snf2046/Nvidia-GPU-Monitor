#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU 监控桌面小组件
基于 PyQt6 和 pynvml 实现类似 nvitop 的功能
"""

import sys
import time
import os
from typing import List
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QProgressBar, QSizePolicy, QMenu, QToolTip
)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, QPoint, QEvent
from PyQt6.QtGui import QFont, QPainter, QColor
# 优先使用 nvidia-ml-py 提供的 pynvml（与 nvitop 一致）
try:
    import pynvml
except ImportError:
    raise ImportError("无法导入 pynvml，请安装 nvidia-ml-py: pip install nvidia-ml-py")

# 尝试导入 nvitop API（可选，用于获取与 nvitop 一致的显存值）
USE_NVITOP_API = False
try:
    from nvitop.api import Device
    USE_NVITOP_API = True
except ImportError:
    # nvitop 未安装，使用标准 pynvml API
    pass


class GPUInfo:
    """GPU 信息数据类"""
    def __init__(self):
        self.index = 0
        self.name = ""
        self.utilization_gpu = 0
        self.utilization_memory = 0
        self.memory_used = 0
        self.memory_total = 0
        self.temperature = 0
        self.power_usage = 0
        self.power_limit = 0
        self.fan_speed = 0  # 单个风扇速度（兼容旧代码）
        self.fan_speeds = []  # 所有风扇速度列表
        self.processes = []


class GPUMonitorThread(QThread):
    """GPU 监控线程"""
    gpu_data_updated = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.update_interval = 1.0  # 1秒更新一次
        
    def run(self):
        """运行监控循环"""
        try:
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            while self.running:
                gpu_list = []
                
                # 如果使用 nvitop API，每次循环都重新获取设备列表以确保数据最新
                nvitop_devices = None
                if USE_NVITOP_API:
                    try:
                        nvitop_devices = Device.all()
                    except:
                        pass
                
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    gpu_info = GPUInfo()
                    gpu_info.index = i
                    
                    # 获取 GPU 名称
                    name = pynvml.nvmlDeviceGetName(handle)
                    gpu_info.name = name.decode('utf-8') if isinstance(name, bytes) else name
                    
                    # 获取利用率
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_info.utilization_gpu = util.gpu
                    gpu_info.utilization_memory = util.memory
                    
                    # 获取VRAM信息
                    # 如果安装了 nvitop，优先使用 nvitop API 以确保与 nvitop 显示一致
                    vram_set = False
                    if USE_NVITOP_API and nvitop_devices is not None and i < len(nvitop_devices):
                        try:
                            device = nvitop_devices[i]
                            mem_info_nvitop = device.memory_info()
                            gpu_info.memory_used = mem_info_nvitop.used // (1024**2)  # MB
                            gpu_info.memory_total = mem_info_nvitop.total // (1024**2)  # MB
                            vram_set = True
                        except:
                            pass  # nvitop API 失败，继续使用标准 API
                    
                    # 如果 nvitop API 未使用或失败，使用标准 API
                    if not vram_set:
                        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        gpu_info.memory_used = mem_info.used // (1024**2)  # MB
                        gpu_info.memory_total = mem_info.total // (1024**2)  # MB
                    
                    # 获取温度
                    try:
                        gpu_info.temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    except:
                        gpu_info.temperature = 0
                    
                    # 获取功耗
                    try:
                        gpu_info.power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # W
                        gpu_info.power_limit = pynvml.nvmlDeviceGetPowerManagementLimitConstraints(handle)[1] / 1000.0  # W
                    except:
                        gpu_info.power_usage = 0
                        gpu_info.power_limit = 0
                    
                    # 获取风扇速度（支持多个风扇）
                    try:
                        # 先尝试获取风扇数量
                        try:
                            fan_count = pynvml.nvmlDeviceGetNumFans(handle)
                            fan_speeds = []
                            for fan_index in range(fan_count):
                                try:
                                    fan_speed = pynvml.nvmlDeviceGetFanSpeed_v2(handle, fan_index)
                                    fan_speeds.append(fan_speed)
                                except:
                                    # 如果v2 API不可用，尝试旧API
                                    try:
                                        fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
                                        fan_speeds.append(fan_speed)
                                        break  # 旧API只返回一个值
                                    except:
                                        pass
                            gpu_info.fan_speeds = fan_speeds if fan_speeds else [0]
                            gpu_info.fan_speed = fan_speeds[0] if fan_speeds else 0  # 兼容旧代码
                        except:
                            # 如果获取风扇数量失败，使用旧API
                            gpu_info.fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
                            gpu_info.fan_speeds = [gpu_info.fan_speed] if gpu_info.fan_speed > 0 else []
                    except:
                        gpu_info.fan_speed = 0
                        gpu_info.fan_speeds = []
                    
                    # 获取进程信息
                    try:
                        procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                        gpu_info.processes = [
                            {
                                'pid': proc.pid,
                                'used_memory': proc.usedGpuMemory // (1024**2)  # MB
                            }
                            for proc in procs
                        ]
                    except:
                        gpu_info.processes = []
                    
                    gpu_list.append(gpu_info)
                
                self.gpu_data_updated.emit(gpu_list)
                time.sleep(self.update_interval)
                
        except Exception as e:
            print(f"监控错误: {e}")
        finally:
            try:
                pynvml.nvmlShutdown()
            except:
                pass
    
    def stop(self):
        """停止监控"""
        self.running = False


class GPUCard(QFrame):
    """单个 GPU 卡片组件 - 横向布局"""
    def __init__(self, gpu_info: GPUInfo):
        super().__init__()
        self.gpu_info = gpu_info
        self.gradient_offset = 0  # 渐变偏移量，用于流动效果（初始值会在start_animation时设置）
        self.animation_timer = QTimer()  # 动画定时器
        self.animation_timer.timeout.connect(self.update_gradient_offset)
        self.animation_timer.setInterval(20)  # 每20ms更新一次，实现快速流畅动画
        self.is_animating = False  # 是否正在播放动画
        self.temperature_history = []  # 温度历史记录，用于检测连续变化
        self.base_temperature = gpu_info.temperature  # 基准温度，用于计算变化
        self.init_ui()
        self.update_style()
    
    def __del__(self):
        """析构函数，确保定时器被停止"""
        if hasattr(self, 'animation_timer'):
            self.animation_timer.stop()
    
    def init_ui(self):
        """初始化 UI"""
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setMinimumHeight(70)  # 最小高度
        self.setMaximumHeight(70)  # 最大高度，固定为70px
        self.setMinimumWidth(580)  # 最小宽度
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)  # 水平扩展，垂直固定
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(10, 5, 10, 5)  # 减小上下内边距
        
        # 标题栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        # GPU 名称
        self.title_label = QLabel(f"GPU {self.gpu_info.index}: {self.gpu_info.name}")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #2c3e50; border: none; background-color: transparent;")  # 移除边框和背景
        header_layout.addWidget(self.title_label)
        
        # 关键指标
        self.quick_info_layout = QHBoxLayout()
        self.quick_info_layout.setSpacing(8)
        self.quick_info_layout.setContentsMargins(5, 0, 5, 0)
        
        # GPU 利用率进度条
        self.quick_gpu_bar = QProgressBar()
        self.quick_gpu_bar.setMinimum(0)
        self.quick_gpu_bar.setMaximum(100)
        self.quick_gpu_bar.setFixedHeight(25)
        self.quick_gpu_bar.setTextVisible(True)
        self.quick_gpu_bar.setMouseTracking(True)  # 启用鼠标跟踪
        self.quick_gpu_bar.installEventFilter(self)  # 安装事件过滤器
        self.quick_info_layout.addWidget(self.quick_gpu_bar)
        
        # VRAM进度条
        self.quick_mem_bar = QProgressBar()
        self.quick_mem_bar.setMinimum(0)
        self.quick_mem_bar.setMaximum(100)
        self.quick_mem_bar.setFixedHeight(25)
        self.quick_mem_bar.setTextVisible(True)
        self.quick_mem_bar.setMouseTracking(True)  # 启用鼠标跟踪
        self.quick_mem_bar.installEventFilter(self)  # 安装事件过滤器
        self.quick_info_layout.addWidget(self.quick_mem_bar)
        
        # 温度进度条（0-100度映射到0-100%）
        self.quick_temp_bar = QProgressBar()
        self.quick_temp_bar.setMinimum(0)
        self.quick_temp_bar.setMaximum(100)
        self.quick_temp_bar.setFixedHeight(25)
        self.quick_temp_bar.setTextVisible(True)
        self.quick_temp_bar.setMouseTracking(True)  # 启用鼠标跟踪
        self.quick_temp_bar.installEventFilter(self)  # 安装事件过滤器
        self.quick_info_layout.addWidget(self.quick_temp_bar)
        
        # 功耗进度条（基于功耗限制的百分比）
        self.quick_power_bar = QProgressBar()
        self.quick_power_bar.setMinimum(0)
        self.quick_power_bar.setMaximum(100)
        self.quick_power_bar.setFixedHeight(25)
        self.quick_power_bar.setTextVisible(True)
        self.quick_power_bar.setMouseTracking(True)  # 启用鼠标跟踪
        self.quick_power_bar.installEventFilter(self)  # 安装事件过滤器
        self.quick_info_layout.addWidget(self.quick_power_bar)
        
        header_layout.addLayout(self.quick_info_layout)
        main_layout.addLayout(header_layout)
        self.setLayout(main_layout)
        
        # 更新快速信息显示
        self.update_quick_info()
        
        # 设置工具提示（鼠标悬停时显示）
        self.update_tooltip()
    
    def update_quick_info(self):
        """更新快速信息显示（使用进度条）"""
        # GPU 利用率进度条
        gpu_percent = self.gpu_info.utilization_gpu
        self.quick_gpu_bar.setValue(int(gpu_percent))
        self.quick_gpu_bar.setFormat(f"GPU: {gpu_percent:.0f}%")
        self.quick_gpu_bar.setToolTip(f"GPU 利用率: {gpu_percent:.1f}%\n\n表示 GPU 计算核心的使用率。\n0-50%: 低负载\n50-80%: 中等负载\n80-100%: 高负载")
        self.update_progress_bar_color(self.quick_gpu_bar, gpu_percent)
        
        # VRAM进度条
        mem_percent = (self.gpu_info.memory_used / self.gpu_info.memory_total * 100) if self.gpu_info.memory_total > 0 else 0
        mem_text = f"{self.gpu_info.memory_used/1024:.1f}G/{self.gpu_info.memory_total/1024:.0f}G"
        self.quick_mem_bar.setValue(int(mem_percent))
        self.quick_mem_bar.setFormat(mem_text)
        mem_used_gb = self.gpu_info.memory_used / 1024
        mem_total_gb = self.gpu_info.memory_total / 1024
        self.quick_mem_bar.setToolTip(f"VRAM (显存) 使用率: {mem_percent:.1f}%\n\n已使用: {mem_used_gb:.2f} GB\n总容量: {mem_total_gb:.2f} GB\n\nVRAM 是 GPU 的专用内存，用于存储纹理、帧缓冲区和计算数据。")
        self.update_progress_bar_color(self.quick_mem_bar, mem_percent)
        
        # 温度进度条（0-100度映射到0-100%）
        temp_percent = min(self.gpu_info.temperature, 100)
        temp_color = self.get_temperature_color(self.gpu_info.temperature)
        self.quick_temp_bar.setValue(int(temp_percent))
        self.quick_temp_bar.setFormat(f"{self.gpu_info.temperature}°C")
        self.quick_temp_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
            }}
            QProgressBar::chunk {{
                background-color: {temp_color};
                border-radius: 3px;
            }}
        """)
        temp_status = "正常" if self.gpu_info.temperature < 50 else ("中等" if self.gpu_info.temperature < 70 else "较高")
        self.quick_temp_bar.setToolTip(f"GPU 温度: {self.gpu_info.temperature}°C\n\n状态: {temp_status}\n\n< 50°C: 正常温度，GPU 运行轻松\n50-70°C: 中等温度，正常负载\n> 70°C: 较高温度，建议检查散热")
        
        # 功耗进度条（基于功耗限制的百分比）
        if self.gpu_info.power_limit > 0:
            power_percent = (self.gpu_info.power_usage / self.gpu_info.power_limit * 100)
            power_text = f"{self.gpu_info.power_usage:.0f}W/{self.gpu_info.power_limit:.0f}W"
        else:
            power_percent = 0
            power_text = f"{self.gpu_info.power_usage:.0f}W"
        self.quick_power_bar.setValue(int(power_percent))
        self.quick_power_bar.setFormat(power_text)
        if self.gpu_info.power_limit > 0:
            self.quick_power_bar.setToolTip(f"GPU 功耗: {self.gpu_info.power_usage:.1f}W / {self.gpu_info.power_limit:.1f}W ({power_percent:.1f}%)\n\n当前功耗: {self.gpu_info.power_usage:.1f}W\n功耗限制: {self.gpu_info.power_limit:.1f}W\n\n功耗反映了 GPU 的能耗水平，高负载时功耗会增加。")
        else:
            self.quick_power_bar.setToolTip(f"GPU 功耗: {self.gpu_info.power_usage:.1f}W\n\n当前功耗: {self.gpu_info.power_usage:.1f}W\n\n功耗反映了 GPU 的能耗水平，高负载时功耗会增加。")
        self.update_progress_bar_color(self.quick_power_bar, power_percent)
    
    def get_temperature_color(self, temp: float) -> str:
        """根据温度返回颜色"""
        if temp < 50:
            return "#2ecc71"  # 绿色
        elif temp < 70:
            return "#f39c12"  # 橙色
        else:
            return "#e74c3c"  # 红色
    
    def update_progress_bar_color(self, bar: QProgressBar, value: float):
        """更新进度条颜色"""
        if value < 50:
            color = "#2ecc71"  # 绿色
        elif value < 80:
            color = "#f39c12"  # 橙色
        else:
            color = "#e74c3c"  # 红色
        
        bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理进度条的鼠标事件以显示工具提示"""
        if obj in [self.quick_gpu_bar, self.quick_mem_bar, self.quick_temp_bar, self.quick_power_bar]:
            if event.type() == QEvent.Type.Enter:
                # 鼠标进入时显示工具提示
                tooltip_text = obj.toolTip()
                if tooltip_text:
                    # 获取全局坐标，使用QToolTip.showText强制显示
                    global_pos = obj.mapToGlobal(QPoint(obj.width() // 2, 0))
                    QToolTip.showText(global_pos, tooltip_text, obj, obj.rect(), 5000)
            elif event.type() == QEvent.Type.Leave:
                # 鼠标离开时隐藏工具提示
                QToolTip.hideText()
        return super().eventFilter(obj, event)
    
    def update_data(self, gpu_info: GPUInfo):
        """更新 GPU 数据"""
        self.gpu_info = gpu_info
        
        # 记录温度历史（保留最近10个值）
        self.temperature_history.append(gpu_info.temperature)
        if len(self.temperature_history) > 10:
            self.temperature_history.pop(0)
        
        # 检查温度变化，决定是否启动/停止动画
        if len(self.temperature_history) >= 2:
            # 计算从基准温度到当前温度的变化
            temp_change = gpu_info.temperature - self.base_temperature
            # 计算最近一次的温度变化（处理突然变化的情况）
            single_change = gpu_info.temperature - self.temperature_history[-2]
            
            if not self.is_animating:
                # 检查温度是否上升超过5度（支持连续上升和突然提升）
                if temp_change >= 5:
                    # 检查是否连续上升（最近几个值都是上升趋势）
                    is_rising = True
                    for i in range(1, min(3, len(self.temperature_history))):
                        if self.temperature_history[i] <= self.temperature_history[i-1]:
                            is_rising = False
                            break
                    
                    # 触发条件：连续上升 OR 单次变化≥3度（处理突然提升）
                    if is_rising or single_change >= 3:
                        self.start_animation()
                        self.base_temperature = gpu_info.temperature  # 更新基准温度为动画启动时的温度
            else:
                # 检查温度是否降低（支持连续下降和突然降低）
                # 检查是否连续下降（最近几个值都是下降趋势）
                is_falling = True
                for i in range(1, min(3, len(self.temperature_history))):
                    if self.temperature_history[i] >= self.temperature_history[i-1]:
                        is_falling = False
                        break
                
                # 触发条件：
                # 1. 从基准温度连续下降超过5度
                # 2. 单次下降≥3度（处理突然降低）
                # 与上升检测逻辑对称：temp_change >= 5 且（连续上升 或 单次上升≥3度）
                if (temp_change <= -5 and is_falling) or single_change <= -3:
                    self.stop_animation()
                    self.base_temperature = gpu_info.temperature  # 更新基准温度为停止时的温度
        
        # 更新快速信息
        self.update_quick_info()
        # 更新工具提示
        self.update_tooltip()
        # 触发重绘以更新背景
        self.update()
    
    def start_animation(self):
        """启动颜色循环动画"""
        if not self.is_animating:
            self.is_animating = True
            # 设置初始偏移量为0，从红色开始循环
            self.gradient_offset = 0
            # 清除样式表背景，使用自定义绘制
            self.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                    border: 2px solid #3498db;
                    border-radius: 10px;
                    margin: 5px;
                }
            """)
            self.animation_timer.start()
    
    def stop_animation(self):
        """停止流动彩色动画"""
        if self.is_animating:
            self.is_animating = False
            self.animation_timer.stop()
            self.gradient_offset = 0
            # 恢复原始样式
            self.update_style()
            self.update()  # 重绘以恢复原始背景
    
    def update_gradient_offset(self):
        """更新颜色循环偏移量"""
        self.gradient_offset += 20  # 每次移动20像素，速度提升2倍
        # 使用模运算实现循环，保持动画连续性
        # 一个完整颜色周期 = width() * 7（7种颜色）
        cycle_length = self.width() * 7 if self.width() > 0 else 1
        self.gradient_offset = self.gradient_offset % cycle_length
        self.update()  # 触发重绘
    
    def update_tooltip(self):
        """更新工具提示（显示风扇转速）"""
        if hasattr(self.gpu_info, 'fan_speeds') and self.gpu_info.fan_speeds:
            if len(self.gpu_info.fan_speeds) == 1:
                fan_text = f"风扇转速: {self.gpu_info.fan_speeds[0]}%"
            else:
                fan_text_list = [f"{s}%" for s in self.gpu_info.fan_speeds]
                fan_text = f"风扇转速: {' / '.join(fan_text_list)}"
            self.setToolTip(fan_text)
        elif self.gpu_info.fan_speed > 0:
            self.setToolTip(f"风扇转速: {self.gpu_info.fan_speed}%")
        else:
            self.setToolTip("")  # 没有风扇数据时不显示工具提示
    
    def paintEvent(self, event):
        """重写绘制事件，实现颜色循环背景"""
        if self.is_animating:
            # 绘制循环彩色背景（整个区域颜色循环变化）
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            rect = self.rect()
            
            # 定义7种彩虹颜色
            colors = [
                QColor(255, 0, 0),        # 红
                QColor(255, 127, 0),      # 橙
                QColor(255, 255, 0),      # 黄
                QColor(0, 255, 0),        # 绿
                QColor(0, 255, 255),      # 青
                QColor(0, 0, 255),        # 蓝
                QColor(127, 0, 255),      # 紫
            ]
            
            # 根据偏移量计算当前应该显示的颜色（平滑渐变）
            num_colors = len(colors)
            # 一个完整颜色周期的长度
            cycle_length = rect.width() * num_colors if rect.width() > 0 else 1
            # 计算归一化的位置（0.0到1.0之间）
            normalized_pos = (self.gradient_offset % cycle_length) / cycle_length if cycle_length > 0 else 0
            
            # 计算当前颜色索引和插值比例
            color_position = normalized_pos * num_colors
            color_index = int(color_position) % num_colors
            next_color_index = (color_index + 1) % num_colors
            interpolation_factor = color_position - int(color_position)  # 0.0到1.0之间的插值比例
            
            # 获取当前颜色和下一个颜色
            current_color = colors[color_index]
            next_color = colors[next_color_index]
            
            # 颜色插值，实现平滑渐变
            r = int(current_color.red() + (next_color.red() - current_color.red()) * interpolation_factor)
            g = int(current_color.green() + (next_color.green() - current_color.green()) * interpolation_factor)
            b = int(current_color.blue() + (next_color.blue() - current_color.blue()) * interpolation_factor)
            
            # 确保颜色值在有效范围内（0-255）
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            # 创建插值后的颜色
            current_color = QColor(r, g, b)
            
            # 绘制圆角矩形背景（单一颜色）
            painter.setBrush(current_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 10, 10)
            
            # 绘制半透明白色覆盖层，使内容清晰可见
            overlay_color = QColor(255, 255, 255, 200)  # 半透明白色
            painter.setBrush(overlay_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 10, 10)
            
            # 绘制边框
            border_color = QColor(52, 152, 219)  # 蓝色边框
            border_pen = painter.pen()
            border_pen.setColor(border_color)
            border_pen.setWidth(2)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 10, 10)
            
            painter.end()
            
            # 调用父类绘制，确保子组件正常显示
            super().paintEvent(event)
        else:
            # 正常绘制
            super().paintEvent(event)
    
    def update_style(self):
        """更新样式"""
        if not self.is_animating:
            self.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    border: 2px solid #bdc3c7;
                    border-radius: 10px;
                    margin: 5px;
                }
                QFrame:hover {
                    border: 2px solid #3498db;
                    background-color: #f8f9fa;
                }
            """)


class GPUMonitorWidget(QMainWindow):
    """GPU 监控主窗口"""
    def __init__(self):
        super().__init__()
        self.gpu_cards = []
        self.monitor_thread = None
        self.title_hide_timer = QTimer()  # 标题栏隐藏定时器
        self.title_hide_timer.timeout.connect(self.hide_window_title_bar)
        self.title_bar_hidden = False  # 标题栏是否已隐藏
        self.drag_position = None  # 拖拽位置
        self.process = None  # 当前进程对象
        if HAS_PSUTIL:
            self.process = psutil.Process(os.getpid())
        self.init_ui()
        self.start_monitoring()
        # 启动内存监控定时器（每2秒更新一次）
        self.memory_timer = QTimer()
        self.memory_timer.timeout.connect(self.update_memory_usage)
        self.memory_timer.start(2000)  # 2秒更新一次
        # 启动10秒后隐藏窗口标题栏
        QTimer.singleShot(10000, self.hide_window_title_bar)
    
    def init_ui(self):
        """初始化 UI - 横向布局"""
        self.setWindowTitle("GPU Monitor - WatchGPU")
        self.setMinimumSize(1500, 115)  # 横向长条，最小高度115px（70px卡片+20px标题+18px状态栏+7px间距）
        self.setMaximumHeight(115)  # 固定高度，确保卡片完整显示
        
        # 启用鼠标跟踪以检测悬停在窗口标题栏区域
        self.setMouseTracking(True)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QLabel {
                background-color: transparent;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局（横向）
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)  # 增加间距，确保状态栏和卡片之间有足够空间
        main_layout.setContentsMargins(10, 3, 10, 0)  # 减小底部边距，让状态栏更靠近窗口下边缘
        
        # 标题栏（紧凑）
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)  # 移除标题栏边距
        title_label = QLabel("🎮 GPU Monitor")
        title_font = QFont()
        title_font.setPointSize(10)  # 减小字体
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; padding: 0px;")
        title_label.setMaximumHeight(20)  # 限制标题栏高度
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        main_layout.addLayout(title_layout)
        
        # GPU 卡片容器（横向滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 不需要垂直滚动
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # 固定高度
        scroll.setMinimumHeight(70)  # 确保滚动区域至少能显示70px高的卡片
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # GPU 卡片容器（横向布局）
        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout()  # 改为横向布局
        self.cards_layout.setSpacing(5)  # 减小卡片间距
        self.cards_layout.setContentsMargins(3, 0, 3, 0)  # 移除上下边距，确保卡片完整显示
        self.cards_container.setMinimumHeight(70)  # 确保容器至少能显示70px高的卡片
        self.cards_container.setLayout(self.cards_layout)
        
        scroll.setWidget(self.cards_container)
        main_layout.addWidget(scroll)
        
        # 状态栏（紧凑，靠近窗口下边缘）
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 2px 2px 0px 2px; font-size: 10px; font-weight: bold;")  # 移除底部内边距
        self.status_label.setFixedHeight(20)  # 增加状态栏高度以容纳更大的字体
        status_font = QFont()
        status_font.setPointSize(10)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        main_layout.addWidget(self.status_label)
        
        central_widget.setLayout(main_layout)
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        
        self.monitor_thread = GPUMonitorThread()
        self.monitor_thread.gpu_data_updated.connect(self.update_gpu_cards)
        self.monitor_thread.start()
        self.status_label.setText("Monitoring...")
    
    def get_memory_usage(self):
        """获取程序自身的内存占用（MB）"""
        if HAS_PSUTIL and self.process:
            try:
                memory_info = self.process.memory_info()
                return memory_info.rss / (1024 * 1024)  # 转换为 MB
            except:
                return 0.0
        return 0.0
    
    def update_memory_usage(self):
        """更新内存占用显示"""
        memory_mb = self.get_memory_usage()
        if memory_mb > 0:
            # 更新状态栏，显示内存占用
            if memory_mb < 1024:
                memory_text = f"App Memory: {memory_mb:.1f} MB"
            else:
                memory_text = f"App Memory: {memory_mb/1024:.2f} GB"
            # 如果状态栏已有内容，追加内存信息
            current_text = self.status_label.text()
            if "|" in current_text:
                # 提取 GPU 信息部分
                gpu_part = current_text.split("|")[0].strip()
                time_part = current_text.split("|")[-1].strip()
                self.status_label.setText(f"{gpu_part} | {memory_text} | {time_part}")
            else:
                self.status_label.setText(f"{memory_text} | {time.strftime('%H:%M:%S')}")
    
    def update_gpu_cards(self, gpu_list: List[GPUInfo]):
        """更新 GPU 卡片"""
        # 如果卡片数量不匹配，重新创建
        if len(self.gpu_cards) != len(gpu_list):
            # 清除旧卡片
            for card in self.gpu_cards:
                self.cards_layout.removeWidget(card)
                card.deleteLater()
            self.gpu_cards.clear()
            
            # 创建新卡片
            for gpu_info in gpu_list:
                card = GPUCard(gpu_info)
                self.gpu_cards.append(card)
                self.cards_layout.addWidget(card)
        else:
            # 更新现有卡片
            for i, gpu_info in enumerate(gpu_list):
                if i < len(self.gpu_cards):
                    self.gpu_cards[i].update_data(gpu_info)
        
        # 更新状态
        gpu_count = len(gpu_list)
        memory_mb = self.get_memory_usage()
        if memory_mb > 0:
            if memory_mb < 1024:
                memory_text = f"App Memory: {memory_mb:.1f} MB"
            else:
                memory_text = f"App Memory: {memory_mb/1024:.2f} GB"
            self.status_label.setText(f"Detected {gpu_count} GPU(s) | {memory_text} | Last Update: {time.strftime('%H:%M:%S')}")
        else:
            self.status_label.setText(f"Detected {gpu_count} GPU(s) | Last Update: {time.strftime('%H:%M:%S')}")
    
    def hide_window_title_bar(self):
        """隐藏窗口标题栏"""
        if not self.title_bar_hidden:
            # 保存原始窗口标志
            self.original_flags = self.windowFlags()
            # 设置无边框窗口（隐藏标题栏）
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
            # 设置窗口透明度为75%
            self.setWindowOpacity(0.75)
            self.show()
            self.title_bar_hidden = True
    
    def is_click_on_card(self, pos):
        """检查点击位置是否在GPU卡片上"""
        clicked_widget = self.childAt(pos)
        if clicked_widget:
            # 向上查找父组件，看是否是GPUCard
            parent = clicked_widget
            while parent:
                if isinstance(parent, GPUCard):
                    return True
                parent = parent.parent()
        return False
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始拖拽窗口"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在卡片上
            if not self.is_click_on_card(event.pos()):
                # 如果不在卡片上，且标题栏已隐藏，允许拖拽
                if self.title_bar_hidden:
                    self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    event.accept()
                    return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖拽窗口"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            # 移动窗口
            if self.title_bar_hidden:
                self.move(event.globalPosition().toPoint() - self.drag_position)
                event.accept()
                return
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 结束拖拽"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
        super().mouseReleaseEvent(event)
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        # 检查点击位置是否在GPU卡片上
        if not self.is_click_on_card(event.pos()):
            # 如果不在卡片上，显示右键菜单
            menu = QMenu(self)
            close_action = menu.addAction("关闭程序")
            close_action.triggered.connect(self.close)
            menu.exec(event.globalPos())
        else:
            # 如果在卡片上，不显示菜单，让卡片处理事件
            super().contextMenuEvent(event)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        if self.title_hide_timer.isActive():
            self.title_hide_timer.stop()
        if hasattr(self, 'memory_timer') and self.memory_timer.isActive():
            self.memory_timer.stop()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示窗口
    window = GPUMonitorWidget()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

