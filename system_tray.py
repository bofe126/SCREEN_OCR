import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext
import pystray
from PIL import Image, ImageDraw, ImageFont, ImageTk
import ctypes
from keyboard import read_hotkey
import queue
import threading
import win32api
from cairosvg import svg2png
from io import BytesIO

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
            "ocr_engine": "PaddleOCR",
            "trigger_delay_ms": 300,
            "hotkey": "alt",
            "auto_copy": True,
            "show_debug": False,
            "debug_log": ""
        }
        
        try:
            # 设置高DPI支持
            HighDPIApp.set_dpi_awareness()
            
            self.root = tk.Toplevel()
            self.root.title("Screen OCR 设置")
            
            # 获取DPI缩放比例
            dpi_scale = HighDPIApp.get_dpi_scale(self.root)
            
            # 设置窗口大小和位置（考虑DPI缩放）
            base_width = 400
            base_height = 600
            window_width = int(base_width * dpi_scale)
            window_height = int(base_height * dpi_scale)
            
            # 获取真实的屏幕尺寸
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # 获取工作区尺寸（排除任务栏等）
            try:
                from win32api import GetMonitorInfo, MonitorFromPoint
                monitor_info = GetMonitorInfo(MonitorFromPoint((0,0)))
                work_area = monitor_info.get("Work")
                if work_area:
                    screen_width = work_area[2] - work_area[0]  # 工作区宽度
                    screen_height = work_area[3] - work_area[1]  # 工作区高度
                    # 计算窗口位置（考虑工作区偏移）
                    x = work_area[0] + (screen_width - window_width) // 2
                    y = work_area[1] + (screen_height - window_height) // 2
            except:
                # 如果获取失败，使用简单的居中计算
                x = (screen_width - window_width) // 2
                y = (screen_height - window_height) // 2
            
            # 确保窗口完全显示在屏幕内
            x = max(0, min(x, screen_width - window_width))
            y = max(0, min(y, screen_height - window_height))
            
            # 微调窗口位置，稍微向左偏移
            x = max(0, x - int(window_width * 0.1))  # 向左偏移窗口宽度的10%
            
            # 设置窗口大小和位置
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            self.root.resizable(False, False)
            
            # 设置窗口关闭处理
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # 应用现代主题
            ModernTheme.apply(self.root)
            
            self.setup_ui()
        except Exception as e:
            print(f"配置窗口初始化失败: {e}")
            if self.root:
                self.root.destroy()
            raise
    
    def setup_ui(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding="30 25 30 25")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Screen OCR 设置", style="Title.TLabel")
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 25))
        
        current_row = 1
        
        # OCR引擎选择
        engine_label = ttk.Label(main_frame, text="OCR引擎", font=ModernTheme.BOLD_FONT)
        engine_label.grid(row=current_row, column=0, sticky="w", pady=(0, 5))
        current_row += 1
        
        self.engine_var = tk.StringVar(value=self.config.get("ocr_engine", self.default_config["ocr_engine"]))
        engine_combo = ttk.Combobox(main_frame, textvariable=self.engine_var, state="readonly", font=ModernTheme.NORMAL_FONT)
        engine_combo['values'] = ("PaddleOCR", "Tesseract")
        if self.engine_var.get() == "PaddleOCR":
            engine_combo.set("PaddleOCR")
        engine_combo.grid(row=current_row, column=0, sticky="ew", pady=(0, 15))
        current_row += 1
        
        # 触发延时设置
        delay_label = ttk.Label(main_frame, text="触发延时 (ms)", font=ModernTheme.BOLD_FONT)
        delay_label.grid(row=current_row, column=0, sticky="w", pady=(0, 5))
        current_row += 1
        
        # 创建延时设置的容器框架
        delay_frame = ttk.Frame(main_frame)
        delay_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 15))
        delay_frame.columnconfigure(0, weight=1)  # 让滑块占据主要空间
        
        # 创建滑块
        self.delay_var = tk.IntVar(value=self.config.get("trigger_delay_ms", self.default_config["trigger_delay_ms"]))
        delay_scale = ttk.Scale(
            delay_frame,
            from_=0,
            to=1000,
            orient="horizontal",
            variable=self.delay_var,
            command=self.on_scale_change
        )
        # 添��鼠标点击事件处理
        delay_scale.bind('<Button-1>', self.on_scale_click)
        delay_scale.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # 创建数值显示框
        self.delay_display = ttk.Label(
            delay_frame,
            text=f"{self.delay_var.get()} ms",
            width=8,  # 改回8，因为只显示数值和单位
            anchor="e",
            font=ModernTheme.NORMAL_FONT
        )
        self.delay_display.grid(row=0, column=1, sticky="e")
        
        current_row += 1
        
        # 快捷键设置
        hotkey_label = ttk.Label(main_frame, text="触发快捷键", font=ModernTheme.BOLD_FONT)
        hotkey_label.grid(row=current_row, column=0, sticky="w", pady=(0, 5))
        current_row += 1
        
        # 创建快捷键输入框架
        hotkey_frame = ttk.Frame(main_frame)
        hotkey_frame.grid(row=current_row, column=0, sticky="ew", pady=(0, 15))
        
        # 创建快捷键显示/输入标签
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", self.default_config["hotkey"]).upper())
        self.hotkey_label = ttk.Label(
            hotkey_frame,
            text=f"{self.hotkey_var.get()}",
            font=ModernTheme.NORMAL_FONT,
            background=ModernTheme.BG_COLOR,
            foreground=ModernTheme.ACCENT_COLOR,
            padding=(5, 2)
        )
        self.hotkey_label.grid(row=0, column=0, sticky="w")
        hotkey_frame.columnconfigure(0, weight=1)
        
        # 绑定事件
        self.hotkey_label.bind('<Button-1>', self.start_hotkey_record)
        self.recording_hotkey = False
        
        current_row += 1
        
        # 分隔线
        separator = ttk.Separator(main_frame, orient="horizontal")
        separator.grid(row=current_row, column=0, sticky="ew", pady=15)
        current_row += 1
        
        # 复选框
        self.auto_copy_var = tk.BooleanVar(value=self.config.get("auto_copy", self.default_config["auto_copy"]))
        auto_copy_cb = ttk.Checkbutton(main_frame, 
                                     text="自动复制选中文本 (默认开启)", 
                                     variable=self.auto_copy_var,
                                     style="TCheckbutton")
        auto_copy_cb.grid(row=current_row, column=0, sticky="w", pady=(0, 8))
        current_row += 1
        
        self.show_debug_var = tk.BooleanVar(value=self.config.get("show_debug", self.default_config["show_debug"]))
        show_debug_cb = ttk.Checkbutton(main_frame, 
                                      text="显示调试信息 (默认关闭)", 
                                      variable=self.show_debug_var,
                                      command=self.toggle_debug_log,
                                      style="TCheckbutton")
        show_debug_cb.grid(row=current_row, column=0, sticky="w", pady=(0, 8))
        current_row += 1
        
        # 调试日志文本框容器
        self.debug_frame = ttk.Frame(main_frame)
        self.debug_text = tk.Text(self.debug_frame, width=40, height=8, font=ModernTheme.NORMAL_FONT)
        
        # 保存当前行号，用于调试框的位置
        self.last_row = current_row

        # 为其他控件添加变更事件处理
        engine_combo.bind('<<ComboboxSelected>>', lambda e: self.update_config())
        
        # 自动复制选项变更事件
        auto_copy_cb.configure(command=self.update_config)
        
        # 调试显示选项变更事件
        show_debug_cb.configure(command=lambda: (self.toggle_debug_log(), self.update_config()))
    
    def start_hotkey_record(self, event):
        """开始记录快捷键"""
        if not self.recording_hotkey:
            self.recording_hotkey = True
            self.hotkey_label.configure(text="按下快捷键组合...", background=ModernTheme.HOVER_COLOR)
            self.pressed_keys = set()
            
            # 绑定键盘事件到主窗口
            self.root.bind('<KeyPress>', self.on_hotkey_press)
            self.root.bind('<KeyRelease>', self.on_hotkey_release)
            self.hotkey_label.focus_set()

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
            self.hotkey_label.configure(text=key_text)

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
            hotkey = self.hotkey_label.cget("text")
            if hotkey and hotkey != "按下快捷键组合...":
                self.hotkey_var.set(hotkey)
                # 实时更新配置
                self.update_config()
            
            # 恢复标签样式
            self.hotkey_label.configure(background=ModernTheme.BG_COLOR)
            # 解绑键盘事件
            self.root.unbind('<KeyPress>')
            self.root.unbind('<KeyRelease>')
    
    def toggle_debug_log(self):
        if self.show_debug_var.get():
            # 显示调试日志框
            self.debug_frame.grid(row=self.last_row, column=0, sticky="nsew", pady=(0, 8))
            self.debug_text.grid(row=0, column=0, sticky="nsew")
            scrollbar = ttk.Scrollbar(self.debug_frame, orient="vertical", command=self.debug_text.yview)
            scrollbar.grid(row=0, column=1, sticky="ns")
            self.debug_text.configure(yscrollcommand=scrollbar.set)
            
            # 设置调试框的大小
            self.debug_frame.columnconfigure(0, weight=1)
            self.debug_frame.rowconfigure(0, weight=1)
            self.debug_text.configure(height=8)
            
            # 更新窗口大小后重新计算位置
            self.root.update_idletasks()
            self.center_window()
        else:
            # 隐藏调试日志框
            self.debug_frame.grid_remove()
            # 更新窗口大小后重新计算位置
            self.root.update_idletasks()
            self.center_window()

    def center_window(self):
        # 获取DPI缩放比例
        dpi_scale = HighDPIApp.get_dpi_scale(self.root)
        
        # 获取窗口当前大小
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 获取屏幕工作区域（排除任务栏）
        monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromWindow(self.root.winfo_id()))
        work_area = monitor_info["Work"]
        screen_width = work_area[2] - work_area[0]
        screen_height = work_area[3] - work_area[1]
        
        # 计算窗口位置，稍微向左偏移以平衡视觉效果
        x = work_area[0] + (screen_width - window_width) // 2 - int(50 * dpi_scale)
        y = work_area[1] + (screen_height - window_height) // 2
        
        # 确保窗口完全在屏幕内
        x = max(work_area[0], min(x, work_area[2] - window_width))
        y = max(work_area[1], min(y, work_area[3] - window_height))
        
        # 设置窗口位置
        self.root.geometry(f"+{x}+{y}")

    def update_config(self):
        """实时更新配置"""
        self.config.update({
            "ocr_engine": self.engine_var.get(),
            "trigger_delay_ms": self.delay_var.get(),
            "hotkey": self.hotkey_var.get(),
            "auto_copy": self.auto_copy_var.get(),
            "show_debug": self.show_debug_var.get(),
            "debug_log": self.debug_text.get('1.0', 'end-1c') if self.show_debug_var.get() else ""
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
            # 将窗口置于最前
            self.root.lift()
            self.root.focus_force()
            
            # 运行主循环
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"显示配置窗口时发生错误: {e}")
            self.on_closing()
            
    def on_closing(self):
        """处理窗口关闭事件"""
        try:
            if self.root and self.root.winfo_exists():
                # 发送一个空的配置更新，通知SystemTray清理对话框
                self.callback(self.config)
                self.root.quit()
                self.root.destroy()
                self.root = None
        except Exception as e:
            print(f"关闭窗口时发生错误: {e}")

class SystemTray:
    def __init__(self, ocr_instance=None):
        self.config = self.load_config()
        self.icon = None
        self.dialog = None
        self.ocr = ocr_instance
        
        # 检查OCR实例
        if not self.ocr or not hasattr(self.ocr, 'config_queue'):
            raise RuntimeError("OCR实例必须提供config_queue")
    
    def _create_config_dialog(self):
        """在主线程中创建配置对话框"""
        try:
            # 如果已有对话框且窗口仍然存在，将其提到前台
            if (self.dialog and hasattr(self.dialog, 'root') and 
                self.dialog.root and self.dialog.root.winfo_exists()):
                self.dialog.root.lift()
                self.dialog.root.focus_force()
                return
            
            # 确保之前的对话框被正确清理
            if self.dialog:
                try:
                    if hasattr(self.dialog, 'root') and self.dialog.root:
                        self.dialog.root.quit()
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
                        self.dialog.root.quit()
                        self.dialog.root.destroy()
                except:
                    pass
                self.dialog = None

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
    
    def create_menu(self):
        """创建系统托盘菜单"""
        return pystray.Menu(
            pystray.MenuItem("设置", self.show_config),
            pystray.MenuItem("启动服务", self.toggle_service, checked=lambda item: self.ocr and self.ocr.enabled),
            pystray.MenuItem("退出", self.quit)
        )
    
    def quit(self, icon, item):
        """退出程序"""
        try:
            # 关闭配置窗口
            if self.dialog and hasattr(self.dialog, 'root') and self.dialog.root.winfo_exists():
                try:
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
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print("配置已保存")
            
            # 通知OCR实例重新加载配置
            if self.ocr:
                self.ocr.config_queue.put(self.ocr.reload_config)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            "ocr_engine": "PaddleOCR",
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
            self.icon = pystray.Icon(
                "screen_ocr",
                self.create_icon(),
                "Screen OCR",
                self.create_menu()
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

if __name__ == "__main__":
    tray = SystemTray()
    tray.run()
