"""
翻译弹窗模块
显示翻译结果的美观弹窗
"""
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *
import threading
import queue
import time
from typing import Optional, Callable, Tuple
import os


class TranslationPopup:
    """翻译结果弹窗"""
    
    def __init__(
        self,
        parent=None,
        position: Tuple[int, int] = None,
        on_close: Optional[Callable] = None
    ):
        """
        初始化翻译弹窗
        
        Args:
            parent: 父窗口
            position: 弹窗位置 (x, y)，None 则居中显示
            on_close: 关闭回调
        """
        self.parent = parent
        self.position = position
        self.on_close = on_close
        self.root: Optional[tk.Toplevel] = None
        self._is_destroyed = False
        self._animation_id = None
        self._update_check_id = None
        
        # 线程安全的更新队列
        self._update_queue: queue.Queue = queue.Queue()
        
        # UI 组件
        self.status_label = None
        self.source_text = None
        self.target_text = None
        self.copy_btn = None
        self.loading_dots = 0
        
    def show(self, source_text: str = ""):
        """
        显示弹窗
        
        Args:
            source_text: 原文
        """
        if self._is_destroyed:
            return
            
        # 创建窗口
        if self.parent:
            self.root = tk.Toplevel(self.parent)
        else:
            self.root = tk.Toplevel()
        
        self.root.withdraw()  # 先隐藏
        
        # 窗口属性
        self.root.overrideredirect(True)  # 无边框
        self.root.attributes('-topmost', True)  # 置顶
        
        # 设置透明度（支持渐入动画）
        self.root.attributes('-alpha', 0.0)
        
        # 创建 UI
        self._create_ui(source_text)
        
        # 更新窗口以计算实际所需大小
        self.root.update_idletasks()
        
        # 获取内容实际需要的大小
        window_width = max(400, self.root.winfo_reqwidth())
        window_height = self.root.winfo_reqheight()
        
        # 计算位置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if self.position:
            x, y = self.position
            # 尝试显示在选区右下方
            x = min(x + 20, screen_width - window_width - 20)
            y = min(y + 20, screen_height - window_height - 60)
            # 确保不超出左上角
            x = max(20, x)
            y = max(20, y)
        else:
            # 居中显示
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind('<Escape>', lambda e: self.close())
        
        # 点击窗口外部时关闭
        self.root.bind('<FocusOut>', self._on_focus_out)
        
        # 显示窗口并启动渐入动画
        self.root.deiconify()
        self.root.focus_force()  # 获取焦点
        self._fade_in()
        
        # 启动更新队列检查
        self._check_update_queue()
        
    def _create_ui(self, source_text: str):
        """创建 UI"""
        # 主容器 - 带圆角阴影效果
        main_frame = tk.Frame(
            self.root,
            bg="#1a1a2e",  # 深蓝紫色背景
            highlightbackground="#4a4a6a",
            highlightthickness=1
        )
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # 状态标签（隐藏，但保留引用以兼容现有代码）
        self.status_label = tk.Label(main_frame, bg="#1a1a2e")
        # 不 pack，保持隐藏
        
        # 内容区域
        content_frame = tk.Frame(main_frame, bg="#1a1a2e")
        content_frame.pack(fill="both", expand=True, padx=15, pady=(10, 5))
        
        # 原文标签
        source_title = tk.Label(
            content_frame,
            text="📝 原文",
            font=("Microsoft YaHei UI", 9),
            fg="#3282b8",
            bg="#1a1a2e",
            anchor="w"
        )
        source_title.pack(fill="x", pady=(0, 3))
        
        # 原文内容（直接显示文字，自动换行）
        self.source_text = tk.Label(
            content_frame,
            text=source_text,
            font=("Microsoft YaHei UI", 10),
            fg="#bbe1fa",
            bg="#1a1a2e",
            anchor="w",
            justify="left",
            wraplength=350  # 自动换行宽度
        )
        self.source_text.pack(fill="x", pady=(0, 10))
        
        # 译文标签
        target_title = tk.Label(
            content_frame,
            text="🔄 译文",
            font=("Microsoft YaHei UI", 9),
            fg="#4ecca3",
            bg="#1a1a2e",
            anchor="w"
        )
        target_title.pack(fill="x", pady=(0, 3))
        
        # 译文内容（直接显示文字）
        self.target_text = tk.Label(
            content_frame,
            text="正在翻译...",
            font=("Microsoft YaHei UI", 10),
            fg="#00ff00",  # 亮绿色，更醒目
            bg="#1a1a2e",
            anchor="nw",
            justify="left",
            wraplength=350
        )
        self.target_text.pack(fill="both", expand=True, pady=(0, 5))
        
        # 底部按钮区域
        button_frame = tk.Frame(main_frame, bg="#16213e", height=45)
        button_frame.pack(fill="x", side="bottom", padx=0, pady=0)
        button_frame.pack_propagate(False)  # 固定高度
        
        # 提示文本
        hint_label = tk.Label(
            button_frame,
            text="点击外部关闭",
            font=("Microsoft YaHei UI", 9),
            fg="#5a5a7a",
            bg="#16213e"
        )
        hint_label.pack(side="left", padx=10, pady=10)
        
        # 复制按钮
        self.copy_btn = tk.Label(
            button_frame,
            text="📋 复制",
            font=("Microsoft YaHei UI", 9),
            fg="#bbe1fa",
            bg="#3282b8",
            cursor="hand2",
            padx=12,
            pady=5
        )
        self.copy_btn.pack(side="right", padx=10, pady=8)
        self.copy_btn.bind("<Button-1>", lambda e: self._copy_translation())
        self.copy_btn.bind("<Enter>", lambda e: self.copy_btn.config(bg="#4a9fd4"))
        self.copy_btn.bind("<Leave>", lambda e: self.copy_btn.config(bg="#3282b8"))
        
        # 启动加载动画
        self._animate_loading()
        
    def _on_focus_out(self, event):
        """窗口失去焦点时关闭"""
        if self._is_destroyed or not self.root:
            return
        # 检查焦点是否转移到了窗口外部（不是子控件）
        try:
            focused = self.root.focus_get()
            # 如果焦点不在当前窗口的任何子控件上，关闭窗口
            if focused is None or not str(focused).startswith(str(self.root)):
                self.close()
        except:
            pass
    
    def _fade_in(self, alpha: float = 0.0):
        """渐入动画"""
        if self._is_destroyed or not self.root:
            return
            
        if alpha < 0.95:
            alpha += 0.1
            try:
                self.root.attributes('-alpha', alpha)
                self.root.after(20, lambda: self._fade_in(alpha))
            except:
                pass
        else:
            try:
                self.root.attributes('-alpha', 0.95)
            except:
                pass
    
    def _fade_out(self, alpha: float = 0.95, callback: Callable = None):
        """渐出动画"""
        if self._is_destroyed or not self.root:
            if callback:
                callback()
            return
            
        if alpha > 0.1:
            alpha -= 0.15
            try:
                self.root.attributes('-alpha', alpha)
                self.root.after(15, lambda: self._fade_out(alpha, callback))
            except:
                if callback:
                    callback()
        else:
            if callback:
                callback()
    
    def _animate_loading(self):
        """加载动画"""
        if self._is_destroyed or not self.root or not self.status_label:
            return
            
        dots = "." * (self.loading_dots % 4)
        try:
            current_text = self.status_label.cget("text")
            if "翻译中" in current_text:
                self.status_label.config(text=f"翻译中{dots}")
                self.loading_dots += 1
                self._animation_id = self.root.after(300, self._animate_loading)
        except:
            pass
    
    def _check_update_queue(self):
        """检查更新队列（在主线程中执行）"""
        if self._is_destroyed or not self.root:
            return
        
        try:
            # 处理队列中的所有更新
            while True:
                try:
                    update_type, data = self._update_queue.get_nowait()
                    if update_type == "translation":
                        self._do_update_translation(data)
                    elif update_type == "error":
                        self._do_show_error(data)
                except queue.Empty:
                    break
            
            # 继续检查
            self._update_check_id = self.root.after(50, self._check_update_queue)
        except:
            pass
    
    def update_translation(self, translated_text: str):
        """
        更新翻译结果（线程安全，可从任何线程调用）
        
        Args:
            translated_text: 翻译后的文本
        """
        if self._is_destroyed:
            return
        # 将更新请求放入队列
        self._update_queue.put(("translation", translated_text))
    
    def _do_update_translation(self, translated_text: str):
        """实际执行翻译结果更新（在主线程中调用）"""
        if self._is_destroyed or not self.root:
            return
            
        try:
            # 停止加载动画
            if self._animation_id:
                self.root.after_cancel(self._animation_id)
                self._animation_id = None
            
            # 更新译文（Label 控件）
            self.target_text.config(text=translated_text, fg="#00ff00")
            print(f"[翻译弹窗] 更新译文: {translated_text[:30]}...")
            
            # 自适应窗口大小
            self.root.update_idletasks()
            
            # 重新计算并调整窗口大小
            new_width = max(400, self.root.winfo_reqwidth())
            new_height = self.root.winfo_reqheight()
            
            # 获取当前位置
            current_x = self.root.winfo_x()
            current_y = self.root.winfo_y()
            
            # 确保不超出屏幕
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if current_x + new_width > screen_width - 20:
                current_x = max(20, screen_width - new_width - 20)
            if current_y + new_height > screen_height - 60:
                current_y = max(20, screen_height - new_height - 60)
            
            self.root.geometry(f"{new_width}x{new_height}+{current_x}+{current_y}")
        except:
            pass
    
    def show_error(self, error_msg: str):
        """
        显示错误信息（线程安全，可从任何线程调用）
        
        Args:
            error_msg: 错误信息
        """
        if self._is_destroyed:
            return
        # 将更新请求放入队列
        self._update_queue.put(("error", error_msg))
    
    def _do_show_error(self, error_msg: str):
        """实际执行错误显示（在主线程中调用）"""
        if self._is_destroyed or not self.root:
            return
            
        try:
            # 停止加载动画
            if self._animation_id:
                self.root.after_cancel(self._animation_id)
                self._animation_id = None
            
            # 更新译文区域显示错误（Label 控件）
            self.target_text.config(text=f"错误: {error_msg}", fg="#e94560")
        except:
            pass
    
    def _copy_translation(self):
        """复制翻译结果"""
        if self._is_destroyed or not self.root or not self.target_text:
            return
            
        try:
            text = self.target_text.cget("text")  # Label 获取文本方式
            if text and not text.startswith("正在翻译") and not text.startswith("错误"):
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                
                # 显示复制成功
                original_text = self.copy_btn.cget("text")
                self.copy_btn.config(text="✓ 已复制!", bg="#4ecca3")
                self.root.after(1500, lambda: self.copy_btn.config(text=original_text, bg="#3282b8") if not self._is_destroyed else None)
        except:
            pass
    
    def close(self):
        """关闭弹窗"""
        if self._is_destroyed:
            return
            
        self._is_destroyed = True
        
        # 停止动画
        if self._animation_id and self.root:
            try:
                self.root.after_cancel(self._animation_id)
            except:
                pass
            self._animation_id = None
        
        # 停止更新队列检查
        if self._update_check_id and self.root:
            try:
                self.root.after_cancel(self._update_check_id)
            except:
                pass
            self._update_check_id = None
        
        # 清空更新队列
        try:
            while not self._update_queue.empty():
                self._update_queue.get_nowait()
        except:
            pass
        
        # 渐出后销毁
        def _destroy():
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass
                self.root = None
            
            if self.on_close:
                self.on_close()
        
        if self.root:
            self._fade_out(callback=_destroy)
        else:
            _destroy()
    
    def is_alive(self) -> bool:
        """检查弹窗是否存活"""
        return not self._is_destroyed and self.root is not None


class TranslationManager:
    """翻译管理器 - 协调翻译流程"""
    
    def __init__(self):
        self.popup: Optional[TranslationPopup] = None
        self.translator = None
        self._is_translating = False
        
    def start_translation(
        self,
        text: str,
        position: Tuple[int, int] = None,
        parent=None,
        source_lang: str = "auto",
        target_lang: str = "zh",
        secret_id: str = "",
        secret_key: str = ""
    ):
        """
        开始翻译
        
        Args:
            text: 待翻译文本
            position: 弹窗位置
            parent: 父窗口
            source_lang: 源语言
            target_lang: 目标语言
            secret_id: API SecretId
            secret_key: API SecretKey
        """
        # 清理之前的弹窗
        self.cancel()
        
        # 导入翻译器
        from translator import get_translator
        self.translator = get_translator()
        
        # 配置凭证
        if secret_id and secret_key:
            self.translator.set_credentials(secret_id, secret_key)
        
        # 检查配置
        if not self.translator.is_configured():
            # 创建弹窗显示错误
            self.popup = TranslationPopup(
                parent=parent,
                position=position,
                on_close=self._on_popup_close
            )
            self.popup.show(text)
            self.popup.show_error("请在设置中配置腾讯云 API 密钥")
            return
        
        # 创建弹窗
        self.popup = TranslationPopup(
            parent=parent,
            position=position,
            on_close=self._on_popup_close
        )
        self.popup.show(text)
        
        self._is_translating = True
        
        # 开始异步翻译
        def on_success(translated: str):
            if self.popup and self.popup.is_alive():
                # update_translation 现在是线程安全的
                self.popup.update_translation(translated)
            self._is_translating = False
        
        def on_error(error: str):
            if self.popup and self.popup.is_alive():
                # show_error 现在是线程安全的
                self.popup.show_error(error)
            self._is_translating = False
        
        def on_cancel():
            self._is_translating = False
        
        self.translator.translate_async(
            text,
            source=source_lang,
            target=target_lang,
            on_success=on_success,
            on_error=on_error,
            on_cancel=on_cancel
        )
    
    def cancel(self):
        """取消翻译并关闭弹窗"""
        # 取消翻译请求
        if self.translator:
            self.translator.cancel()
        
        # 关闭弹窗
        if self.popup:
            self.popup.close()
            self.popup = None
        
        self._is_translating = False
    
    def _on_popup_close(self):
        """弹窗关闭回调"""
        if self.translator:
            self.translator.cancel()
        self._is_translating = False
        self.popup = None
    
    def is_active(self) -> bool:
        """检查是否有活动的翻译"""
        return self._is_translating or (self.popup and self.popup.is_alive())


# 全局翻译管理器
_translation_manager: Optional[TranslationManager] = None


def get_translation_manager() -> TranslationManager:
    """获取全局翻译管理器"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


if __name__ == "__main__":
    # 测试代码
    root = tk.Tk()
    root.withdraw()
    
    def test_popup():
        popup = TranslationPopup(parent=root)
        popup.show("Hello, World! This is a test message.")
        
        # 模拟翻译完成
        def simulate_translation():
            time.sleep(2)
            if popup.is_alive():
                popup.root.after(0, lambda: popup.update_translation("你好，世界！这是一条测试消息。"))
        
        threading.Thread(target=simulate_translation, daemon=True).start()
    
    root.after(100, test_popup)
    root.mainloop()

