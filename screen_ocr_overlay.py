import win32api
import win32gui
import win32con
import win32ui
import ctypes
from ctypes import wintypes
import pytesseract
from PIL import Image, ImageTk
import tkinter as tk
import logging
import traceback
from bs4 import BeautifulSoup
import time

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ScreenOCRTool:
    def __init__(self):
        print("初始化程序...")
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
                        # 处理ALT键 (VK_MENU = 164)
                        if kb.vkCode in [164, 165]:  # 左右Alt键的虚拟键码
                            # ALT键按下，且不是重复按键
                            if wParam == 260 and not kb.flags & 0x80:
                                if not self.event_cycle_active:  # 只有在没有活动事件周期时才处理
                                    print("检测到ALT键按下")
                                    self.alt_press_time = time.time()
                                    self.event_cycle_active = True
                            
                            # ALT键松开
                            elif wParam == 257:
                                print("检测到ALT键松开")
                                self.alt_press_time = 0
                                if not self.is_processing:  # 如果没有在处理中，就结束事件周期
                                    self.event_cycle_active = False
                                self.cleanup_pending = True  # 设置清理标志
                    
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
            logging.error(f"OCR处理失败: {str(e)}")
            return []

    def show_overlay_text(self, text_blocks):
        """显示文本覆盖层"""
        try:
            if hasattr(self, 'overlay_window') and self.overlay_window:
                try:
                    self.overlay_window.destroy()
                except:
                    pass
            
            self.overlay_window = tk.Toplevel()
            self.overlay_window.attributes('-topmost', True, '-alpha', 1.0)  # 设置完全不透明
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
            canvas.pack(fill=None, expand=False)  # 不要自动扩展
            
            # 显示截图作为背景
            if self.current_screenshot:
                # 转换为PhotoImage
                photo = ImageTk.PhotoImage(self.current_screenshot)
                canvas.photo = photo
                canvas.create_image(0, 0, image=photo, anchor='nw')
            
            # 初始化选择相关的变量
            self.selection_start = None
            self.selection_rect = None
            
            # 存储文本块信息
            self.text_blocks = {}
            
            # 按行组织文本块
            text_lines = {}
            for i, block in enumerate(text_blocks):
                line_key = block['y'] // 20  # 使用20像素作为行高
                if line_key not in text_lines:
                    text_lines[line_key] = []
                text_lines[line_key].append((i, block))
            
            # 在每行内按x坐标排序
            for line in text_lines.values():
                line.sort(key=lambda x: x[1]['x'])
            
            # 绘制文本
            for i, block in enumerate(text_blocks):
                try:
                    text_id = canvas.create_text(
                        block['x'],
                        block['y'],
                        text=block['text'],
                        font=('Microsoft YaHei', 12),
                        fill='black',
                        anchor='nw'
                    )
                    
                    # 存储文本块信息
                    line_key = block['y'] // 20
                    line_blocks = text_lines[line_key]
                    block_index = next(idx for idx, (i_, b) in enumerate(line_blocks) if i_ == i)
                    
                    self.text_blocks[i] = {
                        'text_id': text_id,
                        'text': block['text'],
                        'selected': False,
                        'bbox': (block['x'], block['y'],
                                block['x'] + block['width'],
                                block['y'] + block['height']),
                        'line': line_key,
                        'line_index': block_index,
                        'line_total': len(line_blocks)
                    }
                    
                except Exception as e:
                    logging.error(f"创建文本块失败: {str(e)}")
                    continue
            
            def get_text_at_position(x, y):
                """获取指定位置的文本块"""
                # 直接遍历所有文本块，找到最近的
                closest_block = None
                min_distance = float('inf')
                
                for block_id, block in self.text_blocks.items():
                    bx1, by1, bx2, by2 = block['bbox']
                    
                    # 计算点到文本块的距离
                    dx = 0
                    if x < bx1:
                        dx = bx1 - x
                    elif x > bx2:
                        dx = x - bx2
                        
                    dy = 0
                    if y < by1:
                        dy = by1 - y
                    elif y > by2:
                        dy = y - by2
                        
                    distance = (dx * dx + dy * dy) ** 0.5
                    
                    # 如果点在文本块内，直接返回
                    if bx1 <= x <= bx2 and by1 <= y <= by2:
                        print(f"找到直接命中的文本块: {block['text']}")
                        return block
                    
                    # 记录最近的文本块
                    if distance < min_distance:
                        min_distance = distance
                        closest_block = block
                
                # 如果找到了足够近的文本块
                if closest_block and min_distance < 50:  # 50像素的阈值
                    print(f"找到最近的文本块: {closest_block['text']}, 距离: {min_distance:.1f}")
                    return closest_block
                
                print(f"未找到合适的文本块，最近距离: {min_distance:.1f}")
                return None
            
            def on_mouse_down(event):
                self.selection_start = (event.x, event.y)
                # 清除之前的选择
                for block in self.text_blocks.values():
                    # 删除之前的背景矩形
                    if 'rect_id' in block:
                        canvas.delete(block['rect_id'])
                        del block['rect_id']
                    block['selected'] = False
                    canvas.itemconfig(block['text_id'], fill='black')
            
            def on_mouse_drag(event):
                if not self.selection_start:
                    return
                
                x1, y1 = self.selection_start
                x2, y2 = event.x, event.y
                
                # 获取起始和结束位置的文本块
                start_block = get_text_at_position(x1, y1)
                end_block = get_text_at_position(x2, y2)
                
                # 清除所有选择和背景矩形
                for block in self.text_blocks.values():
                    if 'rect_id' in block:
                        canvas.delete(block['rect_id'])
                        del block['rect_id']
                    block['selected'] = False
                    canvas.itemconfig(block['text_id'], fill='black')
                
                # 如果没有找到文本块，直接返回
                if not (start_block and end_block):
                    return
                
                # 确定选择范围
                start_line = min(start_block['line'], end_block['line'])
                end_line = max(start_block['line'], end_block['line'])
                
                # 更新选择区域
                for block in self.text_blocks.values():
                    if start_line <= block['line'] <= end_line:
                        # 单行选择
                        if start_line == end_line:
                            # 根据鼠标移动方向确定选择范围
                            if x2 >= x1:
                                start_idx = start_block['line_index']
                                end_idx = end_block['line_index']
                            else:
                                start_idx = end_block['line_index']
                                end_idx = start_block['line_index']
                            
                            if start_idx <= block['line_index'] <= end_idx:
                                block['selected'] = True
                        # 多行选择
                        else:
                            # 第一行
                            if block['line'] == start_line:
                                if y2 >= y1:
                                    # 向下选择
                                    if block['line_index'] >= start_block['line_index']:
                                        block['selected'] = True
                                else:
                                    # 向上选择
                                    if block['line_index'] <= start_block['line_index']:
                                        block['selected'] = True
                            # 最后一行
                            elif block['line'] == end_line:
                                if y2 >= y1:
                                    # 向下选择
                                    if block['line_index'] <= end_block['line_index']:
                                        block['selected'] = True
                                else:
                                    # 向上选择
                                    if block['line_index'] >= end_block['line_index']:
                                        block['selected'] = True
                            # 中间行
                            else:
                                block['selected'] = True
                    
                    # 更新显示
                    canvas.itemconfig(block['text_id'], 
                                    fill='white' if block['selected'] else 'black')
                
                # 更新选择区域显示
                if self.selection_rect:
                    canvas.delete(self.selection_rect)
                
                selected_blocks = [b for b in self.text_blocks.values() if b['selected']]
                for block in selected_blocks:
                    # 为每个选中的文本块创建背景矩形
                    x1, y1, x2, y2 = block['bbox']
                    rect_id = canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill='#0078D7',
                        stipple='gray50',
                        width=0
                    )
                    # 将背景矩形放到文本下面
                    canvas.tag_lower(rect_id)
                    # 将背景矩形ID存储到文本块中，以便后续删除
                    block['rect_id'] = rect_id
            
            def on_mouse_up(event):
                self.selection_start = None
            
            def show_context_menu(event):
                menu = tk.Menu(canvas, tearoff=0)
                menu.add_command(label="复制", command=self.copy_selected_text)
                menu.post(event.x_root, event.y_root)
            
            # 绑定鼠标事件
            canvas.bind('<Button-1>', on_mouse_down)
            canvas.bind('<B1-Motion>', on_mouse_drag)
            canvas.bind('<ButtonRelease-1>', on_mouse_up)
            canvas.bind('<Button-3>', show_context_menu)  # 右键菜单
            
            # ESC键退出
            self.overlay_window.bind('<Escape>', lambda e: self.cleanup_windows())
            
        except Exception as e:
            logging.error(f"显示文本覆盖层失败: {str(e)}")
            traceback.print_exc()
            self.cleanup_windows()

    def copy_selected_text(self):
        """复制选中的文本"""
        try:
            selected_text = []
            for block in self.text_blocks.values():
                if block['selected']:
                    selected_text.append(block['text'])
            
            if selected_text:
                text = '\n'.join(selected_text)
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                print(f"已复制 {len(selected_text)} 个文本块")
        except Exception as e:
            print(f"复制文本失败: {str(e)}")

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
                    # 检查是否需要清理窗口
                    if self.cleanup_pending:
                        self.cleanup_windows()
                        self.cleanup_pending = False
                    
                    # 检查ALT状态
                    if self.alt_press_time > 0 and not self.is_processing:
                        current_time = time.time()
                        elapsed = current_time - self.alt_press_time
                        if elapsed >= 0.3:
                            print("ALT按下超过0.3秒，开始处理...")
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
            
            # 主循环
            while self._running:
                self.root.update()
                time.sleep(0.01)  # 减少CPU使用
            
        except Exception as e:
            print(f"运行错误: {str(e)}")
        finally:
            print("程序正在退出���清理资源...")
            self.cleanup_windows()
            self.cleanup_hook()
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass
            print("程序退出完成")

if __name__ == '__main__':
    tool = ScreenOCRTool()
    tool.run() 