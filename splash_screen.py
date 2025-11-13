"""
启动画面和欢迎页面模块（使用 ttkbootstrap）
提供首次启动引导和启动进度显示
"""
import os
import sys
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *
import threading
import time
from PIL import Image, ImageTk


class SplashScreen:
    """启动画面类 - 使用 Toplevel 避免阻塞主程序"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.root = None
        self.progress_bar = None
        self.status_label = None
        self.progress_value = 0
        self._running = False
        
    def show(self):
        """显示启动画面"""
        if self._running:
            return
            
        self._running = True
        
        # 如果有父窗口，使用 Toplevel；否则创建独立窗口
        if self.parent:
            self.root = tk.Toplevel(self.parent)
        else:
            # 创建临时的隐藏主窗口
            temp_root = tk.Tk()
            temp_root.withdraw()
            self.root = tk.Toplevel(temp_root)
            self.temp_root = temp_root
        
        self.root.withdraw()  # 先隐藏
        
        # 设置窗口属性
        self.root.overrideredirect(True)  # 无边框
        self.root.attributes('-topmost', True)  # 置顶
        
        # 设置图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        # 窗口尺寸
        window_width = 350
        window_height = 180
        
        # 居中显示
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 背景框架
        bg_frame = tk.Frame(self.root, bg="#2b2b2b", relief="flat")
        bg_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # 主容器
        main_frame = tk.Frame(bg_frame, bg="#2b2b2b")
        main_frame.pack(fill="both", expand=True)
        
        # Logo和标题
        title_label = tk.Label(
            main_frame,
            text="📋 Screen OCR",
            font=("Segoe UI", 24, "bold"),
            fg="#1f538d",
            bg="#2b2b2b"
        )
        title_label.pack(pady=(30, 10))
        
        # 状态文本
        self.status_label = tk.Label(
            main_frame,
            text="正在启动...",
            font=("Segoe UI", 12),
            fg="#b0b0b0",
            bg="#2b2b2b"
        )
        self.status_label.pack(pady=(0, 15))
        
        # 进度条
        self.progress_bar = ttk_boot.Progressbar(
            main_frame,
            mode='determinate',
            length=280,
            bootstyle="info"
        )
        self.progress_bar.pack(pady=(0, 20))
        
        # 版本信息
        version_label = tk.Label(
            main_frame,
            text="v1.0.0",
            font=("Segoe UI", 10),
            fg="#666666",
            bg="#2b2b2b"
        )
        version_label.pack(pady=(0, 15))
        
        # 显示窗口
        self.root.deiconify()
        self.root.update()
        
    def update_progress(self, value, status_text=""):
        """更新进度
        
        Args:
            value: 进度值 0-1
            status_text: 状态文本
        """
        if not self._running or not self.root:
            return
            
        try:
            self.progress_value = value
            
            # 更新进度条
            if self.progress_bar:
                self.progress_bar['value'] = value * 100
            
            # 更新状态文本
            if status_text and self.status_label:
                self.status_label.configure(text=status_text)
            
            self.root.update()
        except:
            pass
    
    def close(self, delay_ms=500):
        """关闭启动画面
        
        Args:
            delay_ms: 延迟关闭时间（毫秒）
        """
        if not self._running or not self.root:
            return
        
        # 使用 after 在主线程中延迟关闭
        def _close():
            if self.root:
                try:
                    self.root.destroy()
                    self.root = None
                except:
                    pass
            self._running = False
        
        # 在主线程中延迟执行
        self.root.after(delay_ms, _close)


class WelcomePage:
    """欢迎页面类（首次启动显示）"""
    
    def __init__(self, config, on_close_callback=None):
        self.config = config
        self.on_close_callback = on_close_callback
        self.root = None
        self.dont_show_var = None
        
    def show(self):
        """显示欢迎页面"""
        # 创建窗口
        self.root = tk.Toplevel()
        self.root.withdraw()
        self.root.title("欢迎使用 Screen OCR")
        
        # 设置图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                print("[欢迎页] 图标设置成功")
        except Exception as e:
            print(f"[欢迎页] 设置图标失败: {e}")
        
        # 窗口尺寸（极致紧凑）
        window_width = 400
        window_height = 410
        
        # 居中显示
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(False, False)
        
        # 键盘快捷键
        self.root.bind('<Return>', lambda e: self.on_start())
        self.root.bind('<Escape>', lambda e: self.on_start())
        
        # 主容器（极小 padding，底部最小）
        main_frame = ttk.Frame(self.root, padding=(15, 10, 15, 3))
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 应用图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path)
                icon_img = icon_img.resize((40, 40), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(icon_img)
                
                icon_label = ttk.Label(main_frame, image=photo)
                icon_label.image = photo  # 保持引用
                icon_label.pack(pady=(0, 4))
        except Exception as e:
            print(f"[欢迎页] 加载图标图片失败: {e}")
        
        # 标题
        title_label = ttk.Label(
            main_frame,
            text="欢迎使用 Screen OCR",
            font=("Microsoft YaHei UI", 15, "bold"),
            foreground="#1f538d"
        )
        title_label.pack(pady=(0, 2))
        
        # 副标题
        subtitle_label = ttk.Label(
            main_frame,
            text="快速识别屏幕上的文字",
            font=("Microsoft YaHei UI", 9),
            foreground="#666666"
        )
        subtitle_label.pack(pady=(0, 8))
        
        # 分隔线
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=(12, 10))
        
        # 快速开始标题
        quick_start_label = ttk.Label(
            main_frame,
            text="快速开始",
            font=("Microsoft YaHei UI", 11, "bold"),
            foreground="#1f538d"
        )
        quick_start_label.pack(anchor="w", pady=(0, 5))
        
        # 获取实际快捷键
        actual_hotkey = self.config.get("hotkey", "ALT").upper()
        
        # 精简步骤 - 合并为 3 步
        steps = [
            ("1️⃣", f"按住 {actual_hotkey} 键不放，开始识别，等待蓝色边框变绿"),
            ("2️⃣", "识别完成后，拖动鼠标选择需要的文字"),
            ("3️⃣", "文字自动复制到剪贴板，松开快捷键退出")
        ]
        
        for emoji, text in steps:
            step_frame = ttk.Frame(main_frame)
            step_frame.pack(fill=tk.X, pady=1)
            
            # 步骤编号
            emoji_label = ttk.Label(
                step_frame,
                text=emoji,
                font=("Segoe UI", 10),
                width=3
            )
            emoji_label.pack(side=tk.LEFT, padx=(0, 4))
            
            # 步骤文字（单行）
            text_label = ttk.Label(
                step_frame,
                text=text,
                font=("Microsoft YaHei UI", 9),
                wraplength=320
            )
            text_label.pack(side=tk.LEFT, anchor="w", fill=tk.X, expand=True)
        
        # 分隔线
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=(12, 10))
        
        # "不再显示"复选框（使用 ttkbootstrap 样式）
        self.dont_show_var = tk.BooleanVar(value=False)
        dont_show_cb = ttk_boot.Checkbutton(
            main_frame,
            text="不再显示此欢迎页面",
            variable=self.dont_show_var,
            bootstyle="round-toggle"
        )
        dont_show_cb.pack(anchor="w", pady=(0, 5))
        
        # 按钮容器
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 4))
        
        # 开始使用按钮（带快捷键提示）
        start_button = ttk_boot.Button(
            button_frame,
            text="开始使用 (Enter)",
            bootstyle="primary",
            width=18,
            command=self.on_start
        )
        start_button.pack(side=tk.LEFT, padx=(0, 10))
        start_button.focus_set()  # 默认焦点
        
        # 详细设置按钮
        settings_button = ttk_boot.Button(
            button_frame,
            text="详细设置",
            bootstyle="secondary-outline",
            width=15,
            command=self.on_settings
        )
        settings_button.pack(side=tk.LEFT)
        
        # 分隔线
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=(12, 10))
        
        # 提示文字（按钮下方，靠左显示）
        tip_label = ttk.Label(
            main_frame,
            text="💡 程序已在系统托盘运行，点击图标打开设置",
            font=("Microsoft YaHei UI", 9),
            foreground="#999999"
        )
        tip_label.pack(anchor="w", pady=(0, 0))
        
        # 设置窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_start)
        
        # 显示窗口
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        
    def on_start(self):
        """开始使用按钮点击"""
        # 保存"不再显示"设置
        if self.dont_show_var and self.dont_show_var.get():
            self.config["show_welcome"] = False
        
        # 关闭窗口
        if self.root:
            self.root.destroy()
        
        # 调用回调
        if self.on_close_callback:
            self.on_close_callback(show_settings=False)
    
    def on_settings(self):
        """详细设置按钮点击"""
        # 保存"不再显示"设置
        if self.dont_show_var and self.dont_show_var.get():
            self.config["show_welcome"] = False
        
        # 关闭窗口
        if self.root:
            self.root.destroy()
        
        # 调用回调并打开设置
        if self.on_close_callback:
            self.on_close_callback(show_settings=True)


class StartupToast:
    """启动通知类（老用户简短提示）"""
    
    def __init__(self, hotkey="ALT"):
        self.hotkey = hotkey
        self.root = None
        
    def show(self, duration_ms=3000):
        """显示启动通知
        
        Args:
            duration_ms: 显示时长（毫秒）
        """
        # 创建窗口
        self.root = tk.Tk()
        self.root.withdraw()
        
        # 设置窗口属性
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)
        
        # 窗口尺寸
        window_width = 320
        window_height = 90
        
        # 右下角显示
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - window_width - 20
        y = screen_height - window_height - 60  # 留出任务栏空间
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 背景框架
        frame = tk.Frame(self.root, bg="#2b2b2b", relief="flat", bd=2)
        frame.pack(fill="both", expand=True)
        
        # 标题
        title_label = tk.Label(
            frame,
            text="📋 Screen OCR 已启动",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        title_label.pack(pady=(15, 5))
        
        # 提示文本
        tip_label = tk.Label(
            frame,
            text=f"按 {self.hotkey} 键开始识别文字",
            font=("Microsoft YaHei UI", 10),
            bg="#2b2b2b",
            fg="#b0b0b0"
        )
        tip_label.pack(pady=(0, 15))
        
        # 显示窗口
        self.root.deiconify()
        self.root.update()
        
        # 自动关闭
        def auto_close():
            time.sleep(duration_ms / 1000)
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass
        
        threading.Thread(target=auto_close, daemon=True).start()


if __name__ == "__main__":
    # 测试启动画面
    print("测试启动画面...")
    splash = SplashScreen()
    splash.show()
    
    # 模拟启动过程
    steps = [
        (0.2, "初始化配置..."),
        (0.4, "设置键盘钩子..."),
        (0.6, "加载OCR引擎..."),
        (0.8, "创建系统托盘..."),
        (1.0, "启动完成！")
    ]
    
    for progress, status in steps:
        time.sleep(0.6)
        splash.update_progress(progress, status)
    
    time.sleep(0.5)
    splash.close()
    
    time.sleep(1)
    
    # 测试欢迎页面
    print("测试欢迎页面...")
    config = {"show_welcome": True}
    
    def on_close(show_settings=False):
        print(f"欢迎页面关闭，打开设置: {show_settings}")
        print(f"配置: {config}")
    
    welcome = WelcomePage(config, on_close)
    welcome.show()
    
    # 等待窗口关闭
    if welcome.root:
        welcome.root.mainloop()
