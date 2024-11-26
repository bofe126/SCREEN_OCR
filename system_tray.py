import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext
import pystray
from PIL import Image, ImageDraw, ImageTk
import ctypes
from keyboard import read_hotkey
import queue
import threading
import win32api

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
        engine_combo['values'] = ("PaddleOCR (默认)", "Tesseract")
        if self.engine_var.get() == "PaddleOCR":
            engine_combo.set("PaddleOCR (默认)")
        engine_combo.grid(row=current_row, column=0, sticky="ew", pady=(0, 15))
        current_row += 1
        
        # 触发延时设置
        delay_label = ttk.Label(main_frame, text="触发延时 (ms)", font=ModernTheme.BOLD_FONT)
        delay_label.grid(row=current_row, column=0, sticky="w", pady=(0, 5))
        current_row += 1
        
        self.delay_var = tk.StringVar(value=str(self.config.get("trigger_delay_ms", self.default_config["trigger_delay_ms"])))
        delay_spin = ttk.Spinbox(main_frame, 
                               from_=0, 
                               to=1000, 
                               increment=50,
                               textvariable=self.delay_var,
                               font=ModernTheme.NORMAL_FONT)
        if self.delay_var.get() == "300":
            delay_spin.delete(0, tk.END)
            delay_spin.insert(0, "300 (默认)")
        delay_spin.grid(row=current_row, column=0, sticky="ew", pady=(0, 15))
        current_row += 1
        
        # 快捷键设置
        hotkey_label = ttk.Label(main_frame, text="触发快捷键", font=ModernTheme.BOLD_FONT)
        hotkey_label.grid(row=current_row, column=0, sticky="w", pady=(0, 5))
        current_row += 1
        
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", self.default_config["hotkey"]).upper())
        self.hotkey_button = ttk.Button(main_frame, 
                                      text=f"{self.hotkey_var.get()} (点击修改)", 
                                      command=self.record_hotkey,
                                      style="TButton")
        self.hotkey_button.grid(row=current_row, column=0, sticky="ew", pady=(0, 15))
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

        # 按钮容器
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=current_row + 1, column=0, sticky="e", pady=(25, 0))
        
        # 按钮
        cancel_btn = ttk.Button(button_frame, text="取消", command=self.root.destroy)
        cancel_btn.pack(side="right", padx=(0, 5))
        
        save_btn = ttk.Button(button_frame, text="保存", command=self.save_config)
        save_btn.pack(side="right")
    
    def record_hotkey(self):
        """记录快捷键"""
        self.hotkey_button.configure(text="请按下快捷键...")
        self.root.update()
        
        # 创建一个新窗口来捕获按键
        dialog = tk.Toplevel(self.root)
        dialog.title("设置快捷键")
        dialog.geometry("300x150")
        dialog.transient(self.root)  # 设置为主窗口的临时窗口
        dialog.grab_set()  # 模态窗口
        
        # 当前按下的键
        pressed_keys = set()
        key_names = {
            16: 'SHIFT',
            17: 'CTRL',
            18: 'ALT',
            91: 'WIN',
        }
        
        label = ttk.Label(dialog, text="请按下快捷键组合\n支持 CTRL、ALT、SHIFT、WIN 等组合键", justify="center")
        label.pack(pady=20)
        
        key_label = ttk.Label(dialog, text="", justify="center")
        key_label.pack(pady=10)
        
        def on_key_down(event):
            key = event.keycode
            if key in key_names:
                pressed_keys.add(key_names[key])
            else:
                key_char = event.char.upper()
                if key_char and key_char.isprintable():
                    pressed_keys.add(key_char)
            
            # 更新显示
            if pressed_keys:
                key_text = "+".join(sorted(pressed_keys))
                key_label.configure(text=key_text)
        
        def on_key_up(event):
            key = event.keycode
            if key in key_names and key_names[key] in pressed_keys:
                pressed_keys.remove(key_names[key])
            else:
                key_char = event.char.upper()
                if key_char and key_char.isprintable() and key_char in pressed_keys:
                    pressed_keys.remove(key_char)
            
            # 如果所有键都释放了，保存组合键
            if not pressed_keys:
                hotkey = key_label.cget("text")
                if hotkey:
                    self.hotkey_var.set(hotkey)
                    self.hotkey_button.configure(text=f"{hotkey} (点击修改)")
                dialog.destroy()
        
        dialog.bind('<KeyPress>', on_key_down)
        dialog.bind('<KeyRelease>', on_key_up)
        dialog.focus_set()
    
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

    def save_config(self):
        self.config.update({
            "ocr_engine": self.engine_var.get(),
            "trigger_delay_ms": int(self.delay_var.get().split()[0]),  # 移除默认值显示
            "hotkey": self.hotkey_var.get(),
            "auto_copy": self.auto_copy_var.get(),
            "show_debug": self.show_debug_var.get(),
            "debug_log": self.debug_text.get('1.0', 'end-1c') if self.show_debug_var.get() else ""
        })
        self.callback(self.config)
        self.root.destroy()
    
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
            if self.root:
                self.root.destroy()
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
            # 如果已有对话框，将其提到前台
            if self.dialog and hasattr(self.dialog, 'root') and self.dialog.root.winfo_exists():
                self.dialog.root.lift()
                self.dialog.root.focus_force()
                return
            
            # 创建新的对话框
            self.dialog = ConfigDialog(self.config, self.on_config_changed)
            self.dialog.show()
            
        except Exception as e:
            print(f"创建配置窗口时发生错误: {e}")
    
    def show_config(self, icon, item):
        """触发显示配置对话框"""
        try:
            if self.ocr and hasattr(self.ocr, 'config_queue'):
                self.ocr.config_queue.put(self._create_config_dialog)
        except Exception as e:
            print(f"触发配置窗口时发生错误: {e}")
    
    def create_icon(self):
        """创建系统托盘图标"""
        # 创建一个 22x22 的图标
        width = 22
        height = 22
        
        # 创建一个新的图像，使用透明背景
        image = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 绘制一个简单的 "OCR" 图标
        # 外圆
        margin = 2
        draw.ellipse([margin, margin, width-margin, height-margin],
                    outline=(52, 152, 219),  # 使用现代蓝色
                    width=2)
        
        # 添加文字
        from PIL import ImageFont
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except:
            font = ImageFont.load_default()
            
        # 在圆圈中央绘制 "OCR" 文字
        text = "OCR"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        draw.text((x, y), text, fill=(52, 152, 219), font=font)
        
        return image
    
    def toggle_service(self, icon, item):
        """切换OCR服务状态"""
        if self.ocr:
            def toggle():
                self.ocr.toggle_enabled()
                # 更新菜单项文本
                enabled = self.ocr.enabled
                item.text = "禁用服务" if enabled else "启用服务"
                # 更新图标
                icon.icon = self.create_icon()
            
            # 将任务添加到OCR实例的配置队列
            self.ocr.config_queue.put(toggle)
    
    def create_menu(self):
        """创建系统托盘菜单"""
        return pystray.Menu(
            pystray.MenuItem("设置", self.show_config),
            pystray.MenuItem("禁用服务", self.toggle_service),
            pystray.MenuItem("退出", self.quit)
        )
    
    def quit(self, icon, item):
        """退出程序"""
        try:
            # 关闭配置窗口
            if self.dialog and hasattr(self.dialog, 'root'):
                try:
                    self.dialog.root.destroy()
                except:
                    pass
            
            # 停止OCR服务
            if self.ocr:
                try:
                    self.ocr.cleanup()  # 使用新的cleanup方法
                except Exception as e:
                    print(f"停止OCR服务时发生错误: {e}")
            
            # 停止系统托盘图标
            if self.icon:
                self.icon.stop()
                
            # 退出主程序
            if self.ocr and hasattr(self.ocr, 'root'):
                self.ocr.root.quit()
                
        except Exception as e:
            print(f"退出程序时发生错误: {e}")
            # 确保程序退出
            import sys
            sys.exit(1)
    
    def on_config_changed(self, new_config):
        """配置更改回调"""
        try:
            self.config = new_config
            self.save_config()
        except Exception as e:
            print(f"保存配置时发生错误: {e}")
    
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
