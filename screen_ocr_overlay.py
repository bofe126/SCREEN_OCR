import win32api
import win32gui
import win32con
import win32ui
import ctypes
from ctypes import wintypes
import pytesseract
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
import logging
import traceback
from bs4 import BeautifulSoup
import time
from paddleocr import PaddleOCR
import numpy as np
import queue
import threading
import sys

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ScreenOCRTool:
    # 默认配置常量
    DEFAULT_CONFIG = {
        "ocr_engine": "PaddleOCR",
        "trigger_delay_ms": 300,
        "hotkey": "ALT",
        "auto_copy": True,
        "show_debug": False,
        "debug_log": ""
    }
    
    def __init__(self):
        print("初始化程序...")
        # 设置高DPI支持
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
            except:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()  # 旧版API
                except:
                    pass
        
        # 添加配置队列和状态标志
        self.config_queue: queue.Queue = queue.Queue()
        self.enabled: bool = True  # 默认启用服务
        
        # 初始化主窗口
        self.root = tk.Tk()
        self.root.withdraw()
        
        # 初始化状态
        self.is_processing: bool = False
        self.current_screenshot = None
        self._running: bool = True
        self.key_press_time: float = 0
        self.cleanup_pending: bool = False
        
        # 获取系统DPI缩放和屏幕尺寸
        self.dpi_scale: float = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        
        # 使用tkinter获取实际屏幕尺寸
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        print(f"系统DPI缩放: {self.dpi_scale}")
        print(f"屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
        # 设置键盘钩子
        self.keyboard_hook_id = None
        print("开始设置键盘钩子...")
        self.setup_keyboard_hook()
        print("键盘钩子设置完成")
        
        # 设置 Tesseract 路径
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # 添加选择模式配置
        self.selection_mode: str = 'text'  # 'text' 或 'region'
        
        # 初始化OCR相关属性
        self._paddle_ocr = None
        self._ocr_engine: str = self.DEFAULT_CONFIG["ocr_engine"]
        self.trigger_delay_ms: int = self.DEFAULT_CONFIG["trigger_delay_ms"]
        self.hotkey: str = self.DEFAULT_CONFIG["hotkey"]
        self.pressed_keys: set = set()

        # 定义虚拟键码映射
        self.key_mapping = {
            # 控制键
            'ctrl': [162, 163],     # 左右CTRL键
            'alt': [164, 165],      # 左右ALT键
            'shift': [160, 161],    # 左右SHIFT键
            'win': [91, 92],        # 左右WIN键
            
            # 功能键
            'f1': [112], 'f2': [113], 'f3': [114], 'f4': [115],
            'f5': [116], 'f6': [117], 'f7': [118], 'f8': [119],
            'f9': [120], 'f10': [121], 'f11': [122], 'f12': [123],
            
            # 数字键
            '0': [48], '1': [49], '2': [50], '3': [51], '4': [52],
            '5': [53], '6': [54], '7': [55], '8': [56], '9': [57],
            
            # 字母键
            'a': [65], 'b': [66], 'c': [67], 'd': [68], 'e': [69],
            'f': [70], 'g': [71], 'h': [72], 'i': [73], 'j': [74],
            'k': [75], 'l': [76], 'm': [77], 'n': [78], 'o': [79],
            'p': [80], 'q': [81], 'r': [82], 's': [83], 't': [84],
            'u': [85], 'v': [86], 'w': [87], 'x': [88], 'y': [89],
            'z': [90],
            
            # 特殊键
            'space': [32],          # 空格键
            'tab': [9],            # Tab键
            'enter': [13],         # 回车键
            'backspace': [8],      # 退格键
            'delete': [46],        # 删除键
            'esc': [27],           # ESC键
            'capslock': [20],      # 大写锁定键
            
            # 方向键
            'up': [38],            # 上箭头
            'down': [40],          # 下箭头
            'left': [37],          # 左箭头
            'right': [39],         # 右箭头
            
            # 其他常用键
            'home': [36],          # Home键
            'end': [35],           # End键
            'pageup': [33],        # PageUp键
            'pagedown': [34],      # PageDown键
            'insert': [45],        # Insert键
            'printscreen': [44],   # PrintScreen键
            'scrolllock': [145],   # ScrollLock键
            'pause': [19],         # Pause键
        }
        
    @property
    def paddle_ocr(self):
        """延迟初始化PaddleOCR实例"""
        if self._paddle_ocr is None and self._ocr_engine == "PaddleOCR":
            import logging
            logging.getLogger("ppocr").setLevel(logging.WARNING)  # 设置日志级别为WARNING
            self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)  # 关闭PaddleOCR的日志
        return self._paddle_ocr

    def validate_config(self, config: dict) -> bool:
        """验证配置值的合法性"""
        try:
            if not isinstance(config["trigger_delay_ms"], int) or config["trigger_delay_ms"] < 0:
                print("错误：trigger_delay_ms 必须是非负整数")
                return False
            if not isinstance(config["hotkey"], str) or not config["hotkey"]:
                print("错误：hotkey 必须是非空字符串")
                return False
            if config["ocr_engine"] not in ["PaddleOCR", "Tesseract"]:
                print("错误：不支持的 OCR 引擎")
                return False
            return True
        except KeyError as e:
            print(f"错误：缺少必要的配置项 {e}")
            return False

    def init_ocr_engine(self):
        """初始化OCR引擎"""
        try:
            # 清理现有的OCR引擎
            if hasattr(self, '_paddle_ocr'):
                self._paddle_ocr = None

            # 根据配置初始化OCR引擎
            if self._ocr_engine == "PaddleOCR":
                print("初始化PaddleOCR引擎...")
                self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            print(f"OCR引擎已设置为: {self._ocr_engine}")
        except Exception as e:
            print(f"初始化OCR引擎失败: {str(e)}")

    def setup_keyboard_hook(self):
        """设置全局键盘钩子"""
        try:
            user32 = ctypes.WinDLL('user32', use_last_error=True)
            
            # 定义键盘钩子结构
            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [
                    ('vkCode', wintypes.DWORD),
                    ('scanCode', wintypes.DWORD),
                    ('flags', wintypes.DWORD),
                    ('time', wintypes.DWORD),
                    ('dwExtraInfo', wintypes.PULONG)
                ]
            
            def keyboard_hook_proc(nCode, wParam, lParam):
                """统一的键盘钩子处理函数"""
                try:
                    if nCode >= 0:
                        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                        
                        hotkey_parts = self.hotkey.lower().split('+')
                        
                        # 获取当前按键的虚拟键码集合
                        current_key_codes = set()
                        for key in hotkey_parts:
                            if key in self.key_mapping:
                                current_key_codes.update(self.key_mapping[key])
                        
                        # 检查是否是配置的快捷键
                        if kb.vkCode in current_key_codes:
                            # 按键按下 (WM_KEYDOWN 或 WM_SYSKEYDOWN)
                            if wParam in (win32con.WM_KEYDOWN, win32con.WM_SYSKEYDOWN):
                                # 新增：如果已经在处理中或事件周期活动中，直接返回
                                if self.is_processing:
                                    return user32.CallNextHookEx(None, nCode, wParam, lParam)
                                # 将按键添加到已按下的按键集合中
                                self.pressed_keys.add(kb.vkCode)

                                # 只有当所有配置的按键都被按下时才开始计时
                                if all(any(code in self.pressed_keys for code in self.key_mapping.get(key, [])) for key in hotkey_parts):
                                    self.key_press_time = time.time()
                            
                            # 按键松开 (WM_KEYUP 或 WM_SYSKEYUP)
                            elif wParam in (win32con.WM_KEYUP, win32con.WM_SYSKEYUP):
                                # 从已按下的按键集合中移除
                                self.pressed_keys.discard(kb.vkCode)
                                
                                # 重置计时器和状态
                                #if not self.is_processing:
                                self.key_press_time = 0                   
                                self.is_processing = False
                                self.cleanup_pending = True
                except Exception as e:
                    print(f"键盘钩子处理错误: {str(e)}")
                    if hasattr(e, '__traceback__'):
                        traceback.print_tb(e.__traceback__)
                
                # 正确调用CallNextHookEx
                return user32.CallNextHookEx(None, nCode, wParam, lParam)
            
            # 保存keyboard_proc作为实例属性以防止被垃圾回收
            HOOKPROC = ctypes.CFUNCTYPE(
                ctypes.c_long,
                ctypes.c_int,
                wintypes.WPARAM,
                ctypes.POINTER(KBDLLHOOKSTRUCT)
            )
            
            self.keyboard_proc = HOOKPROC(keyboard_hook_proc)
            
            # 修改这里：正确处理模块句柄
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE
            kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            module_handle = kernel32.GetModuleHandleW(None)
            
            # 设置钩子
            user32.SetWindowsHookExW.argtypes = [
                ctypes.c_int,
                HOOKPROC,
                wintypes.HINSTANCE,
                wintypes.DWORD
            ]
            user32.SetWindowsHookExW.restype = wintypes.HHOOK
            
            # 使用正确转换的模块句柄
            self.keyboard_hook_id = user32.SetWindowsHookExW(
                win32con.WH_KEYBOARD_LL,
                self.keyboard_proc,
                module_handle,
                0
            )
            
            if not self.keyboard_hook_id:
                error = ctypes.get_last_error()
                print(f"设置键盘钩子失败，错误码: {error}")
                raise Exception(f"无法设置键盘钩子，错误码: {error}")
            else:
                print("键盘钩子设置成功")
                
        except Exception as e:
            logging.error(f"设置键盘钩子失败: {str(e)}")
            raise

    def capture_screen_region(self, width, height):
        """捕获屏幕区域"""
        hwnd = None
        hwndDC = None
        mfcDC = None
        saveDC = None
        saveBitMap = None
        try:
            # 获取当前屏幕的完整区域
            monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0,0)))
            monitor_area = monitor_info["Monitor"]
            real_width = monitor_area[2] - monitor_area[0]
            real_height = monitor_area[3] - monitor_area[1]
            
            print(f"\n=== 屏幕捕获参数 ===")
            print(f"显示器区域: {monitor_area}")
            print(f"实际捕获尺寸: {real_width}x{real_height}")
            
            # 获取整个桌面窗口
            hwnd = win32gui.GetDesktopWindow()
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, real_width, real_height)
            saveDC.SelectObject(saveBitMap)
            
            # 捕获整个屏幕区域，包括任务栏
            saveDC.BitBlt(
                (0, 0), 
                (real_width, real_height), 
                mfcDC, 
                (monitor_area[0], monitor_area[1]), 
                win32con.SRCCOPY
            )
            
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            image = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            print(f"最终截图尺寸: {image.size}")
            print(f"图像模式: {image.mode}")
            print(f"图像像素: {image.size[0] * image.size[1]}")
            return image
        except Exception as e:
            logging.error(f"屏幕捕获失败: {str(e)}")
            return None
        finally:
            # 确保所有资源都被清理
            if saveDC:
                saveDC.DeleteDC()
            if mfcDC:
                mfcDC.DeleteDC()
            if hwndDC and hwnd:
                win32gui.ReleaseDC(hwnd, hwndDC)
            if saveBitMap:
                win32gui.DeleteObject(saveBitMap.GetHandle())

    def get_text_positions(self, image):
        """获取文字位置信息"""
        try:
            if self._ocr_engine == "PaddleOCR":
                return self._get_text_positions_paddle(image)
            else:
                return self._get_text_positions_tesseract(image)
        except Exception as e:
            logging.error(f"OCR处理失败: {str(e)}")
            return []

    def _get_text_positions_paddle(self, image):
        """使用PaddleOCR获取文字位置"""
        try:
            # 转换图像为numpy数组
            if isinstance(image, Image.Image):
                image = np.array(image)
            
            result = []
            # 进行OCR识别
            ocr_result = self.paddle_ocr.ocr(image, cls=True)
            
            for line in ocr_result:
                for word_info in line:
                    # 获取坐标和文本
                    box = word_info[0]  # 四个角点坐标
                    text = word_info[1][0]  # 文本内容
                    confidence = word_info[1][1]  # 置信度
                    
                    # 计算边界框
                    x1 = min(point[0] for point in box)
                    y1 = min(point[1] for point in box)
                    x2 = max(point[0] for point in box)
                    y2 = max(point[1] for point in box)
                    
                    # 计算每个字符的宽度
                    if len(text) > 0:
                        char_width = (x2 - x1) / len(text)
                        
                        # 为每个字符创建单独的文本块
                        for i, char in enumerate(text):
                            char_x = x1 + i * char_width
                            result.append({
                                'text': char,
                                'x': int(char_x),
                                'y': int(y1),
                                'width': int(char_width),
                                'height': int(y2 - y1)
                            })
            
            return result
            
        except Exception as e:
            logging.error(f"PaddleOCR处理失败: {str(e)}")
            return []

    def _get_text_positions_tesseract(self, image):
        """使用Tesseract获取文字位置（原有的实现）"""
        try:
            hocr_data = pytesseract.image_to_pdf_or_hocr(
                image,
                extension='hocr',
                lang='chi_sim+eng',
                config='--psm 3'
            ).decode('utf-8')
            
            soup = BeautifulSoup(hocr_data, 'html.parser')
            result = []
            
            for word in soup.find_all(class_='ocrx_word'):
                if word.get('title'):
                    coords = word['title'].split(';')[0]
                    bbox = coords.split('bbox ')[1].split()
                    x1, y1, x2, y2 = map(int, bbox)
                    text = word.get_text()
                    
                    # 计算每个字符的宽度
                    if len(text) > 0:
                        char_width = (x2 - x1) / len(text)
                        
                        # 为每个字符创建单独的文本块
                        for i, char in enumerate(text):
                            char_x = x1 + i * char_width
                            result.append({
                                'text': char,
                                'x': int(char_x),
                                'y': y1,
                                'width': int(char_width),
                                'height': y2 - y1
                            })
            
            return result
            
        except Exception as e:
            logging.error(f"Tesseract处理失败: {str(e)}")
            return []

    def should_add_space(self, prev_block, next_block, min_gap=10):
        if not prev_block or not next_block:
            return False
        
        prev_text = prev_block['text'].strip()
        next_text = next_block['text'].strip()
        if not prev_text or not next_text:
            return False
        
        # 获取两个文本块之间的间距
        gap = next_block['x'] - (prev_block['x'] + prev_block['width'])
        
        # 如果间距小于阈值，不添加空格
        if gap < min_gap:
            return False
        
        # 定义标点符号集合
        punctuation = set(',.:;?!，。：；？！、（）()[]【】{}""\'\'')
        
        # 获取前后字符
        prev_char = prev_text[-1]
        next_char = next_text[0]
        
        # 如果任一字符是标点，不添加空格
        if prev_char in punctuation or next_char in punctuation:
            return False
        
        # 检查是否是中文字符
        def is_chinese(char):
            return '\u4e00' <= char <= '\u9fff'
        
        # 如果前后都是中文，不添加空格
        if is_chinese(prev_char) and is_chinese(next_char):
            return False
        
        # 检查数字
        def is_digit(char):
            return char.isdigit()
        
        # 如果都是数字，不添加空格
        if is_digit(prev_char) and is_digit(next_char):
            return False
        
        # 如果一个是字母，一个是数字，添加空格
        if (prev_char.isalpha() and is_digit(next_char)) or \
           (is_digit(prev_char) and next_char.isalpha()):
            return True
        
        # 如果都是字母，添加空格
        if prev_char.isalpha() and next_char.isalpha():
            return True
        
        return False

    def merge_text_blocks(self, selected_blocks):
        if not selected_blocks:
            return ""
        
        # 获取选中的文本块
        blocks = [self.text_blocks[block_id] for block_id in selected_blocks]
        
        # 按垂直位置分组
        lines = {}
        for block in blocks:
            # 计算文本块的垂直中心点
            center_y = (block['y'] + block['height']) / 2
            
            # 查找匹配的行（允许5像素的垂直偏差）
            matched_line = None
            for line_y in lines.keys():
                if abs(center_y - line_y) <= 5:
                    matched_line = line_y
                    break
            
            # 如果没有匹配的行，创建新行
            if matched_line is None:
                lines[center_y] = []
            else:
                center_y = matched_line
            
            lines[center_y].append(block)
        
        # 对每一行的文本块按x坐标排序
        result = []
        for y in sorted(lines.keys()):
            line_blocks = lines[y]
            line_blocks.sort(key=lambda b: b['x'])  # 按x坐标排序
            
            # 合并同一行的文本，用空格分隔
            line_text = ''
            for i, block in enumerate(line_blocks):
                if i > 0:
                    prev_block = line_blocks[i-1]
                    if self.should_add_space(prev_block, block):
                        line_text += ' '
                line_text += block['text'].strip()
            
            result.append(line_text)
        
        # 用换行符连接不同行
        return '\n'.join(result)

    def create_highlight_layer(self, canvas, selected_blocks):
        """创建统一的高亮图层"""
        if not selected_blocks:
            return
        
        # 获取所有选中块的边界
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for block_id in selected_blocks:
            block = self.text_blocks[block_id]
            x1, y1, x2, y2 = block['x'], block['y'], block['x'] + block['width'], block['y'] + block['height']
            min_x = min(min_x, x1)
            min_y = min(min_y, y1)
            max_x = max(max_x, x2)
            max_y = max(max_y, y2)
        
        # 创建一个空白图像作为高亮层
        width = int(max_x - min_x + 4)  # 额外的2像素边距
        height = int(max_y - min_y + 4)
        highlight = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(highlight)
        
        # 在高亮层上绘制所有选中区域
        for block_id in selected_blocks:
            block = self.text_blocks[block_id]
            x1, y1, x2, y2 = block['x'], block['y'], block['x'] + block['width'], block['y'] + block['height']
            # 调整坐标到相对位置
            rect_x1 = int(x1 - min_x)
            rect_y1 = int(y1 - min_y)
            rect_x2 = int(x2 - min_x)
            rect_y2 = int(y2 - min_y)
            # 使用统一的颜色和透明度
            draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2],
                         fill=(77, 148, 255, 77))  # #4D94FF with 30% opacity
        
        # 转换为PhotoImage并显示
        highlight_photo = ImageTk.PhotoImage(highlight)
        # 保存引用防止被垃圾回收
        if hasattr(self, 'highlight_photo'):
            del self.highlight_photo
        self.highlight_photo = highlight_photo
        
        # 清除之前的高亮
        canvas.delete('highlight')
        
        # 创建新的高亮层
        canvas.create_image(
            int(min_x - 2), int(min_y - 2),  # 考虑边距
            image=highlight_photo,
            anchor='nw',
            tags='highlight'
        )

    def show_overlay_text(self, text_blocks):
        """显示文本覆盖层"""
        try:
            if hasattr(self, 'overlay_window') and self.overlay_window:
                try:
                    self.overlay_window.destroy()
                except:
                    pass
            
            print("\n=== 显示覆盖层 ===")
            print(f"屏幕尺寸: {self.screen_width}x{self.screen_height}")
            if self.current_screenshot:
                print(f"截图尺寸: {self.current_screenshot.size}")
            
            # 获取当前屏幕的完整区域
            monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0,0)))
            monitor_area = monitor_info["Monitor"]
            screen_x = monitor_area[0]
            screen_y = monitor_area[1]
            screen_width = monitor_area[2] - monitor_area[0]
            screen_height = monitor_area[3] - monitor_area[1]
            
            print(f"显示器区域: {monitor_area}")
            print(f"窗口位置和大小: {screen_width}x{screen_height}+{screen_x}+{screen_y}")
            
            # 创建新窗口
            self.overlay_window = tk.Toplevel()
            self.overlay_window.withdraw()  # 先隐藏窗口，等设置完成后再显示
            
            # 设置窗口属性
            self.overlay_window.attributes('-topmost', True)
            self.overlay_window.overrideredirect(True)  # 移除窗口边框
            
            # 设置窗口大小和位置以覆盖整个屏幕
            self.overlay_window.geometry(f"{screen_width}x{screen_height}+{screen_x}+{screen_y}")
            
            # 配置grid布局
            self.overlay_window.grid_rowconfigure(0, weight=1)
            self.overlay_window.grid_columnconfigure(0, weight=1)
            
            # 创建画布
            canvas = tk.Canvas(
                self.overlay_window,
                highlightthickness=0,
                bg='white',
                width=screen_width,
                height=screen_height,
                cursor='wait' if not text_blocks else 'arrow'  # 根据是否有文本块决定光标样式
            )
            canvas.grid(row=0, column=0, sticky='nsew')
            
            # 显示截图作为背景
            if self.current_screenshot:
                # 确保截图大小与窗口匹配
                if self.current_screenshot.size != (screen_width, screen_height):
                    print(f"调整截图大小从 {self.current_screenshot.size} 到 {screen_width}x{screen_height}")
                    self.current_screenshot = self.current_screenshot.resize((screen_width, screen_height))
                photo = ImageTk.PhotoImage(self.current_screenshot)
                canvas.photo = photo
                canvas.create_image(0, 0, image=photo, anchor='nw')
            
            # 显示窗口
            self.overlay_window.deiconify()
            self.overlay_window.lift()
            self.overlay_window.focus_force()
            
            # 如果没有文本块，说明是等待状态，直接返回
            if not text_blocks:
                return
            
            # 初始化选择相关的变量
            self.selection_start = None
            self.text_blocks = {}
            self.selected_blocks = set()
            
            # 存储文本块信息
            for i, block in enumerate(text_blocks):
                self.text_blocks[i] = {
                    'text': block['text'],
                    'x': block['x'],
                    'y': block['y'],
                    'width': block['width'],
                    'height': block['height'],
                    'selected': False
                }
            
            # OCR识别完成后，将光标设置为默认箭头
            canvas.configure(cursor='arrow')
            
            def on_mouse_down(event):
                self.selection_start = (event.x, event.y)
                # 清除之前的选择
                self.selected_blocks.clear()
                canvas.delete('highlight')
            
            def on_mouse_drag(event):
                if not self.selection_start:
                    return
                
                x1, y1 = self.selection_start
                x2, y2 = event.x, event.y
                
                # 确定选择区域
                min_x = min(x1, x2)
                max_x = max(x1, x2)
                min_y = min(y1, y2)
                max_y = max(y1, y2)
                
                # 清除之前的选中状态
                self.selected_blocks.clear()
                
                # 检查每个文本块
                for block_id, block in self.text_blocks.items():
                    bx1, by1, bx2, by2 = block['x'], block['y'], block['x'] + block['width'], block['y'] + block['height']
                    
                    # 检查是否与选择区域相交
                    if not (max_x < bx1 or min_x > bx2 or max_y < by1 or min_y > by2):
                        self.selected_blocks.add(block_id)
                
                # 创建新的高亮层
                self.create_highlight_layer(canvas, self.selected_blocks)
            
            def on_mouse_up(event):
                if self.selection_start and self.selected_blocks:
                    # 使用新的文本合并逻辑
                    text = self.merge_text_blocks(self.selected_blocks)
                    if text:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text)
                        print(f"已复制文本:\n{text}")
            
                self.selection_start = None
            
            def on_mouse_move(event):
                # 检查鼠标是否在任何文本块上
                cursor_on_text = False
                for block in self.text_blocks.values():
                    if (block['x'] <= event.x <= block['x'] + block['width'] and
                        block['y'] <= event.y <= block['y'] + block['height']):
                        cursor_on_text = True
                        break
                
                # 根据鼠标位置设置光标样式
                if cursor_on_text:
                    canvas.configure(cursor='ibeam')
                else:
                    canvas.configure(cursor='arrow')  # 使用默认箭头光标
        
            # 绑定事件
            canvas.bind('<Button-1>', on_mouse_down)
            canvas.bind('<B1-Motion>', on_mouse_drag)
            canvas.bind('<ButtonRelease-1>', on_mouse_up)
            canvas.bind('<Motion>', on_mouse_move)  # 添加鼠标移动事件
            canvas.bind('<Escape>', lambda e: self.cleanup_windows())
        
        except Exception as e:
            logging.error(f"显示覆盖层失败: {str(e)}")
            traceback.print_exc()

    def capture_and_process(self, width, height):
        """捕获并处理屏幕"""
        if self.is_processing:
            print("已有处理进行中，跳过本次请求")
            return
        
        try:
            self.is_processing = True
            print(f"\n=== 开始截图 ===")
            print(f"请求的屏幕大小: {width}x{height}")
            print(f"当前屏幕大小: {self.screen_width}x{self.screen_height}")
            
            # 确保使用当前屏幕尺寸
            width = self.screen_width
            height = self.screen_height
            
            # 如果已经有窗口，先清理掉
            if hasattr(self, 'overlay_window') and self.overlay_window:
                self.overlay_window.destroy()
                self.overlay_window = None
            
            self.current_screenshot = self.capture_screen_region(width, height)
            if not self.current_screenshot:
                print("截图失败")
                return
            
            # 创建新窗口并显示等待光标
            self.show_overlay_text([])  # 传入空的文本块列表，创建初始窗口
            
            # 确保窗口创建后立即设置等待光标
            if hasattr(self, 'overlay_window') and self.overlay_window:
                for widget in self.overlay_window.winfo_children():
                    if isinstance(widget, tk.Canvas):
                        widget.configure(cursor='wait')
                self.overlay_window.update_idletasks()
            
            print("开始OCR识别...")
            text_blocks = self.get_text_positions(self.current_screenshot)
            
            # OCR识别完成后显示结果
            if text_blocks:
                print(f"识别到{len(text_blocks)}个文本块，开始显示...")
                # 销毁当前的等待窗口
                if hasattr(self, 'overlay_window') and self.overlay_window:
                    self.overlay_window.destroy()
                    self.overlay_window = None
                # 创建新的结果显示窗口
                self.show_overlay_text(text_blocks)
            else:
                print("未识别到文本")
                # 即使没有识别到文本，也更新覆盖层状态
                if hasattr(self, 'overlay_window') and self.overlay_window:
                    for widget in self.overlay_window.winfo_children():
                        if isinstance(widget, tk.Canvas):
                            widget.configure(cursor='arrow')
        
        except Exception as e:
            print(f"处理失败: {str(e)}")


    def cleanup_windows(self):
        """清理窗口"""
        try:
            print("\n=== 清理窗口 ===")
            if hasattr(self, 'overlay_window') and self.overlay_window:
                print("正在销毁overlay_window")
                self.overlay_window.destroy()
                self.overlay_window = None  # 确保引用被清除
                print("overlay_window已销毁")
            if self.current_screenshot:
                print("清除当前截图")
                self.current_screenshot = None
            # 重置处理状态
            #self.is_processing = False
            print("窗口清理完成")
        except Exception as e:
            logging.error(f"清理窗口失败: {str(e)}")
            print(f"清理窗口时发生错误: {str(e)}")

    def cleanup_hook(self):
        """清理键盘钩子"""
        try:
            if self.keyboard_hook_id:
                user32 = ctypes.WinDLL('user32', use_last_error=True)
                if not user32.UnhookWindowsHookEx(self.keyboard_hook_id):
                    logging.error("卸载键盘钩子失败")
                self.keyboard_hook_id = None
        except Exception as e:
            logging.error(f"清理键盘钩子异常: {str(e)}")

    def run(self):
        """运行程序"""
        print("程序开始运行...")
        try:
            def check_state():
                try:
                    # 检查配置队列
                    while not self.config_queue.empty():
                        task = self.config_queue.get_nowait()
                        if callable(task):
                            task()
                    
                    # 检查是否需要清理窗口
                    if self.cleanup_pending:
                        self.cleanup_windows()
                        self.cleanup_pending = False

                    # 检查按键延迟触发
                    if not self.is_processing and self.key_press_time > 0:
                        current_time = time.time()
                        if (current_time - self.key_press_time) * 1000 >= self.trigger_delay_ms:
                            print(f"触发延迟已到 ({self.trigger_delay_ms}ms)")
                            print(f"当前状态：{str(self.is_processing)}")
                            # 使用保存的屏幕尺寸
                            self.capture_and_process(self.screen_width, self.screen_height)
                except Exception as e:
                    print(f"状态检查错误: {str(e)}")
                finally:
                    if self._running:
                        self.root.after(50, check_state)  # 每50ms检查一次
            
            # 启动状态检查
            self.root.after(50, check_state)
            
            # 创建系统托盘
            from system_tray import SystemTray
            self.tray = SystemTray(self)
            
            # 在新线程中运行系统托盘
            tray_thread = threading.Thread(target=self.tray.run)
            tray_thread.daemon = True
            tray_thread.start()
            
            # 主循环
            while self._running:
                self.root.update()
                time.sleep(0.01)  # 减少CPU使用
            
        except Exception as e:
            print(f"运行错误: {str(e)}")
        finally:
            print("程序正在退出清理资源...")
            self.cleanup_windows()
            self.cleanup_hook()
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass
            print("程序退出完成")
    
    def reload_config(self):
        """重新加载配置"""
        try:
            if hasattr(self, 'tray'):
                old_engine = self._ocr_engine
                self.config = self.tray.config
                
                # 更新触发延时
                self.trigger_delay_ms = self.config.get('trigger_delay_ms', 300)
                print(f"触发延迟已更新为: {self.trigger_delay_ms}ms")
                
                # 更新快捷键配置
                self.hotkey = self.config.get('hotkey', 'alt')
                print(f"快捷键已更新为: {self.hotkey}")
                
                # 如果OCR引擎为None或发生变化，进行初始化
                new_engine = self.config.get('ocr_engine', self.DEFAULT_CONFIG["ocr_engine"])
                if self._ocr_engine != new_engine:
                    print(f"OCR引擎{'初始化' if old_engine is None else f'从 {old_engine} 切换'} 为 {new_engine}")
                    self._ocr_engine = new_engine
                    self.init_ocr_engine()
                
                print("配置已重新加载")
        except Exception as e:
            print(f"重新加载配置失败: {str(e)}")
    
    def toggle_enabled(self):
        """切换服务状态"""
        self.enabled = not self.enabled
        if not self.enabled:
            # 如果禁用服务，清理所有窗口
            self.cleanup_windows()
        print(f"服务状态已切换为: {'启用' if self.enabled else '禁用'}")
    
    def cleanup(self):
        """清理资源"""
        self._running = False
        self.cleanup_windows()
        self.cleanup_hook()

if __name__ == '__main__':
    tool = ScreenOCRTool()
    tool.run()