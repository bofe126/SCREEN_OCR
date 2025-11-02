
"""
WeChatOCR 包装类
用于自动查找和调用 WeChatOCR.exe 进行文字识别

注意：此实现依赖于 wcocr 模块
项目地址：https://github.com/swigger/wechat-ocr
安装方法：从上述 GitHub 仓库下载预编译的 wcocr.pyd 文件，或自行编译
"""
import os
import re
import logging
from pathlib import Path

from typing import List, Dict, Optional

try:
    # 尝试导入 wcocr 模块（将 wcocr.dll 重命名为 wcocr.pyd）
    import wcocr
    WECHAT_OCR_AVAILABLE = True
except ImportError:
    WECHAT_OCR_AVAILABLE = False
    logging.warning("wcocr 模块未安装，WeChatOCR 功能将不可用")
    logging.warning("请从 https://github.com/swigger/wechat-ocr 下载 wcocr.pyd")


class WeChatOCRWrapper:
    """WeChatOCR 包装类"""
    
    def __init__(self):
        """初始化 WeChatOCR"""
        self.ocr_exe_path = None
        self.wechat_dir = None
        self.initialized = False
        
        if not WECHAT_OCR_AVAILABLE:
            logging.error("wcocr 模块未安装")
            return
        
        # 查找 WeChatOCR.exe 和微信目录路径
        self.ocr_exe_path = self._find_wechat_ocr_exe()
        self.wechat_dir = self._find_wechat_dir()
        
        if self.ocr_exe_path and self.wechat_dir:
            try:
                logging.info(f"找到 WeChatOCR.exe: {self.ocr_exe_path}")
                logging.info(f"找到微信目录: {self.wechat_dir}")
                # 初始化 wcocr
                wcocr.init(self.ocr_exe_path, self.wechat_dir)
                # 等待初始化完成（WeChatOCR 初始化是异步的）
                # 优化：减少等待时间，使用更智能的检测方式
                import time
                max_wait = 3.0  # 最多等待3秒
                check_interval = 0.1  # 每100ms检查一次
                waited = 0.0
                while waited < max_wait:
                    time.sleep(check_interval)
                    waited += check_interval
                    # 简单检测：等待一定时间后认为已就绪
                    if waited >= 1.0:  # 至少等待1秒
                        break
                self.initialized = True
                logging.info(f"WeChatOCR 初始化完成 (耗时 {waited:.1f}秒)")
            except Exception as e:
                logging.error(f"初始化 WeChatOCR 失败: {str(e)}")
                import traceback
                traceback.print_exc()
                self.initialized = False
        else:
            if not self.ocr_exe_path:
                logging.warning("未找到 WeChatOCR.exe，请确保已安装微信客户端")
            if not self.wechat_dir:
                logging.warning("未找到微信目录")
    
    def _find_wechat_ocr_exe(self) -> Optional[str]:
        """
        自动查找 WeChatOCR.exe 的完整路径
        返回: WeChatOCR.exe 的完整路径，如果未找到则返回 None
        """
        # 方法1: 从 APPDATA 查找（最常见的位置）
        appdata = os.getenv('APPDATA')
        if appdata:
            # 微信 3.x 路径
            base_path = Path(appdata) / "Tencent" / "WeChat" / "XPlugin" / "Plugins" / "WeChatOCR"
            if base_path.exists():
                # 查找版本号目录
                version_pattern = re.compile(r'^\d+$')
                for version_dir in sorted(base_path.iterdir(), reverse=True):  # 从最新版本开始查找
                    if version_dir.is_dir() and version_pattern.match(version_dir.name):
                        # 检查 extracted 子目录
                        ocr_exe = version_dir / "extracted" / "WeChatOCR.exe"
                        if ocr_exe.exists():
                            return str(ocr_exe)
                        # 直接在版本目录下
                        ocr_exe = version_dir / "WeChatOCR.exe"
                        if ocr_exe.exists():
                            return str(ocr_exe)
            
            # 微信 4.x 路径 (使用 wxocr.dll)
            base_path_4x = Path(appdata) / "Tencent" / "xwechat" / "XPlugin" / "plugins" / "WeChatOcr"
            if base_path_4x.exists():
                version_pattern = re.compile(r'^\d+$')
                for version_dir in sorted(base_path_4x.iterdir(), reverse=True):
                    if version_dir.is_dir() and version_pattern.match(version_dir.name):
                        ocr_dll = version_dir / "extracted" / "wxocr.dll"
                        if ocr_dll.exists():
                            return str(ocr_dll)
        
        # 方法2: 从注册表查找微信安装路径
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat")
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            
            # 在微信安装目录下查找 WeChatOCR
            wechat_path = Path(install_path)
            
            # 检查 XPlugin 目录
            plugin_path = wechat_path / "XPlugin" / "Plugins" / "WeChatOCR"
            if plugin_path.exists():
                version_pattern = re.compile(r'^\d+$')
                for version_dir in sorted(plugin_path.iterdir(), reverse=True):
                    if version_dir.is_dir() and version_pattern.match(version_dir.name):
                        ocr_exe = version_dir / "extracted" / "WeChatOCR.exe"
                        if ocr_exe.exists():
                            return str(ocr_exe)
                        ocr_exe = version_dir / "WeChatOCR.exe"
                        if ocr_exe.exists():
                            return str(ocr_exe)
                
        except:
            pass
        
        return None
    
    def _find_wechat_dir(self) -> Optional[str]:
        """
        自动查找微信运行时目录
        返回: 微信目录路径，如果未找到则返回 None
        """
        # 如果找到了 wxocr.dll (微信 4.0)，需要找到 Weixin\x.x.x.x 格式的目录
        is_wechat_4 = self.ocr_exe_path and 'wxocr.dll' in self.ocr_exe_path
        
        # 方法1: 从注册表查找
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat")
            install_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            
            install_path = Path(install_path)
            
            # 如果是微信 4.0，尝试查找 Weixin\版本号 目录
            if is_wechat_4:
                # 尝试在同级目录查找 Weixin 文件夹
                parent = install_path.parent  # Tencent 目录
                weixin_base = parent / "Weixin"
                if weixin_base.exists():
                    # 查找版本号目录 (如 4.0.0.26)
                    version_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
                    for version_dir in sorted(weixin_base.iterdir(), reverse=True):
                        if version_dir.is_dir() and version_pattern.match(version_dir.name):
                            logging.info(f"找到微信 4.0 运行时目录: {version_dir}")
                            return str(version_dir)
                # 微信 4.0 必须找到 Weixin\版本号 目录，否则继续往下找
                pass
            else:
                # 不是微信 4.0，返回注册表路径
                if install_path.exists():
                    return str(install_path)
                
        except:
            pass
        
        # 方法2: 在常见安装位置查找
        # 获取所有可能的驱动器
        drives = []
        for letter in 'CDEFGHIJ':
            drive = Path(f"{letter}:\\")
            if drive.exists():
                drives.append(drive)
        
        for drive in drives:
            if is_wechat_4:
                # 微信 4.0: 查找 Weixin\x.x.x.x
                weixin_base = drive / "Program Files" / "Tencent" / "Weixin"
                if weixin_base.exists():
                    version_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
                    for version_dir in sorted(weixin_base.iterdir(), reverse=True):
                        if version_dir.is_dir() and version_pattern.match(version_dir.name):
                            logging.info(f"找到微信 4.0 运行时目录: {version_dir}")
                            return str(version_dir)
                
                # 也尝试 Program Files (x86)
                weixin_base_x86 = drive / "Program Files (x86)" / "Tencent" / "Weixin"
                if weixin_base_x86.exists():
                    version_pattern = re.compile(r'^\d+\.\d+\.\d+\.\d+$')
                    for version_dir in sorted(weixin_base_x86.iterdir(), reverse=True):
                        if version_dir.is_dir() and version_pattern.match(version_dir.name):
                            logging.info(f"找到微信 4.0 运行时目录: {version_dir}")
                            return str(version_dir)
            else:
                # 微信 3.x: 查找 WeChat 目录
                common_paths = [
                    drive / "Program Files" / "Tencent" / "WeChat",
                    drive / "Program Files (x86)" / "Tencent" / "WeChat",
                ]
                
                for base_path in common_paths:
                    if base_path.exists():
                        # 查找版本号目录
                        version_pattern = re.compile(r'^\[?[\d.]+\]?$')
                        for subdir in sorted(base_path.iterdir(), reverse=True):
                            if subdir.is_dir() and version_pattern.match(subdir.name):
                                return str(subdir)
                        # 如果没有版本号目录，直接返回基础路径
                        return str(base_path)
        
        return None
    
    def is_available(self) -> bool:
        """检查 WeChatOCR 是否可用"""
        return WECHAT_OCR_AVAILABLE and self.initialized
    
    def preprocess_image(self, pil_image, enhance_contrast=False, sharpen=False):
        """
        图像预处理（可选）
        
        参数:
            pil_image: PIL Image 对象
            enhance_contrast: 是否增强对比度
            sharpen: 是否锐化
        
        返回:
            处理后的 PIL Image
        """
        from PIL import ImageEnhance, ImageFilter
        
        result = pil_image.copy()
        
        # 对比度增强 - 对低对比度文字有帮助
        if enhance_contrast:
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(1.5)  # 增强50%
        
        # 锐化 - 对模糊文字有帮助
        if sharpen:
            result = result.filter(ImageFilter.SHARPEN)
        
        return result
    
    def ocr_pil_image(self, pil_image, preprocess=False) -> List[Dict]:
        """
        对 PIL Image 对象进行 OCR 识别
        
        参数:
            pil_image: PIL Image 对象
            preprocess: 是否进行预处理（对比度增强+锐化）
        
        返回:
            识别结果列表，每项包含: text, x, y, width, height
        """
        if not self.is_available():
            logging.error("WeChatOCR 不可用")
            return []
        
        temp_path = None
        try:
            # 可选的图像预处理
            if preprocess:
                pil_image = self.preprocess_image(pil_image, enhance_contrast=True, sharpen=True)
            
            # 保存为临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                temp_path = tmp_file.name
                pil_image.save(temp_path, 'PNG')
            
            # 进行识别
            result = wcocr.ocr(temp_path)
            
            # 验证结果
            if result is None:
                logging.error("OCR 识别失败：未能获取结果")
                return []
            
            return self._parse_ocr_result(result)
            
        except Exception as e:
            logging.error(f"WeChatOCR 识别失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            # 确保删除临时文件
            if temp_path:
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    def _parse_ocr_result(self, result) -> List[Dict]:
        """
        解析 OCR 结果，转换为统一格式
        
        参数:
            result: WeChatOCR 返回的原始结果
        
        返回:
            标准化的结果列表
        """
        parsed_results = []
        
        if not result:
            logging.warning("OCR 结果为空")
            return parsed_results
        
        try:
            # WeChatOCR 的结果格式可能是字典或列表
            if isinstance(result, dict):
                ocr_response = result.get('ocr_response', [])
                if not ocr_response:
                    # 尝试其他可能的键名
                    for key in ['result', 'results', 'data', 'text', 'texts']:
                        if key in result:
                            ocr_response = result[key]
                            break
            elif isinstance(result, list):
                ocr_response = result
            else:
                logging.warning(f"未知的 OCR 结果格式: {type(result)}")
                return parsed_results
            
            skipped_count = 0
            for item in ocr_response:
                try:
                    # 提取文本
                    text = item.get('text', '') or item.get('word', '')
                    if not text:
                        continue
                    
                    # 提取坐标信息（尝试多种可能的字段名）
                    # 格式1: left, top, right, bottom (WeChatOCR 4.0 格式)
                    if 'left' in item and 'right' in item:
                        left = item.get('left', 0)
                        top = item.get('top', 0)
                        right = item.get('right', 0)
                        bottom = item.get('bottom', 0)
                        x = int(left)
                        y = int(top)
                        width = int(right - left)
                        height = int(bottom - top)
                    # 格式2: pos 字段
                    elif 'pos' in item:
                        pos = item['pos']
                        x = pos.get('x', 0)
                        y = pos.get('y', 0)
                        width = pos.get('width', 0)
                        height = pos.get('height', 0)
                    # 格式3: location 字段
                    elif 'location' in item:
                        loc = item['location']
                        x = loc.get('left', 0)
                        y = loc.get('top', 0)
                        width = loc.get('width', 0)
                        height = loc.get('height', 0)
                    # 格式4: 直接在 item 中使用 x, y, width, height
                    else:
                        x = item.get('x', 0)
                        y = item.get('y', 0)
                        width = item.get('width', 0) or item.get('w', 0)
                        height = item.get('height', 0) or item.get('h', 0)
                    
                    # 将整行文本按字符拆分
                    if len(text) > 0 and width > 0 and height > 0:
                        char_width = width / len(text)
                        for i, char in enumerate(text):
                            char_x = x + i * char_width
                            parsed_results.append({
                                'text': char,
                                'x': int(char_x),
                                'y': int(y),
                                'width': int(char_width),
                                'height': int(height)
                            })
                    else:
                        skipped_count += 1
                    
                except Exception as e:
                    logging.warning(f"解析 OCR 结果项失败: {str(e)}")
                    continue
            
            if skipped_count > 0:
                logging.warning(f"跳过了 {skipped_count} 个无效的OCR项")
        
        except Exception as e:
            logging.error(f"解析 OCR 结果失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return parsed_results
    
    def close(self):
        """关闭 OCR 实例"""
        if self.initialized:
            try:
                # wcocr 模块没有显式的 close 方法
                # 清理状态即可
                self.initialized = False
            except:
                pass


# 全局实例（单例模式）
_wechat_ocr_instance = None

def get_wechat_ocr() -> WeChatOCRWrapper:
    """获取 WeChatOCR 全局实例"""
    global _wechat_ocr_instance
    if _wechat_ocr_instance is None:
        _wechat_ocr_instance = WeChatOCRWrapper()
    return _wechat_ocr_instance
