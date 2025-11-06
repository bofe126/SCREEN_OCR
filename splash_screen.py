"""
启动画面和欢迎页面模块
提供首次启动引导和启动进度显示
"""
import tkinter as tk
import customtkinter as ctk
import threading
import time


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
        
        # 窗口尺寸
        window_width = 350
        window_height = 180
        
        # 居中显示
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 使用标准 tkinter 组件（避免 CustomTkinter 依赖问题）
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
        
        # 进度条容器
        progress_container = tk.Frame(main_frame, bg="#2b2b2b")
        progress_container.pack(pady=(0, 20))
        
        # 简单的进度条（使用 Canvas）
        self.progress_canvas = tk.Canvas(
            progress_container,
            width=280,
            height=8,
            bg="#404040",
            highlightthickness=0
        )
        self.progress_canvas.pack()
        
        # 进度条背景
        self.progress_bg = self.progress_canvas.create_rectangle(
            0, 0, 280, 8,
            fill="#404040",
            outline=""
        )
        
        # 进度条前景
        self.progress_fg = self.progress_canvas.create_rectangle(
            0, 0, 0, 8,
            fill="#1f538d",
            outline=""
        )
        
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
            if hasattr(self, 'progress_canvas') and hasattr(self, 'progress_fg'):
                width = int(280 * value)
                self.progress_canvas.coords(self.progress_fg, 0, 0, width, 8)
            
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
        self.root = ctk.CTkToplevel()
        self.root.withdraw()
        self.root.title("欢迎使用 Screen OCR")
        
        # 窗口尺寸
        window_width = 500
        window_height = 550
        
        # 居中显示
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(False, False)
        
        # 主容器
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=25)
        
        # 标题
        title_label = ctk.CTkLabel(
            main_frame,
            text="欢迎使用 Screen OCR",
            font=("Segoe UI", 24, "bold"),
            text_color="#1f538d"
        )
        title_label.pack(pady=(0, 10))
        
        # 副标题
        subtitle_label = ctk.CTkLabel(
            main_frame,
            text="快速识别屏幕上的文字",
            font=("Segoe UI", 12),
            text_color="gray"
        )
        subtitle_label.pack(pady=(0, 25))
        
        # 分隔线
        separator = ctk.CTkFrame(main_frame, height=2, fg_color="gray70")
        separator.pack(fill="x", pady=(0, 20))
        
        # 快速开始标题
        quick_start_label = ctk.CTkLabel(
            main_frame,
            text="快速开始",
            font=("Segoe UI", 16, "bold"),
            text_color="#1f538d"
        )
        quick_start_label.pack(anchor="w", pady=(0, 15))
        
        # 使用步骤
        steps = [
            ("1️⃣", "按住 ALT 键", "触发OCR识别功能"),
            ("2️⃣", "等待蓝色边框出现", "表示正在识别文字"),
            ("3️⃣", "拖动鼠标选择文字", "选中需要的文本内容"),
            ("4️⃣", "自动复制到剪贴板", "松开快捷键即可使用")
        ]
        
        for emoji, title, desc in steps:
            step_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            step_frame.pack(fill="x", pady=5)
            
            # 步骤编号
            emoji_label = ctk.CTkLabel(
                step_frame,
                text=emoji,
                font=("Segoe UI", 16),
                width=40
            )
            emoji_label.pack(side="left", padx=(0, 10))
            
            # 步骤内容
            content_frame = ctk.CTkFrame(step_frame, fg_color="transparent")
            content_frame.pack(side="left", fill="x", expand=True)
            
            title_label = ctk.CTkLabel(
                content_frame,
                text=title,
                font=("Segoe UI", 13, "bold"),
                anchor="w"
            )
            title_label.pack(anchor="w")
            
            desc_label = ctk.CTkLabel(
                content_frame,
                text=desc,
                font=("Segoe UI", 11),
                text_color="gray",
                anchor="w"
            )
            desc_label.pack(anchor="w")
        
        # 提示信息
        tip_frame = ctk.CTkFrame(main_frame, fg_color="#e3f2fd", corner_radius=8)
        tip_frame.pack(fill="x", pady=(20, 0))
        
        tip_label = ctk.CTkLabel(
            tip_frame,
            text="💡 提示：程序已最小化到系统托盘，点击托盘图标可打开设置",
            font=("Segoe UI", 11),
            text_color="#1976d2",
            wraplength=420
        )
        tip_label.pack(padx=15, pady=12)
        
        # 分隔线
        separator2 = ctk.CTkFrame(main_frame, height=2, fg_color="gray70")
        separator2.pack(fill="x", pady=(20, 15))
        
        # "不再显示"复选框
        self.dont_show_var = tk.BooleanVar(value=False)
        dont_show_cb = ctk.CTkCheckBox(
            main_frame,
            text="不再显示此欢迎页面",
            variable=self.dont_show_var,
            font=("Segoe UI", 12)
        )
        dont_show_cb.pack(anchor="w", pady=(0, 15))
        
        # 按钮容器
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 0))
        
        # 开始使用按钮
        start_button = ctk.CTkButton(
            button_frame,
            text="开始使用",
            font=("Segoe UI", 13, "bold"),
            width=150,
            height=40,
            command=self.on_start
        )
        start_button.pack(side="left", padx=(0, 10))
        
        # 详细设置按钮
        settings_button = ctk.CTkButton(
            button_frame,
            text="详细设置",
            font=("Segoe UI", 13),
            width=150,
            height=40,
            fg_color="gray60",
            hover_color="gray50",
            command=self.on_settings
        )
        settings_button.pack(side="left")
        
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
            font=("Segoe UI", 12, "bold"),
            bg="#2b2b2b",
            fg="#ffffff"
        )
        title_label.pack(pady=(15, 5))
        
        # 提示文本
        tip_label = tk.Label(
            frame,
            text=f"按 {self.hotkey} 键开始识别文字",
            font=("Segoe UI", 10),
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
    
    time.sleep(1)
    
    # 测试Toast通知
    print("测试Toast通知...")
    toast = StartupToast(hotkey="ALT")
    toast.show(duration_ms=3000)
    
    time.sleep(4)
    print("测试完成")
