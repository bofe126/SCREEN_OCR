"""
系统托盘模块（使用 ttkbootstrap）
"""
import os
import json
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
import pystray
from PIL import Image, ImageDraw, ImageFont
from cairosvg import svg2png
from io import BytesIO
from datetime import datetime
import logging
import sys


class GlobalLogBuffer:
    """全局日志缓冲区，用于捕捉和存储所有日志"""
    def __init__(self, max_lines=1000):
        self.buffer = []
        self.max_lines = max_lines
        self.text_widget = None
        self.original_stdout = None
        self.original_stderr = None
        self.log_handler = None
        
    def start_capture(self):
        """开始捕捉日志"""
        if self.original_stdout is None:
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            
            # 重定向 stdout
            class StdoutRedirector:
                def __init__(self, buffer, original):
                    self.buffer = buffer
                    self.original = original
                    
                def write(self, text):
                    if self.original:
                        self.original.write(text)
                        self.original.flush()
                    if text.strip():
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        self.buffer.add_log(f"{timestamp} - STDOUT - {text.strip()}")
                        
                def flush(self):
                    if self.original:
                        self.original.flush()
            
            # 重定向 stderr
            class StderrRedirector:
                def __init__(self, buffer, original):
                    self.buffer = buffer
                    self.original = original
                    
                def write(self, text):
                    if self.original:
                        self.original.write(text)
                        self.original.flush()
                    if text.strip():
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        self.buffer.add_log(f"{timestamp} - STDERR - {text.strip()}")
                        
                def flush(self):
                    if self.original:
                        self.original.flush()
            
            sys.stdout = StdoutRedirector(self, self.original_stdout)
            sys.stderr = StderrRedirector(self, self.original_stderr)
            
            # 添加 logging 处理器
            if self.log_handler is None:
                class BufferHandler(logging.Handler):
                    def __init__(self, buffer):
                        super().__init__()
                        self.buffer = buffer
                        
                    def emit(self, record):
                        try:
                            msg = self.format(record)
                            self.buffer.add_log(msg)
                        except:
                            pass
                
                self.log_handler = BufferHandler(self)
                self.log_handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
                self.log_handler.setFormatter(formatter)
                logging.getLogger().addHandler(self.log_handler)
    
    def add_log(self, message):
        """添加日志到缓冲区"""
        self.buffer.append(message)
        if len(self.buffer) > self.max_lines:
            self.buffer.pop(0)
        
        # 如果有连接的文本框，立即显示
        if self.text_widget:
            try:
                self.text_widget.configure(state='normal')
                self.text_widget.insert('end', message + '\n')
                self.text_widget.see('end')
                self.text_widget.configure(state='disabled')
            except:
                pass
    
    def connect_widget(self, text_widget):
        """连接文本框并显示历史日志"""
        self.text_widget = text_widget
        if text_widget:
            try:
                text_widget.configure(state='normal')
                text_widget.delete('1.0', 'end')
                # 显示所有历史日志
                for log in self.buffer:
                    text_widget.insert('end', log + '\n')
                text_widget.see('end')
                text_widget.configure(state='disabled')
            except:
                pass
    
    def clear(self):
        """清空缓冲区"""
        self.buffer.clear()


# 创建全局日志缓冲区实例
_global_log_buffer = GlobalLogBuffer()
# 程序启动时就开始捕捉日志
_global_log_buffer.start_capture()


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
            "image_preprocess": False,
            "ocr_engine": "wechat",
            "debug_log": "",
            # 翻译配置
            "enable_translation": True,
            "translation_source": "auto",
            "translation_target": "zh",
            "tencent_secret_id": "",
            "tencent_secret_key": ""
        }
        
        try:
            # 创建窗口
            self.root = tk.Toplevel()
            self.root.withdraw()
            self.root.title("Screen OCR 设置")
            
            # 设置图标
            try:
                icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
                    print("[设置页] 图标设置成功")
            except Exception as e:
                print(f"[设置页] 设置图标失败: {e}")
            
            # 窗口尺寸（紧凑版）
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            window_width = 480
            window_height = 720
            
            # 居中
            x = max(50, (screen_width - window_width) // 2)
            y = max(50, (screen_height - window_height) // 2)
            
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            self.root.minsize(450, 600)
            self.root.resizable(True, True)
            
            # 设置窗口关闭处理
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            self.setup_ui()
        except Exception as e:
            print(f"配置窗口初始化失败: {e}")
            if self.root:
                self.root.destroy()
            raise
    
    def setup_ui(self):
        """设置UI"""
        # 主容器（紧凑 padding）
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame,
            text="Screen OCR 设置",
            font=("Microsoft YaHei UI", 16, "bold"),
            foreground="#1f538d"
        )
        title_label.pack(pady=(0, 15))
        
        # 内容容器（直接显示，无滚动）
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 触发延时设置
        delay_label = ttk.Label(
            content_frame,
            text="触发延时 (ms)",
            font=("Microsoft YaHei UI", 11, "bold")
        )
        delay_label.pack(anchor="w", pady=(0, 4))
        
        delay_frame = ttk.Frame(content_frame)
        delay_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.delay_var = tk.IntVar(value=self.config.get("trigger_delay_ms", self.default_config["trigger_delay_ms"]))
        
        delay_scale = ttk_boot.Scale(
            delay_frame,
            from_=0,
            to=1000,
            variable=self.delay_var,
            orient=tk.HORIZONTAL,
            bootstyle="info",
            command=self.on_scale_change
        )
        delay_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.delay_display = ttk.Label(
            delay_frame,
            text=f"{self.delay_var.get()} ms",
            width=10,
            font=("Microsoft YaHei UI", 10)
        )
        self.delay_display.pack(side=tk.RIGHT)
        
        # 快捷键设置
        hotkey_label = ttk.Label(
            content_frame,
            text="触发快捷键",
            font=("Microsoft YaHei UI", 11, "bold")
        )
        hotkey_label.pack(anchor="w", pady=(0, 4))
        
        hotkey_frame = ttk.Frame(content_frame)
        hotkey_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", self.default_config["hotkey"]).upper())
        self.hotkey_button = ttk_boot.Button(
            hotkey_frame,
            text=f"{self.hotkey_var.get()}",
            bootstyle="secondary-outline",
            width=15,
            command=self.start_hotkey_record
        )
        self.hotkey_button.pack(side=tk.LEFT)
        
        self.recording_hotkey = False
        
        # 分隔线
        ttk.Separator(content_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # OCR 引擎选择
        ocr_label = ttk.Label(
            content_frame,
            text="OCR 引擎",
            font=("Microsoft YaHei UI", 11, "bold")
        )
        ocr_label.pack(anchor="w", pady=(0, 4))
        
        ocr_frame = ttk.Frame(content_frame)
        ocr_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.ocr_engine_var = tk.StringVar(value=self.config.get("ocr_engine", self.default_config["ocr_engine"]))
        
        wechat_rb = ttk_boot.Radiobutton(
            ocr_frame,
            text="微信 OCR (需确保已安装微信)",
            variable=self.ocr_engine_var,
            value="wechat",
            bootstyle="primary",
            command=self.update_config
        )
        wechat_rb.pack(anchor="w", pady=(0, 4))
        
        windows_rb = ttk_boot.Radiobutton(
            ocr_frame,
            text="Windows OCR (系统自带，推荐)",
            variable=self.ocr_engine_var,
            value="windows",
            bootstyle="primary",
            command=self.update_config
        )
        windows_rb.pack(anchor="w")
        
        # 分隔线
        ttk.Separator(content_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 翻译设置
        translate_label = ttk.Label(
            content_frame,
            text="翻译设置",
            font=("Microsoft YaHei UI", 11, "bold")
        )
        translate_label.pack(anchor="w", pady=(0, 4))
        
        # 启用翻译
        self.enable_translation_var = tk.BooleanVar(
            value=self.config.get("enable_translation", self.default_config["enable_translation"])
        )
        enable_translation_cb = ttk_boot.Checkbutton(
            content_frame,
            text="启用选中文字翻译",
            variable=self.enable_translation_var,
            bootstyle="round-toggle",
            command=self.update_config
        )
        enable_translation_cb.pack(anchor="w", pady=(0, 8))
        
        # 目标语言选择
        lang_frame = ttk.Frame(content_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(lang_frame, text="翻译为:", font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT, padx=(0, 10))
        
        self.translation_target_var = tk.StringVar(
            value=self.config.get("translation_target", self.default_config["translation_target"])
        )
        target_lang_combo = ttk_boot.Combobox(
            lang_frame,
            textvariable=self.translation_target_var,
            values=["zh", "en", "ja", "ko", "fr", "de", "es", "ru"],
            width=10,
            state="readonly"
        )
        target_lang_combo.pack(side=tk.LEFT)
        target_lang_combo.bind("<<ComboboxSelected>>", lambda e: self.update_config())
        
        # 语言名称提示
        lang_names = {"zh": "中文", "en": "英语", "ja": "日语", "ko": "韩语", 
                      "fr": "法语", "de": "德语", "es": "西班牙语", "ru": "俄语"}
        self.lang_hint = ttk.Label(
            lang_frame, 
            text=lang_names.get(self.translation_target_var.get(), ""),
            font=("Microsoft YaHei UI", 9),
            foreground="#666666"
        )
        self.lang_hint.pack(side=tk.LEFT, padx=(10, 0))
        
        def update_lang_hint(*args):
            self.lang_hint.config(text=lang_names.get(self.translation_target_var.get(), ""))
        self.translation_target_var.trace_add("write", update_lang_hint)
        
        # API 密钥设置
        api_label = ttk.Label(
            content_frame,
            text="腾讯云 API 密钥 (翻译功能需要)",
            font=("Microsoft YaHei UI", 10),
            foreground="#666666"
        )
        api_label.pack(anchor="w", pady=(5, 4))
        
        # SecretId
        id_frame = ttk.Frame(content_frame)
        id_frame.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(id_frame, text="SecretId:", width=10).pack(side=tk.LEFT)
        self.secret_id_var = tk.StringVar(
            value=self.config.get("tencent_secret_id", "")
        )
        secret_id_entry = ttk_boot.Entry(
            id_frame,
            textvariable=self.secret_id_var,
            width=35
        )
        secret_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        secret_id_entry.bind("<FocusOut>", lambda e: self.update_config())
        
        # SecretKey
        key_frame = ttk.Frame(content_frame)
        key_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(key_frame, text="SecretKey:", width=10).pack(side=tk.LEFT)
        self.secret_key_var = tk.StringVar(
            value=self.config.get("tencent_secret_key", "")
        )
        secret_key_entry = ttk_boot.Entry(
            key_frame,
            textvariable=self.secret_key_var,
            show="*",
            width=35
        )
        secret_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        secret_key_entry.bind("<FocusOut>", lambda e: self.update_config())
        
        # API 获取提示
        api_hint = ttk.Label(
            content_frame,
            text="💡 在腾讯云控制台 → 访问密钥 获取",
            font=("Microsoft YaHei UI", 9),
            foreground="#888888",
            cursor="hand2"
        )
        api_hint.pack(anchor="w", pady=(0, 5))
        api_hint.bind("<Button-1>", lambda e: self._open_tencent_console())
        
        # 分隔线
        ttk.Separator(content_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 复选框选项
        self.auto_copy_var = tk.BooleanVar(value=self.config.get("auto_copy", self.default_config["auto_copy"]))
        auto_copy_cb = ttk_boot.Checkbutton(
            content_frame,
            text="自动复制选中文本 (默认开启)",
            variable=self.auto_copy_var,
            bootstyle="round-toggle",
            command=self.update_config
        )
        auto_copy_cb.pack(anchor="w", pady=(0, 8))
        
        self.image_preprocess_var = tk.BooleanVar(
            value=self.config.get("image_preprocess", self.default_config.get("image_preprocess", False))
        )
        preprocess_cb = ttk_boot.Checkbutton(
            content_frame,
            text="图像预处理 (增强对比度+锐化)",
            variable=self.image_preprocess_var,
            bootstyle="round-toggle",
            command=self.update_config
        )
        preprocess_cb.pack(anchor="w", pady=(0, 8))
        
        self.show_debug_var = tk.BooleanVar(value=self.config.get("show_debug", self.default_config["show_debug"]))
        show_debug_cb = ttk_boot.Checkbutton(
            content_frame,
            text="显示调试信息 (默认关闭)",
            variable=self.show_debug_var,
            bootstyle="round-toggle",
            command=lambda: (self.toggle_debug_log(), self.update_config())
        )
        show_debug_cb.pack(anchor="w", pady=(0, 8))
        
        # 调试日志文本框容器
        self.debug_frame = ttk.Frame(content_frame)
        
        # 创建日志文本框
        self.debug_text = ScrolledText(
            self.debug_frame,
            height=12,
            wrap="word",
            autohide=True,
            bootstyle="secondary"
        )
        self.debug_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # 设置为只读
        self.debug_text.text.configure(state='disabled')
        
        # 日志按钮
        button_frame = ttk.Frame(self.debug_frame)
        button_frame.pack(fill=tk.X)
        
        clear_log_btn = ttk_boot.Button(
            button_frame,
            text="清空日志",
            bootstyle="warning-outline",
            command=self._clear_logs
        )
        clear_log_btn.pack(side=tk.LEFT)
        
        # 初始化日志处理器
        self.log_handler = None
        self.log_messages = []  # 存储日志消息
        self.original_stdout = None
        self.original_stderr = None
        
        # 如果启动时调试模式已开启，立即显示调试框
        if self.show_debug_var.get():
            self.debug_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            self._start_log_capture()
    
    def start_hotkey_record(self):
        """开始记录快捷键"""
        if not self.recording_hotkey:
            self.recording_hotkey = True
            self.hotkey_button.configure(text="按下快捷键...")
            self.pressed_keys = set()
            
            # 绑定键盘事件
            self.root.bind('<KeyPress>', self.on_hotkey_press)
            self.root.bind('<KeyRelease>', self.on_hotkey_release)
            self.hotkey_button.focus_set()
    
    def on_hotkey_press(self, event):
        """处理按键按下事件"""
        if not self.recording_hotkey:
            return
            
        key_names = {
            16: 'SHIFT', 17: 'CTRL', 18: 'ALT', 91: 'WIN',
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
            if hotkey and hotkey != "按下快捷键...":
                self.hotkey_var.set(hotkey)
                self.update_config()
            
            # 解绑键盘事件
            self.root.unbind('<KeyPress>')
            self.root.unbind('<KeyRelease>')
    
    def toggle_debug_log(self):
        """切换调试日志显示"""
        if self.show_debug_var.get():
            self.debug_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            self._start_log_capture()
        else:
            self._stop_log_capture()
            self.debug_frame.pack_forget()
    
    def _start_log_capture(self):
        """启动日志捕捉（连接到全局缓冲区）"""
        try:
            # 添加欢迎信息
            self.debug_text.text.configure(state='normal')
            self.debug_text.text.delete('1.0', 'end')
            welcome_msg = f"=== 调试日志窗口打开于 {datetime.now().strftime('%H:%M:%S')} ===\n"
            welcome_msg += "显示从程序启动以来的所有日志\n"
            self.debug_text.text.insert('1.0', welcome_msg)
            self.debug_text.text.configure(state='disabled')
            
            # 连接到全局日志缓冲区（会自动显示所有历史日志）
            _global_log_buffer.connect_widget(self.debug_text.text)
            
            # 标记已连接
            self.log_handler = True  # 标记为已连接
        except Exception as e:
            # 使用原始 stdout 输出错误（避免循环）
            try:
                sys.__stdout__.write(f"启动日志捕捉失败: {e}\n")
            except:
                pass
    
    def _stop_log_capture(self):
        """停止日志捕捉（断开与全局缓冲区的连接）"""
        try:
            # 断开与文本框的连接
            if self.log_handler:
                _global_log_buffer.connect_widget(None)
                self.log_handler = None
        except Exception as e:
            # 注意：这里可能 print 已经被重定向了，所以使用原始 stdout
            try:
                sys.__stdout__.write(f"停止日志捕捉失败: {e}\n")
            except:
                pass
    
    
    
    
    
    def _clear_logs(self):
        """清空日志"""
        try:
            # 清空全局缓冲区
            _global_log_buffer.clear()
            
            # 清空文本框
            self.debug_text.text.configure(state='normal')
            self.debug_text.text.delete('1.0', 'end')
            welcome_msg = f"=== 日志已清空于 {datetime.now().strftime('%H:%M:%S')} ===\n"
            self.debug_text.text.insert('1.0', welcome_msg)
            self.debug_text.text.configure(state='disabled')
            
            # 添加到缓冲区
            _global_log_buffer.add_log(welcome_msg.strip())
        except Exception as e:
            print(f"清空日志失败: {e}")
    
    def update_config(self):
        """实时更新配置"""
        self.config.update({
            "trigger_delay_ms": self.delay_var.get(),
            "hotkey": self.hotkey_var.get(),
            "auto_copy": self.auto_copy_var.get(),
            "image_preprocess": self.image_preprocess_var.get(),
            "show_debug": self.show_debug_var.get(),
            "ocr_engine": self.ocr_engine_var.get(),
            # 翻译配置
            "enable_translation": self.enable_translation_var.get(),
            "translation_target": self.translation_target_var.get(),
            "tencent_secret_id": self.secret_id_var.get(),
            "tencent_secret_key": self.secret_key_var.get(),
        })
        self.callback(self.config)
    
    def _open_tencent_console(self):
        """打开腾讯云控制台"""
        import webbrowser
        webbrowser.open("https://console.cloud.tencent.com/cam/capi")
    
    def on_scale_change(self, value):
        """处理滑块值变化"""
        current_value = int(float(value))
        snapped_value = round(current_value / 50) * 50
        
        if self.delay_var.get() != snapped_value:
            self.delay_var.set(snapped_value)
            self.delay_display.configure(text=f"{snapped_value} ms")
            self.update_config()
    
    def on_save(self):
        """保存按钮点击"""
        self.update_config()
        self.on_closing()
    
    def show(self):
        """显示配置对话框"""
        try:
            if self.root:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
        except Exception as e:
            print(f"显示配置窗口时发生错误: {e}")
            self.on_closing()
    
    def on_closing(self):
        """处理窗口关闭事件"""
        try:
            self._stop_log_capture()
            
            if self.root:
                try:
                    if self.root.winfo_exists():
                        self.callback(self.config)
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
        self.creating_dialog = False
        
        # 检查OCR实例
        if not self.ocr or not hasattr(self.ocr, 'config_queue'):
            raise RuntimeError("OCR实例必须提供config_queue")
    
    def _create_config_dialog(self):
        """在主线程中创建配置对话框"""
        try:
            # 防止重复创建
            if self.creating_dialog:
                return
            
            # 如果已有对话框且窗口仍然存在，将其提到前台
            if (self.dialog and hasattr(self.dialog, 'root') and 
                self.dialog.root and self.dialog.root.winfo_exists()):
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
            # 读取SVG文件
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
            with open(icon_path, 'rb') as f:
                svg_data = f.read()
            
            # 转换为PNG
            png_data = svg2png(bytestring=svg_data, output_width=20, output_height=20)
            
            # 创建带有白色背景的新图像
            background = Image.new('RGBA', (24, 24), color=(0, 0, 0, 0))
            
            # 创建圆角矩形遮罩
            mask = Image.new('L', (24, 24), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, 23, 23], radius=4, fill=255)
            
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
            return self._create_default_icon()
            
    def _create_default_icon(self):
        """创建默认的备用图标"""
        width = 24
        height = 24
        image = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        bg_color = (41, 128, 185)
        draw.rectangle([0, 0, width, height], fill=bg_color)
        
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
                icon.icon = self.create_icon()
                icon.menu = self.create_menu()
            
            self.ocr.config_queue.put(toggle)
    
    def on_left_click(self, icon):
        """处理托盘图标左键点击事件"""
        self.show_config(icon, None)
    
    def create_menu(self):
        """创建系统托盘菜单"""
        return pystray.Menu(
            pystray.MenuItem("设置", self.show_config, default=True),
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
            # 过滤掉不应该保存的临时字段
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
            "image_preprocess": False,
            "debug_log": "",
            # 翻译配置
            "enable_translation": True,
            "translation_source": "auto",
            "translation_target": "zh",
            "tencent_secret_id": "",
            "tencent_secret_key": ""
        }
    
    def run(self):
        """运行系统托盘程序"""
        try:
            self.icon = pystray.Icon(
                "screen_ocr",
                self.create_icon(),
                "Screen OCR",
                menu=self.create_menu(),
                on_activate=self.on_left_click
            )
            
            self.icon.run()
        except Exception as e:
            print(f"系统托盘运行错误: {e}")
        finally:
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
            # 创建帮助窗口
            help_window = tk.Toplevel()
            help_window.withdraw()
            help_window.title("Screen OCR 帮助")
            
            # 设置图标
            try:
                icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
                if os.path.exists(icon_path):
                    help_window.iconbitmap(icon_path)
                    print("[帮助页] 图标设置成功")
            except Exception as e:
                print(f"[帮助页] 设置图标失败: {e}")
            
            # 窗口尺寸
            window_width = 520
            window_height = 400
            
            # 居中显示
            screen_width = help_window.winfo_screenwidth()
            screen_height = help_window.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            
            help_window.geometry(f"{window_width}x{window_height}+{x}+{y}")
            help_window.resizable(False, False)
            
            # 主容器
            main_frame = ttk.Frame(help_window, padding=30)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = ttk.Label(
                main_frame,
                text="Screen OCR 使用说明",
                font=("Microsoft YaHei UI", 18, "bold"),
                foreground="#1f538d"
            )
            title_label.pack(pady=(0, 20))
            
            # 创建文本框
            text = ScrolledText(
                main_frame,
                height=15,
                wrap="word",
                autohide=True,
                bootstyle="secondary"
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
• 支持图像预处理以提高识别准确率

提示

• 识别效果取决于文字清晰度和对比度
• 建议在光线充足、文字清晰的环境下使用
• 如遇问题，可尝试调整触发延时或启用图像预处理
"""
            text.text.insert("1.0", help_text)
            text.text.configure(state="disabled")
            
            # 关闭按钮
            close_btn = ttk_boot.Button(
                main_frame,
                text="关闭",
                bootstyle="secondary",
                width=12,
                command=help_window.destroy
            )
            close_btn.pack(pady=(15, 0))
            
            # 显示窗口
            help_window.deiconify()
            help_window.lift()
            help_window.focus_force()
            
        except Exception as e:
            print(f"创建帮助窗口时发生错误: {e}")


if __name__ == "__main__":
    tray = SystemTray()
    tray.run()
