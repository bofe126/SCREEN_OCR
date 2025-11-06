import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw, ImageFont, ImageTk
import ctypes
from keyboard import read_hotkey
import queue
import threading
import win32api
from cairosvg import svg2png
from io import BytesIO
import logging
import sys
from datetime import datetime

# 设置 CustomTkinter 外观模式和主题
ctk.set_appearance_mode("dark")  # 暗色模式（支持 "light", "dark", "system"）
ctk.set_default_color_theme("blue")  # 蓝色主题（支持 "blue", "green", "dark-blue"）

# 全局日志缓冲区（程序启动时就开始捕获）
class GlobalLogBuffer:
    """全局日志缓冲区，在程序启动时就开始捕获所有输出"""
    def __init__(self):
        self.buffer = []
        self.max_size = 1000  # 最多保存1000条日志
        self.text_widget = None  # 稍后设置
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.log_handler = None
        self.stdout_handler = None
        self.stderr_handler = None
        self._capturing = False
    
    def start_capture(self):
        """开始捕获日志"""
        if self._capturing:
            return
        
        self._capturing = True
        
        # 保存原始流（可能为 None，在窗口程序中）
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # 移除所有可能导致问题的 StreamHandler（指向 None 的）
        root_logger = logging.getLogger()
        handlers_to_remove = []
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                # 检查 stream 是否为 None 或指向已替换的流
                if handler.stream is None or handler.stream in (sys.stdout, sys.stderr):
                    handlers_to_remove.append(handler)
        
        for handler in handlers_to_remove:
            root_logger.removeHandler(handler)
        
        # 创建 stdout 捕获（即使 original_stdout 为 None 也能工作）
        self.stdout_handler = BufferedStreamCapture(self, sys.stdout)
        sys.stdout = self.stdout_handler
        
        # 创建 stderr 捕获（即使 original_stderr 为 None 也能工作）
        self.stderr_handler = BufferedStreamCapture(self, sys.stderr)
        sys.stderr = self.stderr_handler
        
        # 创建 logging 处理器
        self.log_handler = BufferedLogHandler(self)
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(self.log_handler)
    
    def add_log(self, message, source="LOG"):
        """添加日志到缓冲区"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'message': message,
            'source': source
        }
        self.buffer.append(log_entry)
        
        # 限制缓冲区大小
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)
        
        # 如果文本框已连接，立即显示
        if self.text_widget:
            self._append_to_widget(log_entry)
    
    def connect_widget(self, text_widget):
        """连接文本框，显示所有历史日志"""
        self.text_widget = text_widget
        
        # 如果传入 None，只是断开连接，不显示历史
        if text_widget is None:
            return
        
        # 显示所有历史日志
        if self.buffer:
            try:
                self.text_widget.configure(state='normal')
                for entry in self.buffer:
                    formatted = f"{entry['timestamp']} - {entry['message']}"
                    self.text_widget.insert('end', formatted + '\n')
                self.text_widget.see('end')
                self.text_widget.configure(state='disabled')
            except:
                pass
    
    def _append_to_widget(self, entry):
        """添加新日志到文本框"""
        if not self.text_widget:
            return
        
        try:
            formatted = f"{entry['timestamp']} - {entry['message']}"
            def append():
                try:
                    # 再次检查，因为可能在此期间被设置为 None
                    if not self.text_widget:
                        return
                    self.text_widget.configure(state='normal')
                    self.text_widget.insert('end', formatted + '\n')
                    self.text_widget.see('end')
                    self.text_widget.configure(state='disabled')
                except:
                    pass
            
            self.text_widget.after(0, append)
        except:
            pass
    
    def stop_capture(self):
        """停止捕获"""
        if not self._capturing:
            return
        
        self._capturing = False
        
        # 恢复原始流（如果存在）
        if self.stdout_handler:
            try:
                sys.stdout = self.original_stdout if self.original_stdout else sys.__stdout__
            except:
                sys.stdout = sys.__stdout__
        
        if self.stderr_handler:
            try:
                sys.stderr = self.original_stderr if self.original_stderr else sys.__stderr__
            except:
                sys.stderr = sys.__stderr__
        
        # 移除日志处理器
        if self.log_handler:
            root_logger = logging.getLogger()
            if self.log_handler in root_logger.handlers:
                root_logger.removeHandler(self.log_handler)
        
        self.text_widget = None

class BufferedStreamCapture:
    """缓冲流捕获器"""
    def __init__(self, buffer, original_stream):
        self.buffer = buffer
        self.original_stream = original_stream
        self.line_buffer = ""
    
    def write(self, message):
        """写入消息"""
        # 安全地写入原始流（如果存在）
        if self.original_stream:
            try:
                self.original_stream.write(message)
                self.original_stream.flush()
            except:
                pass
        
        # 添加到缓冲区
        if message:
            self.line_buffer += message
            if '\n' in self.line_buffer:
                lines = self.line_buffer.split('\n')
                self.line_buffer = lines[-1]
                for line in lines[:-1]:
                    if line.strip():
                        self.buffer.add_log(line.strip(), "OUTPUT")
    
    def flush(self):
        """刷新输出"""
        if self.original_stream:
            try:
                self.original_stream.flush()
            except:
                pass
        
        # 如果缓冲区有内容，也输出
        if self.line_buffer.strip():
            self.buffer.add_log(self.line_buffer.strip(), "OUTPUT")
            self.line_buffer = ""

class BufferedLogHandler(logging.Handler):
    """缓冲日志处理器"""
    def __init__(self, buffer):
        super().__init__()
        self.buffer = buffer
        self.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    def emit(self, record):
        """安全地输出日志记录"""
        try:
            msg = self.format(record)
            self.buffer.add_log(msg, "LOG")
        except Exception:
            # 静默处理异常，避免循环错误
            pass

# 创建全局日志缓冲区实例
_global_log_buffer = GlobalLogBuffer()

# 在模块加载时立即开始捕获
_global_log_buffer.start_capture()

class TextWidgetHandler(logging.Handler):
    """自定义日志处理器，将日志输出到文本框"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        # 简化格式，只显示级别和消息
        self.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    def emit(self, record):
        """输出日志记录"""
        try:
            msg = self.format(record)
            # 使用 after 确保在主线程中更新UI
            self.text_widget.after(0, lambda: self._append_log(msg))
        except:
            pass
    
    def _append_log(self, msg):
        """在文本框中添加日志（主线程）"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_msg = f"{timestamp} - {msg}"
            
            self.text_widget.configure(state='normal')
            self.text_widget.insert('end', formatted_msg + '\n')
            self.text_widget.see('end')  # 自动滚动到底部
            self.text_widget.configure(state='disabled')
        except:
            pass

class PrintCapture:
    """捕获 print 输出到文本框"""
    def __init__(self, text_widget, original_stream):
        self.text_widget = text_widget
        self.original_stream = original_stream
        self.buffer = ""  # 缓冲不完整的行
    
    def write(self, message):
        """重定向 print 输出"""
        try:
            # 同时输出到原始 stdout/stderr（控制台）
            if self.original_stream:
                self.original_stream.write(message)
                self.original_stream.flush()
            
            # 添加到缓冲区
            if message:
                self.buffer += message
                
                # 如果包含换行符，处理完整行
                if '\n' in self.buffer:
                    lines = self.buffer.split('\n')
                    # 保留最后不完整的行在缓冲区
                    self.buffer = lines[-1]
                    # 处理完整的行
                    for line in lines[:-1]:
                        if line.strip():  # 忽略空行
                            self._append_line(line)
        except:
            pass
    
    def flush(self):
        """刷新输出"""
        try:
            if self.original_stream:
                self.original_stream.flush()
            
            # 如果缓冲区有内容，也输出
            if self.buffer.strip():
                self._append_line(self.buffer)
                self.buffer = ""
        except:
            pass
    
    def _append_line(self, line):
        """添加一行到文本框"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_msg = f"{timestamp} - {line}"
            
            def append():
                try:
                    self.text_widget.configure(state='normal')
                    self.text_widget.insert('end', formatted_msg + '\n')
                    self.text_widget.see('end')
                    self.text_widget.configure(state='disabled')
                except:
                    pass
            
            self.text_widget.after(0, append)
        except:
            pass

class HighDPIApp:
    """高DPI支持"""
    @staticmethod
    def set_dpi_awareness():
        """设置DPI感知"""
        try:
            # 使用 PROCESS_PER_MONITOR_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                # 降级到 PROCESS_SYSTEM_DPI_AWARE
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except:
                try:
                    # 最后尝试旧版 API
                    ctypes.windll.user32.SetProcessDPIAware()
                except:
                    pass
    
    @staticmethod
    def get_dpi_scale(window):
        """获取DPI缩放比例"""
        try:
            # 获取窗口关联的显示器句柄
            monitor = ctypes.windll.user32.MonitorFromWindow(
                window.winfo_id(), 0x00000002)  # MONITOR_DEFAULTTONEAREST
            
            # 获取显示器DPI
            dpi_x = ctypes.c_uint()
            dpi_y = ctypes.c_uint()
            ctypes.windll.shcore.GetDpiForMonitor(
                monitor,
                0,  # MDT_EFFECTIVE_DPI
                ctypes.byref(dpi_x),
                ctypes.byref(dpi_y)
            )
            
            # 计算缩放比例（相对于96 DPI）
            return dpi_x.value / 96.0
        except:
            try:
                # 备用方法：使用DC获取DPI
                dc = ctypes.windll.user32.GetDC(0)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
                ctypes.windll.user32.ReleaseDC(0, dc)
                return dpi / 96.0
            except:
                return 1.0  # 如果无法获取DPI，返回1.0表示不缩放

class ModernTheme:
    """现代主题样式"""
    FONT_FAMILY = "Microsoft YaHei UI"
    TITLE_FONT = (FONT_FAMILY, 16, "bold")
    BOLD_FONT = (FONT_FAMILY, 11, "bold")
    NORMAL_FONT = (FONT_FAMILY, 11)
    BG_COLOR = "#ffffff"
    FG_COLOR = "#2c3e50"  # 更深的文字颜色
    ACCENT_COLOR = "#3498db"  # 更现代的蓝色
    BUTTON_BG = "#ebf5fb"  # 更柔和的按钮背景色
    HOVER_COLOR = "#d4e9f7"
    BORDER_COLOR = "#bdc3c7"  # 边框颜色
    
    @staticmethod
    def apply(root):
        style = ttk.Style(root)
        style.configure("Title.TLabel", font=ModernTheme.TITLE_FONT)
        style.configure("TLabel", font=ModernTheme.NORMAL_FONT)
        style.configure("TButton", font=ModernTheme.NORMAL_FONT, padding=5)
        style.configure("TCheckbutton", font=ModernTheme.NORMAL_FONT)
        style.configure("TCombobox", font=ModernTheme.NORMAL_FONT)
        style.configure("TSpinbox", font=ModernTheme.NORMAL_FONT)
        
        # 通用设置
        style.configure(".", 
                       background=ModernTheme.BG_COLOR,
                       foreground=ModernTheme.FG_COLOR,
                       font=ModernTheme.NORMAL_FONT)
        
        # 框架样式
        style.configure("TFrame", background=ModernTheme.BG_COLOR)
        
        # 标签样式
        style.configure("TLabel", 
                       background=ModernTheme.BG_COLOR, 
                       foreground=ModernTheme.FG_COLOR,
                       font=ModernTheme.NORMAL_FONT)
        
        # 按钮样式
        style.configure("TButton",
                       background=ModernTheme.BUTTON_BG,
                       foreground=ModernTheme.ACCENT_COLOR,
                       padding=(20, 8),
                       font=ModernTheme.NORMAL_FONT,
                       borderwidth=0)
        style.map("TButton",
                 background=[("active", ModernTheme.HOVER_COLOR)],
                 foreground=[("active", ModernTheme.ACCENT_COLOR)])
        
        # 复选框样式
        style.configure("TCheckbutton",
                       background=ModernTheme.BG_COLOR,
                       foreground=ModernTheme.FG_COLOR,
                       font=ModernTheme.NORMAL_FONT)
        
        # 下拉框样式
        style.configure("TCombobox",
                       background=ModernTheme.BG_COLOR,
                       foreground=ModernTheme.FG_COLOR,
                       arrowcolor=ModernTheme.ACCENT_COLOR,
                       font=ModernTheme.NORMAL_FONT)
        
        # 标题样式
        style.configure("Title.TLabel",
                       font=ModernTheme.TITLE_FONT,
                       foreground=ModernTheme.ACCENT_COLOR)
        
        # 分隔线样式
        style.configure("TSeparator",
                       background=ModernTheme.BORDER_COLOR)
        
        # 设置根窗口背景
        root.configure(bg=ModernTheme.BG_COLOR)

class ConfigDialog:
    def __init__(self, config, callback):
        self.config = config.copy()
        self.callback = callback
        self.root = None
        self.default_config = {
            "trigger_delay_ms": 300,
            "hotkey": "alt",
            "auto_copy": True,
            "show_debug": False,
            "debug_log": ""
        }
        
        try:
            # 设置高DPI支持
            HighDPIApp.set_dpi_awareness()
            
            # 创建窗口并立即移到屏幕外（防止白色闪烁）
            self.root = ctk.CTkToplevel()
            self.root.geometry("+10000+10000")  # 在屏幕外创建和渲染
            self.root.withdraw()  # 隐藏窗口
            self.root.title("Screen OCR 设置")
            
            # 获取DPI缩放比例
            dpi_scale = HighDPIApp.get_dpi_scale(self.root)
            
            # 强制使用 Tkinter 的逻辑像素坐标系统（自动处理DPI）
            # update_idletasks 确保窗口管理器已初始化
            self.root.update_idletasks()
            
            # 获取屏幕尺寸（逻辑像素）
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 根据屏幕大小计算合适的窗口尺寸（使用逻辑像素）
            # 窗口宽度：屏幕宽度的25%，最小400px，最大550px
            # 窗口高度：屏幕高度的50%，最小500px，最大700px（减少了高度避免溢出）
            window_width = max(400, min(550, int(screen_width * 0.25)))
            window_height = max(500, min(700, int(screen_height * 0.50)))
            
            # 确保窗口不会超出屏幕（留出50px边距）
            max_width = screen_width - 100
            max_height = screen_height - 100
            window_width = min(window_width, max_width)
            window_height = min(window_height, max_height)
            
            # 简单直接的居中计算（使用Tkinter的屏幕尺寸）
            x = max(50, (screen_width - window_width) // 2)
            y = max(50, (screen_height - window_height) // 2)
            
            # 保存目标位置，稍后再设置（避免在屏幕上显示）
            self.target_geometry = f"{window_width}x{window_height}+{x}+{y}"
            
            # 暂时只设置大小，保持在屏幕外
            self.root.geometry(f"{window_width}x{window_height}+10000+10000")
            
            # 设置最小窗口大小（防止缩得太小）
            self.root.minsize(400, 500)
            # 允许调整窗口大小
            self.root.resizable(True, True)
            
            # 设置窗口关闭处理
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # 注意：CustomTkinter 自动处理主题，不需要 ModernTheme.apply
            # ModernTheme.apply 是为传统 tkinter/ttk 设计的
            
            self.setup_ui()
        except Exception as e:
            print(f"配置窗口初始化失败: {e}")
            if self.root:
                self.root.destroy()
            raise
    
    def setup_ui(self):
        # 主容器
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=25)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 标题
        title_label = ctk.CTkLabel(main_frame, text="Screen OCR 设置", 
                                   font=("Segoe UI", 20, "bold"),
                                   text_color="#1f538d")
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 25))
        
        current_row = 1
        
        # 触发延时设置
        delay_label = ctk.CTkLabel(main_frame, text="触发延时 (ms)", 
                                    font=("Segoe UI", 14, "bold"))
        delay_label.grid(row=current_row, column=0, sticky="w", pady=(0, 5))
        current_row += 1
        
        # 创建延时设置的容器框架
        delay_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        delay_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 15))
        delay_frame.columnconfigure(0, weight=1)  # 让滑块占据主要空间
        
        # 创建滑块
        self.delay_var = tk.IntVar(value=self.config.get("trigger_delay_ms", self.default_config["trigger_delay_ms"]))
        delay_scale = ctk.CTkSlider(
            delay_frame,
            from_=0,
            to=1000,
            variable=self.delay_var,
            command=self.on_scale_change
        )
        delay_scale.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # 创建数值显示框
        self.delay_display = ctk.CTkLabel(
            delay_frame,
            text=f"{self.delay_var.get()} ms",
            width=80,
            anchor="e"
        )
        self.delay_display.grid(row=0, column=1, sticky="e")
        
        current_row += 1
        
        # 快捷键设置
        hotkey_label = ctk.CTkLabel(main_frame, text="触发快捷键", 
                                     font=("Segoe UI", 14, "bold"))
        hotkey_label.grid(row=current_row, column=0, sticky="w", pady=(0, 5))
        current_row += 1
        
        # 创建快捷键输入框架
        hotkey_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        hotkey_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 15))
        
        # 创建快捷键显示按钮
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", self.default_config["hotkey"]).upper())
        self.hotkey_button = ctk.CTkButton(
            hotkey_frame,
            text=f"{self.hotkey_var.get()}",
            width=100,
            height=30,
            command=self.start_hotkey_record
        )
        self.hotkey_button.grid(row=0, column=0, sticky="w")
        hotkey_frame.columnconfigure(0, weight=1)
        
        self.recording_hotkey = False
        
        current_row += 1
        
        # 分隔线
        separator_frame = ctk.CTkFrame(main_frame, height=2, fg_color="gray70")
        separator_frame.grid(row=current_row, column=0, sticky="ew", pady=15)
        current_row += 1
        
        # 复选框
        self.auto_copy_var = tk.BooleanVar(value=self.config.get("auto_copy", self.default_config["auto_copy"]))
        auto_copy_cb = ctk.CTkCheckBox(main_frame, 
                                     text="自动复制选中文本 (默认开启)", 
                                     variable=self.auto_copy_var,
                                     command=self.update_config)
        auto_copy_cb.grid(row=current_row, column=0, sticky="w", pady=(0, 8))
        current_row += 1
        
        self.image_preprocess_var = tk.BooleanVar(value=self.config.get("image_preprocess", self.default_config.get("image_preprocess", False)))
        preprocess_cb = ctk.CTkCheckBox(main_frame, 
                                     text="图像预处理 (增强对比度+锐化，适合模糊/低对比度文字)", 
                                     variable=self.image_preprocess_var,
                                     command=self.update_config)
        preprocess_cb.grid(row=current_row, column=0, sticky="w", pady=(0, 8))
        current_row += 1
        
        self.show_debug_var = tk.BooleanVar(value=self.config.get("show_debug", self.default_config["show_debug"]))
        show_debug_cb = ctk.CTkCheckBox(main_frame, 
                                      text="显示调试信息 (默认关闭)", 
                                      variable=self.show_debug_var,
                                      command=lambda: (self.toggle_debug_log(), self.update_config()))
        show_debug_cb.grid(row=current_row, column=0, sticky="w", pady=(0, 8))
        current_row += 1
        
        # 调试日志文本框容器
        self.debug_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        
        # 创建日志文本框和按钮的容器
        log_container = ctk.CTkFrame(self.debug_frame, fg_color="transparent")
        log_container.grid(row=0, column=0, sticky="nsew")
        
        self.debug_text = ctk.CTkTextbox(log_container, width=400, height=150, wrap="word")
        
        # 添加测试日志按钮
        button_frame = ctk.CTkFrame(self.debug_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        
        test_log_btn = ctk.CTkButton(
            button_frame, 
            text="生成测试日志",
            width=120,
            height=28,
            command=self._generate_test_logs
        )
        test_log_btn.pack(side="left", padx=5)
        
        clear_log_btn = ctk.CTkButton(
            button_frame,
            text="清空日志",
            width=100,
            height=28,
            command=self._clear_logs
        )
        clear_log_btn.pack(side="left", padx=5)
        
        # 初始化日志处理器（但先不添加）
        self.log_handler = None
        self.stdout_handler = None
        self.stderr_handler = None
        
        # 如果启动时调试模式已开启，立即显示调试框
        if self.show_debug_var.get():
            self.root.after(100, self.toggle_debug_log)
        
        # 保存当前行号，用于调试框的位置
        self.last_row = current_row
    
    def start_hotkey_record(self):
        """开始记录快捷键"""
        if not self.recording_hotkey:
            self.recording_hotkey = True
            self.hotkey_button.configure(text="按下快捷键组合...")
            self.pressed_keys = set()
            
            # 绑定键盘事件到主窗口
            self.root.bind('<KeyPress>', self.on_hotkey_press)
            self.root.bind('<KeyRelease>', self.on_hotkey_release)
            self.hotkey_button.focus_set()

    def on_hotkey_press(self, event):
        """处理按键按下事件"""
        if not self.recording_hotkey:
            return
            
        key_names = {
            16: 'SHIFT', 17: 'CTRL', 18: 'ALT', 91: 'WIN',
            # 可以添加更多特殊键
        }
        
        key = event.keycode
        if key in key_names:
            self.pressed_keys.add(key_names[key])
        else:
            key_char = event.char.upper()
            if key_char and key_char.isprintable():
                self.pressed_keys.add(key_char)
        
        if self.pressed_keys:
            key_text = "+".join(sorted(self.pressed_keys))
            self.hotkey_button.configure(text=key_text)

    def on_hotkey_release(self, event):
        """处理按键释放事件"""
        if not self.recording_hotkey:
            return
            
        key_names = {
            16: 'SHIFT', 17: 'CTRL', 18: 'ALT', 91: 'WIN',
        }
        
        key = event.keycode
        if key in key_names and key_names[key] in self.pressed_keys:
            self.pressed_keys.remove(key_names[key])
        else:
            key_char = event.char.upper()
            if key_char and key_char.isprintable() and key_char in self.pressed_keys:
                self.pressed_keys.remove(key_char)
        
        # 如果所有键都释放了，完成快捷键设置
        if not self.pressed_keys:
            self.recording_hotkey = False
            hotkey = self.hotkey_button.cget("text")
            if hotkey and hotkey != "按下快捷键组合...":
                self.hotkey_var.set(hotkey)
                # 实时更新配置
                self.update_config()
            
            # 解绑键盘事件
            self.root.unbind('<KeyPress>')
            self.root.unbind('<KeyRelease>')
    
    def toggle_debug_log(self):
        if self.show_debug_var.get():
            # 显示调试日志框
            self.debug_frame.grid(row=self.last_row, column=0, sticky="nsew", pady=(0, 8))
            self.debug_text.grid(row=0, column=0, sticky="nsew")
            
            # 设置调试框的大小和布局
            self.debug_frame.columnconfigure(0, weight=1)
            self.debug_frame.rowconfigure(0, weight=1)
            
            # 启动日志捕获
            self._start_log_capture()
            
            # 更新窗口大小后重新计算位置
            self.root.update_idletasks()
            self.center_window()
        else:
            # 停止日志捕获
            self._stop_log_capture()
            
            # 隐藏调试日志框
            self.debug_frame.grid_remove()
            # 更新窗口大小后重新计算位置
            self.root.update_idletasks()
            self.center_window()
    
    def _start_log_capture(self):
        """启动日志捕获（连接到全局缓冲区）"""
        try:
            # 清空文本框
            self.debug_text.configure(state='normal')
            self.debug_text.delete('1.0', 'end')
            
            # 添加欢迎信息
            welcome_msg = f"=== 调试日志窗口打开于 {datetime.now().strftime('%H:%M:%S')} ===\n"
            welcome_msg += "显示从程序启动以来的所有日志\n"
            self.debug_text.insert('1.0', welcome_msg)
            self.debug_text.configure(state='disabled')
            
            # 连接到全局日志缓冲区（会自动显示所有历史日志）
            _global_log_buffer.connect_widget(self.debug_text)
            
            # 标记已连接
            self.log_handler = True  # 标记为已连接
            
        except Exception as e:
            # 使用原始 stdout 输出错误（避免循环）
            try:
                sys.__stdout__.write(f"启动日志捕获失败: {e}\n")
            except:
                pass
    
    def _stop_log_capture(self):
        """停止日志捕获（断开与全局缓冲区的连接）"""
        try:
            # 断开与文本框的连接
            if self.log_handler:
                _global_log_buffer.connect_widget(None)
                self.log_handler = None
        except Exception as e:
            # 注意：这里可能 print 已经被重定向了，所以使用原始 stdout
            try:
                sys.__stdout__.write(f"停止日志捕获失败: {e}\n")
            except:
                pass
    
    def _add_log(self, message, level="INFO"):
        """直接添加日志到文本框"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_msg = f"{timestamp} - {level} - {message}"
            
            self.debug_text.configure(state='normal')
            self.debug_text.insert('end', formatted_msg + '\n')
            self.debug_text.see('end')
            self.debug_text.configure(state='disabled')
        except:
            pass
    
    def _generate_test_logs(self):
        """生成测试日志"""
        try:
            self._add_log("=== 开始测试日志生成 ===")
            
            # 测试不同级别的日志
            logging.debug("这是一条 DEBUG 级别的日志")
            logging.info("这是一条 INFO 级别的日志")
            logging.warning("这是一条 WARNING 级别的日志")
            logging.error("这是一条 ERROR 级别的日志")
            
            # 测试 print 输出（stdout）
            print("这是通过 print() 输出的消息")
            print("多行测试：")
            print("  - 第一行")
            print("  - 第二行")
            
            # 测试 stderr 输出
            import sys
            sys.stderr.write("这是一条 stderr 错误消息\n")
            
            # 模拟配置信息
            self._add_log(f"OCR 引擎: WeChatOCR")
            self._add_log(f"触发延时: {self.config.get('trigger_delay_ms', 'N/A')} ms")
            self._add_log(f"快捷键: {self.config.get('hotkey', 'N/A')}")
            
            # 测试异常输出
            try:
                raise ValueError("这是一个测试异常")
            except Exception as e:
                logging.error(f"捕获到测试异常: {e}")
            
            self._add_log("=== 测试日志生成完成 ===")
            
        except Exception as e:
            self._add_log(f"生成测试日志失败: {e}", "ERROR")
    
    def _clear_logs(self):
        """清空日志"""
        try:
            self.debug_text.configure(state='normal')
            self.debug_text.delete('1.0', 'end')
            
            welcome_msg = f"=== 日志已清空于 {datetime.now().strftime('%H:%M:%S')} ===\n"
            self.debug_text.insert('1.0', welcome_msg)
            self.debug_text.configure(state='disabled')
            
            logging.info("日志已清空")
        except Exception as e:
            print(f"清空日志失败: {e}")

    def center_window(self):
        """将窗口居中显示"""
        # 获取窗口当前大小
        self.root.update_idletasks()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 获取屏幕尺寸（逻辑像素）
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 居中计算，确保不溢出屏幕
        x = max(0, min((screen_width - window_width) // 2, screen_width - window_width))
        y = max(0, min((screen_height - window_height) // 2, screen_height - window_height))
        
        # 设置窗口位置
        self.root.geometry(f"+{x}+{y}")

    def update_config(self):
        """实时更新配置"""
        self.config.update({
            "trigger_delay_ms": self.delay_var.get(),
            "hotkey": self.hotkey_var.get(),
            "auto_copy": self.auto_copy_var.get(),
            "image_preprocess": self.image_preprocess_var.get(),
            "show_debug": self.show_debug_var.get(),
            # 注意：不保存日志内容到配置，日志是临时的
        })
        # 调用回调函数实时更新配置
        self.callback(self.config)

    def on_scale_change(self, value):
        """处理滑块值变化"""
        # 将当前值调整到最近的50的倍数
        current_value = int(float(value))
        snapped_value = round(current_value / 50) * 50
        
        # 如果值发生了变化，更新滑块和配置
        if self.delay_var.get() != snapped_value:
            self.delay_var.set(snapped_value)
            self.delay_display.configure(text=f"{snapped_value} ms")
            # 实时更新配置
            self.update_config()

    def on_scale_click(self, event):
        """处理滑块点击事件"""
        scale = event.widget
        # 计算点击位置对应的值
        clicked_value = scale.get()
        if event.x < 0:
            clicked_value = scale.cget('from')
        elif event.x > scale.winfo_width():
            clicked_value = scale.cget('to')
        else:
            clicked_value = (event.x / scale.winfo_width()) * (scale.cget('to') - scale.cget('from'))
        
        # 调整到最近的50的倍数
        snapped_value = round(clicked_value / 50) * 50
        self.delay_var.set(snapped_value)
        self.delay_display.configure(text=f"{snapped_value} ms")
        # 添加实时配置更新
        self.update_config()

    def show(self):
        """显示配置对话框"""
        if not self.root:
            return
            
        try:
            # 在屏幕外渲染所有组件
            self.root.update_idletasks()
            self.root.update()  # 确保 CustomTkinter 主题完全加载
            
            # 延迟后移到正确位置并显示
            self.root.after(30, self._move_and_show)
            
        except Exception as e:
            print(f"显示配置窗口时发生错误: {e}")
            self.on_closing()
    
    def _move_and_show(self):
        """移动到目标位置并显示窗口"""
        try:
            # 移动到目标位置
            if hasattr(self, 'target_geometry'):
                self.root.geometry(self.target_geometry)
            
            # 显示窗口并置于最前
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            
            # 再次更新确保位置正确（有时需要窗口显示后才能准确获取位置）
            self.root.after(50, self._final_center)
        except:
            pass
    
    def _final_center(self):
        """最终居中调整（窗口显示后）"""
        try:
            self.root.update_idletasks()
            
            # 获取窗口实际大小
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # 获取屏幕尺寸
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 重新计算居中位置，确保不溢出屏幕
            x = max(0, min((screen_width - window_width) // 2, screen_width - window_width))
            y = max(0, min((screen_height - window_height) // 2, screen_height - window_height))
            
            # 设置最终位置
            self.root.geometry(f"+{x}+{y}")
        except:
            pass
            
    def on_closing(self):
        """处理窗口关闭事件"""
        try:
            # 停止日志捕获
            self._stop_log_capture()
            
            if self.root:
                try:
                    if self.root.winfo_exists():
                        # 发送配置更新，通知SystemTray
                        self.callback(self.config)
                        
                        # 只销毁窗口，不要调用 quit()
                        # quit() 会停止整个程序的主循环
                        self.root.destroy()
                except:
                    pass
                finally:
                    self.root = None
        except Exception as e:
            print(f"关闭窗口时发生错误: {e}")

class SystemTray:
    def __init__(self, ocr_instance=None):
        self.config = self.load_config()
        self.icon = None
        self.dialog = None
        self.ocr = ocr_instance
        self.creating_dialog = False  # 防止重复创建对话框
        
        # 检查OCR实例
        if not self.ocr or not hasattr(self.ocr, 'config_queue'):
            raise RuntimeError("OCR实例必须提供config_queue")
    
    def _create_config_dialog(self):
        """在主线程中创建配置对话框"""
        try:
            # 防止重复创建：如果正在创建中，直接返回
            if self.creating_dialog:
                return
            
            # 如果已有对话框且窗口仍然存在，将其提到前台
            if (self.dialog and hasattr(self.dialog, 'root') and 
                self.dialog.root and self.dialog.root.winfo_exists()):
                # 如果窗口被隐藏，先显示它
                self.dialog.root.deiconify()
                self.dialog.root.lift()
                self.dialog.root.focus_force()
                return
            
            # 标记正在创建
            self.creating_dialog = True
            
            # 确保之前的对话框被正确清理
            if self.dialog:
                try:
                    if hasattr(self.dialog, 'root') and self.dialog.root:
                        if self.dialog.root.winfo_exists():
                            self.dialog.root.destroy()
                except:
                    pass
                self.dialog = None
            
            # 创建新的对话框
            self.dialog = ConfigDialog(self.config, self.on_config_changed)
            self.dialog.show()
            
        except Exception as e:
            print(f"创建配置窗口时发生错误: {e}")
            # 清理失效的对话框引用
            if self.dialog:
                try:
                    if hasattr(self.dialog, 'root') and self.dialog.root:
                        if self.dialog.root.winfo_exists():
                            self.dialog.root.destroy()
                except:
                    pass
                self.dialog = None
        finally:
            # 创建完成，重置标志
            self.creating_dialog = False

    def on_config_changed(self, new_config):
        """配置更改回调"""
        try:
            self.config = new_config
            self.save_config()
        except Exception as e:
            print(f"保存配置时发生错误: {e}")

    def show_config(self, icon, item):
        """触发显示配置对话框"""
        try:
            if self.ocr and hasattr(self.ocr, 'config_queue'):
                self.ocr.config_queue.put(self._create_config_dialog)
        except Exception as e:
            print(f"触发配置窗口时发生错误: {e}")

    def create_icon(self):
        """从SVG文件创建系统托盘图标"""
        try:
            from cairosvg import svg2png
            from io import BytesIO
            
            # 读取SVG文件
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
            with open(icon_path, 'rb') as f:
                svg_data = f.read()
            
            # 转换为PNG，稍微放大以适应背景
            png_data = svg2png(bytestring=svg_data, output_width=20, output_height=20)
            
            # 创建带有白色背景的新图像
            background = Image.new('RGBA', (24, 24), color=(0, 0, 0, 0))
            
            # 创建圆角矩形遮罩
            mask = Image.new('L', (24, 24), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, 23, 23], radius=4, fill=255)  # 圆角从6改为4
            
            # 创建白色背景层
            white_bg = Image.new('RGBA', (24, 24), color='white')
            background.paste(white_bg, mask=mask)
            
            # 加载SVG图像并居中放置
            icon = Image.open(BytesIO(png_data))
            icon_x = (24 - icon.width) // 2
            icon_y = (24 - icon.height) // 2
            background.paste(icon, (icon_x, icon_y), icon)
            
            return background
            
        except Exception as e:
            print(f"加载SVG图标失败: {e}")
            # 如果加载失败，使用默认图标
            return self._create_default_icon()
            
    def _create_default_icon(self):
        """创建默认的备用图标"""
        width = 24
        height = 24
        image = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 使用简单的蓝色背景
        bg_color = (41, 128, 185)
        draw.rectangle([0, 0, width, height], fill=bg_color)
        
        # 添加文字
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except:
            font = ImageFont.load_default()
        
        text = "OCR"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        draw.text((x, y), text, fill='white', font=font)
        
        return image

    def toggle_service(self, icon, item):
        """切换OCR服务状态"""
        if self.ocr:
            def toggle():
                self.ocr.toggle_enabled()
                # 更新图标和菜单
                icon.icon = self.create_icon()
                icon.menu = self.create_menu()
            
            # 将任务添加到OCR实例的配置队列
            self.ocr.config_queue.put(toggle)
    
    def on_left_click(self, icon):
        """处理托盘图标左键点击事件"""
        # 左键点击时打开设置窗口
        self.show_config(icon, None)
    
    def create_menu(self):
        """创建系统托盘菜单"""
        return pystray.Menu(
            pystray.MenuItem("设置", self.show_config, default=True),  # 设为默认项，双击时触发
            pystray.MenuItem("启动服务", self.toggle_service, checked=lambda item: self.ocr and self.ocr.enabled),
            pystray.MenuItem("帮助", self.show_help),
            pystray.MenuItem("退出", self.quit)
        )
    
    def quit(self, icon, item):
        """退出程序"""
        try:
            # 关闭配置窗口
            if self.dialog and hasattr(self.dialog, 'root') and self.dialog.root:
                try:
                    if self.dialog.root.winfo_exists():
                        self.dialog.root.destroy()
                except:
                    pass
            self.dialog = None
            
            # 停止OCR服务
            if self.ocr:
                try:
                    if hasattr(self.ocr, 'cleanup'):
                        self.ocr.cleanup()
                except Exception as e:
                    print(f"停止OCR服务时发生错误: {e}")
            
            # 停止系统托盘图标
            icon.stop()
            
            # 强制退出程序
            os._exit(0)
            
        except Exception as e:
            print(f"退出程序时发生错误: {e}")
            # 确保程序退出
            os._exit(1)
    
    def load_config(self):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        default_config = self.get_default_config()
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 确保所有必要的配置项都存在
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except Exception as e:
            print(f"加载配置文件失败: {e}")
        
        return default_config
    
    def save_config(self):
        """保存配置到文件"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            # 过滤掉不应该保存的临时字段（如 debug_log）
            config_to_save = {k: v for k, v in self.config.items() if k != 'debug_log'}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            print("配置已保存")
            
            # 通知OCR实例重新加载配置
            if self.ocr:
                self.ocr.config_queue.put(self.ocr.reload_config)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            "trigger_delay_ms": 300,
            "hotkey": "alt",
            "auto_copy": True,
            "show_debug": False,
            "debug_log": ""
        }
    
    def run(self):
        """运行系统托盘程序"""
        try:
            # 创建系统托盘图标
            # on_activate: 单击托盘图标时触发（打开设置）
            # menu: 右键菜单
            self.icon = pystray.Icon(
                "screen_ocr",
                self.create_icon(),
                "Screen OCR",
                menu=self.create_menu(),
                on_activate=self.on_left_click  # 左键单击打开设置
            )
            
            # 运行系统托盘
            self.icon.run()
        except Exception as e:
            print(f"系统托盘运行错误: {e}")
        finally:
            # 确保清理资源
            if self.icon:
                try:
                    self.icon.stop()
                except:
                    pass

    def show_help(self, icon, item):
        """触发显示帮助信息"""
        try:
            if self.ocr and hasattr(self.ocr, 'config_queue'):
                self.ocr.config_queue.put(self._create_help_window)
        except Exception as e:
            print(f"触发帮助窗口时发生错误: {e}")

    def _create_help_window(self):
        """在主线程中创建帮助窗口"""
        try:
            # 创建帮助窗口（在屏幕外，避免白色闪烁）
            help_window = ctk.CTkToplevel()
            help_window.geometry("+10000+10000")  # 屏幕外创建
            help_window.withdraw()
            help_window.title("Screen OCR 使用说明")
            
            # 创建主框架
            main_frame = ctk.CTkFrame(help_window, fg_color="transparent")
            main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)
            
            # 创建标题
            title_label = ctk.CTkLabel(
                main_frame,
                text="Screen OCR 使用说明",
                font=("Segoe UI", 20, "bold"),
                text_color="#1f538d"
            )
            title_label.pack(pady=(0, 20))
            
            # 创建文本框
            text = ctk.CTkTextbox(
                main_frame,
                wrap="word",
                font=("Microsoft YaHei UI", 11),
                width=440,
                height=250
            )
            text.pack(fill=tk.BOTH, expand=True)
            
            # 插入帮助文本
            help_text = """使用方法

• 按住快捷键（默认为ALT）不放，等待屏幕出现蓝色边框
• 继续按住直到识别完成（绿色边框）
• 拖动鼠标选择需要的文本，自动复制到剪贴板
• 松开快捷键即可退出

设置说明

• 左键点击托盘图标打开设置界面
• 可自定义快捷键（支持组合键如CTRL+SHIFT）
• 可选择OCR引擎和调整触发延时
"""
            text.insert("1.0", help_text)
            text.configure(state="disabled")  # 设置为只读
            
            # 计算居中位置并显示
            help_window.update_idletasks()
            
            # 获取屏幕尺寸（逻辑像素）
            screen_width = help_window.winfo_screenwidth()
            screen_height = help_window.winfo_screenheight()
            
            # 根据屏幕大小计算合适的窗口尺寸
            # 帮助窗口相对较小
            window_width = max(450, min(550, int(screen_width * 0.25)))
            window_height = max(350, min(450, int(screen_height * 0.40)))
            
            # 确保窗口不会超出屏幕（留出50px边距）
            max_width = screen_width - 100
            max_height = screen_height - 100
            window_width = min(window_width, max_width)
            window_height = min(window_height, max_height)
            
            # 居中计算，确保不溢出屏幕
            x = max(0, min((screen_width - window_width) // 2, screen_width - window_width))
            y = max(0, min((screen_height - window_height) // 2, screen_height - window_height))
            
            # 延迟显示（屏幕外渲染完成后再移动）
            def show_help():
                help_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
                help_window.deiconify()
                help_window.lift()
                help_window.focus_force()
                # 再次调整确保居中（窗口显示后可能会有内容调整）
                help_window.after(50, lambda: center_help_window(help_window))
            
            def center_help_window(window):
                """帮助窗口最终居中调整"""
                try:
                    window.update_idletasks()
                    
                    # 获取窗口实际大小
                    actual_width = window.winfo_width()
                    actual_height = window.winfo_height()
                    
                    # 获取屏幕尺寸
                    scr_width = window.winfo_screenwidth()
                    scr_height = window.winfo_screenheight()
                    
                    # 重新计算居中位置，确保不溢出屏幕
                    new_x = max(0, min((scr_width - actual_width) // 2, scr_width - actual_width))
                    new_y = max(0, min((scr_height - actual_height) // 2, scr_height - actual_height))
                    
                    # 设置最终位置
                    window.geometry(f"+{new_x}+{new_y}")
                except:
                    pass
            
            help_window.after(30, show_help)
            
        except Exception as e:
            print(f"创建帮助窗口时发生错误: {e}")

if __name__ == "__main__":
    tray = SystemTray()
    tray.run()
