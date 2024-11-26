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

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ScreenOCRTool:
    def __init__(self):
        print("初始化程序...")
        # 添加配置队列和状态标志
        self.config_queue = queue.Queue()
        self.enabled = True  # 默认启用服务
        
        # 初始化主窗口
        self.root = tk.Tk()
        self.root.withdraw()
        
        # 初始化状态
        self.is_processing = False
        self.current_screenshot = None
        self._running = True
        self.alt_press_time = 0
        self.event_cycle_active = False  # 添加事件周期状态
        self.cleanup_pending = False  # 添加清理标志
        
        # 设置键盘钩子
        self.keyboard_hook_id = None
        print("开始设置键盘钩子...")
        self.setup_keyboard_hook()
        print("键盘钩子设置完成")
        
        # 设置 Tesseract 路径
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # 添加选择模式配置
        self.selection_mode = 'text'  # 'text' 或 'region'
        
        # 获取系统 DPI 缩放
        self.dpi_scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        print(f"系统DPI缩放: {self.dpi_scale}")
        
        # 初始化OCR相关属性
        self.paddle_ocr = None
        self.ocr_engine = None  # 将在reload_config中设置
        self.trigger_delay_ms = 300  # 默认触发延时
        self.hotkey = 'alt'  # 默认快捷键
        self.pressed_keys = set()  # 用于跟踪当前按下的键
        
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
        
        # 加载配置
        if hasattr(self, 'tray'):
            self.config = self.tray.config
            self.reload_config()
        
    def init_ocr_engine(self):
        """初始化OCR引擎"""
        try:
            # 清理现有的OCR引擎
            if hasattr(self, 'paddle_ocr'):
                self.paddle_ocr = None

            # 根据配置初始化OCR引擎
            if self.ocr_engine == 'paddle':
                print("初始化PaddleOCR引擎...")
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            print(f"OCR引擎已设置为: {self.ocr_engine}")
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
                try:
                    if nCode >= 0:
                        kb = lParam.contents
                        # 检查是否是配置的快捷键
                        if self.hotkey.lower() == 'alt':
                            # ALT键按下，且不是重复按键
                            if kb.vkCode in [164, 165] and wParam == 260 and not kb.flags & 0x80:
                                if not self.event_cycle_active:  # 只有在没有活动事件周期时才处理
                                    print("检测到ALT键按下")
                                    self.alt_press_time = time.time()
                                    self.event_cycle_active = True
                            
                            # ALT键松开
                            elif kb.vkCode in [164, 165] and wParam == 257:
                                print("检测到ALT键松开")
                                # 检查是否满足延时要求
                                if self.alt_press_time > 0:
                                    current_time = time.time()
                                    elapsed = current_time - self.alt_press_time
                                    trigger_delay = self.trigger_delay_ms / 1000  # 转换为秒
                                    if elapsed >= trigger_delay:
                                        print(f"ALT键按下时间超过{self.trigger_delay_ms}毫秒，开始处理...")
                                        screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                                        screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                                        self.capture_and_process(screen_width, screen_height)
                                    else:
                                        print(f"ALT键按下时间不足{self.trigger_delay_ms}毫秒，不处理")
                                self.alt_press_time = 0
                                if not self.is_processing:  # 如果没有在处理中，就结束事件周期
                                    self.event_cycle_active = False
                                self.cleanup_pending = True  # 设置清理标志
                        elif self.hotkey.lower() == 'ctrl':
                            # CTRL键按下，且不是重复按键
                            if kb.vkCode in [162, 163] and wParam == 256 and not kb.flags & 0x80:
                                if not self.event_cycle_active:
                                    print("检测到CTRL键按下")
                                    self.alt_press_time = time.time()
                                    self.event_cycle_active = True
                            
                            # CTRL键松开
                            elif kb.vkCode in [162, 163] and wParam == 257:
                                print("检测到CTRL键松开")
                                # 检查是否满足延时要求
                                if self.alt_press_time > 0:
                                    current_time = time.time()
                                    elapsed = current_time - self.alt_press_time
                                    trigger_delay = self.trigger_delay_ms / 1000  # 转换为秒
                                    if elapsed >= trigger_delay:
                                        print(f"CTRL键按下时间超过{self.trigger_delay_ms}毫秒，开始处理...")
                                        screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                                        screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                                        self.capture_and_process(screen_width, screen_height)
                                    else:
                                        print(f"CTRL键按下时间不足{self.trigger_delay_ms}毫秒，不处理")
                                self.alt_press_time = 0
                                if not self.is_processing:
                                    self.event_cycle_active = False
                                self.cleanup_pending = True
                        else:
                            # 处理组合键
                            key_name = None
                            # 查找虚拟键码对应的键名
                            for name, codes in self.key_mapping.items():
                                if kb.vkCode in codes:
                                    key_name = name
                                    break
                            
                            if key_name:
                                if wParam == 256 or wParam == 260:  # 键按下
                                    if not kb.flags & 0x80:  # 不是重复按键
                                        self.pressed_keys.add(key_name)
                                        required_keys = set(self.hotkey.lower().split('+'))
                                        if required_keys == self.pressed_keys:
                                            if not self.event_cycle_active:
                                                print(f"检测到快捷键组合: {'+'.join(sorted(self.pressed_keys))}")
                                                self.alt_press_time = time.time()
                                                self.event_cycle_active = True
                                elif wParam == 257:  # 键松开
                                    self.pressed_keys.discard(key_name)
                                    if not self.pressed_keys:
                                        # 检查是否满足延时要求
                                        if self.alt_press_time > 0:
                                            current_time = time.time()
                                            elapsed = current_time - self.alt_press_time
                                            trigger_delay = self.trigger_delay_ms / 1000  # 转换为秒
                                            if elapsed >= trigger_delay:
                                                print(f"快捷键按下时间超过{self.trigger_delay_ms}毫秒，开始处理...")
                                                screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                                                screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                                                self.capture_and_process(screen_width, screen_height)
                                            else:
                                                print(f"快捷键按下时间不足{self.trigger_delay_ms}毫秒，不处理")
                                        self.alt_press_time = 0
                                        if not self.is_processing:
                                            self.event_cycle_active = False
                                        self.cleanup_pending = True
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)
                except Exception as e:
                    print(f"键盘钩子处理错误: {str(e)}")
                    return user32.CallNextHookEx(None, nCode, wParam, lParam)
            
            # 设置钩子
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
            
            # 设置SetWindowsHookExW的参数类型
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
                raise ctypes.WinError(ctypes.get_last_error())
                
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
            # 考虑DPI缩放计算实际大小
            real_width = int(width * self.dpi_scale)
            real_height = int(height * self.dpi_scale)
            print(f"开始捕获屏幕，实际大小: {real_width}x{real_height}, DPI缩放: {self.dpi_scale}")
            
            hwnd = win32gui.GetDesktopWindow()
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, real_width, real_height)
            saveDC.SelectObject(saveBitMap)
            saveDC.BitBlt((0, 0), (real_width, real_height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            image = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # 调整图像大小以匹配显示
            if self.dpi_scale != 1.0:
                image = image.resize((width, height), Image.Resampling.LANCZOS)
                print(f"调整图像大小为: {width}x{height}")
            
            print("屏幕捕获成功")
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
            if self.ocr_engine == 'paddle':
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
        gap = next_block['bbox'][0] - (prev_block['bbox'][0] + prev_block['bbox'][2])
        
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
            center_y = (block['bbox'][1] + block['bbox'][3]) / 2
            
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
            line_blocks.sort(key=lambda b: b['bbox'][0])  # 按x坐标排序
            
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
            x1, y1, x2, y2 = block['bbox']
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
            x1, y1, x2, y2 = block['bbox']
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
            
            self.overlay_window = tk.Toplevel()
            self.overlay_window.attributes('-topmost', True, '-alpha', 1.0)
            self.overlay_window.overrideredirect(True)
            
            try:
                self.overlay_window.state('zoomed')
            except:
                self.overlay_window.attributes('-fullscreen', True)
            
            # 获取屏幕尺寸（不考虑DPI缩放）
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # 创建画布并设置确切的大小
            canvas = tk.Canvas(
                self.overlay_window,
                highlightthickness=0,
                bg='white',
                cursor='ibeam',
                width=screen_width,
                height=screen_height
            )
            canvas.pack(fill=None, expand=False)
            
            # 显示截图作为背景
            if self.current_screenshot:
                photo = ImageTk.PhotoImage(self.current_screenshot)
                canvas.photo = photo
                canvas.create_image(0, 0, image=photo, anchor='nw')
            
            # 初始化选择相关的变量
            self.selection_start = None
            self.text_blocks = {}
            self.selected_blocks = set()
            
            # 存储文本块信息
            for i, block in enumerate(text_blocks):
                self.text_blocks[i] = {
                    'text': block['text'],
                    'bbox': (block['x'], block['y'],
                            block['x'] + block['width'],
                            block['y'] + block['height']),
                    'selected': False
                }
            
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
                    bx1, by1, bx2, by2 = block['bbox']
                    
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
            
            # 绑定事件
            canvas.bind('<Button-1>', on_mouse_down)
            canvas.bind('<B1-Motion>', on_mouse_drag)
            canvas.bind('<ButtonRelease-1>', on_mouse_up)
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
            print(f"开始截图... 屏幕大小: {width}x{height}")
            self.current_screenshot = self.capture_screen_region(width, height)
            if not self.current_screenshot:
                print("截图失败")
                return
            
            print("开始OCR识别...")
            text_blocks = self.get_text_positions(self.current_screenshot)
            if text_blocks:
                print(f"识别到{len(text_blocks)}个文本块，开始显示...")
                self.show_overlay_text(text_blocks)
            else:
                print("未识别到文本")
            
        except Exception as e:
            print(f"处理失败: {str(e)}")
            traceback.print_exc()
        finally:
            self.is_processing = False
            if self.alt_press_time == 0:
                self.event_cycle_active = False

    def cleanup_windows(self):
        """清理窗口"""
        try:
            if hasattr(self, 'overlay_window') and self.overlay_window:
                self.overlay_window.destroy()
            self.current_screenshot = None
        except Exception as e:
            logging.error(f"清理窗口失败: {str(e)}")

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
                    
                    # 检查ALT状态
                    if self.alt_press_time > 0 and not self.is_processing and self.enabled:
                        current_time = time.time()
                        elapsed = current_time - self.alt_press_time
                        trigger_delay = self.trigger_delay_ms / 1000  # 转换为秒
                        if elapsed >= trigger_delay:
                            print(f"ALT按下超过{self.trigger_delay_ms}毫秒，开始处理...")
                            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                            self.capture_and_process(screen_width, screen_height)
                            self.alt_press_time = 0  # 重置时间，防止重复触发
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
                old_engine = self.ocr_engine
                self.config = self.tray.config
                
                # 更新触发延时
                self.trigger_delay_ms = self.config.get('trigger_delay_ms', 300)
                print(f"触发延时已更新为: {self.trigger_delay_ms}ms")
                
                # 更新快捷键配置
                self.hotkey = self.config.get('hotkey', 'alt')
                print(f"快捷键已更新为: {self.hotkey}")
                
                # 如果OCR引擎为None或发生变化，进行初始化
                new_engine = self.config.get('ocr_engine', 'paddle')  # 默认使用paddle
                if new_engine == "PaddleOCR (默认)":
                    new_engine = "paddle"
                elif new_engine == "Tesseract":
                    new_engine = "tesseract"
                
                if self.ocr_engine != new_engine:
                    print(f"OCR引擎{'初始化' if old_engine is None else f'从 {old_engine} 切换'} 为 {new_engine}")
                    self.ocr_engine = new_engine
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