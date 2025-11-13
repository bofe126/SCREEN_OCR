"""
Windows OCR 包装类
使用 Windows 10/11 内置的 OCR API 进行文字识别

依赖安装:
pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage winrt-Windows.Storage.Streams winrt-Windows.Globalization winrt-Windows.Foundation winrt-Windows.Foundation.Collections
"""
import asyncio
import logging
from typing import List, Dict, Optional
from PIL import Image
import io
import os
import tempfile

try:
    # 导入 Windows Runtime API
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.graphics.imaging import BitmapDecoder, SoftwareBitmap
    from winrt.windows.storage import StorageFile
    from winrt.windows.storage.streams import RandomAccessStreamReference, DataReader
    WINDOWS_OCR_AVAILABLE = True
except ImportError as e:
    WINDOWS_OCR_AVAILABLE = False
    print(f"Windows OCR 导入失败: {e}")
except Exception as e:
    WINDOWS_OCR_AVAILABLE = False
    print(f"Windows OCR 导入异常: {e}")


class WindowsOCRWrapper:
    """Windows OCR 包装类"""
    
    def __init__(self):
        """初始化 Windows OCR"""
        self.initialized = False
        self.error_message = None
        self.engine = None
        
        if not WINDOWS_OCR_AVAILABLE:
            self.error_message = "Windows OCR 模块未安装"
            logging.error("❌ Windows OCR 模块未安装")
            logging.error("   请运行: pip install winrt-Windows.Media.Ocr")
            return
        
        try:
            # 尝试创建 OCR 引擎（中文简体）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.engine = loop.run_until_complete(self._create_engine())
            
            if self.engine:
                self.initialized = True
                logging.info("✓ Windows OCR 初始化成功")
            else:
                self.error_message = "无法创建 Windows OCR 引擎"
                logging.error("❌ 无法创建 Windows OCR 引擎")
        except Exception as e:
            self.error_message = f"Windows OCR 初始化失败: {str(e)}"
            logging.error(f"❌ Windows OCR 初始化失败: {e}")
    
    async def _create_engine(self):
        """创建 OCR 引擎"""
        try:
            from winrt.windows.globalization import Language
            
            # 尝试中文简体
            engine = OcrEngine.try_create_from_language(Language("zh-CN"))
            if engine:
                return engine
            
            # 如果中文不可用，使用默认语言
            engine = OcrEngine.try_create_from_user_profile_languages()
            return engine
        except Exception as e:
            logging.error(f"创建 OCR 引擎失败: {e}")
            return None
    
    def is_available(self):
        """检查 OCR 是否可用"""
        return self.initialized and self.engine is not None
    
    async def _ocr_image_async(self, image: Image.Image) -> List[Dict]:
        """异步 OCR 识别"""
        try:
            # 保存图片到临时文件
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name
                image.save(tmp_path, 'PNG')
            
            try:
                # 加载图片文件
                storage_file = await StorageFile.get_file_from_path_async(tmp_path)
                stream = await storage_file.open_async(1)  # FileAccessMode.Read = 1
                
                # 解码图片
                decoder = await BitmapDecoder.create_async(stream)
                bitmap = await decoder.get_software_bitmap_async()
                
                # 执行 OCR
                result = await self.engine.recognize_async(bitmap)
                
                # 解析结果
                text_blocks = []
                for line in result.lines:
                    # 获取边界框
                    words = list(line.words)
                    if not words:
                        continue
                    
                    # 计算整行的边界框
                    min_x = min(word.bounding_rect.x for word in words)
                    min_y = min(word.bounding_rect.y for word in words)
                    max_x = max(word.bounding_rect.x + word.bounding_rect.width for word in words)
                    max_y = max(word.bounding_rect.y + word.bounding_rect.height for word in words)
                    
                    text_blocks.append({
                        'text': line.text,
                        'x': int(min_x),
                        'y': int(min_y),
                        'width': int(max_x - min_x),
                        'height': int(max_y - min_y)
                    })
                
                return text_blocks
            finally:
                # 清理临时文件
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        except Exception as e:
            logging.error(f"Windows OCR 识别失败: {e}")
            return []
    
    def ocr_pil_image(self, image: Image.Image, preprocess: bool = False) -> List[Dict]:
        """
        对 PIL Image 进行 OCR 识别
        
        Args:
            image: PIL Image 对象
            preprocess: 是否进行图像预处理（Windows OCR 通常不需要）
        
        Returns:
            文本块列表，每个块包含 text, x, y, width, height
        """
        if not self.is_available():
            logging.error("Windows OCR 不可用")
            return []
        
        try:
            # 如果需要预处理
            if preprocess:
                from PIL import ImageEnhance, ImageFilter
                # 增强对比度
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)
                # 锐化
                image = image.filter(ImageFilter.SHARPEN)
            
            # 运行异步 OCR
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._ocr_image_async(image))
            loop.close()
            
            return result
        
        except Exception as e:
            logging.error(f"Windows OCR 处理失败: {e}")
            return []


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    ocr = WindowsOCRWrapper()
    if ocr.is_available():
        print("✓ Windows OCR 可用")
        
        # 测试识别
        from PIL import Image
        test_img = Image.new('RGB', (100, 100), 'white')
        result = ocr.ocr_pil_image(test_img)
        print(f"测试结果: {result}")
    else:
        print(f"✗ Windows OCR 不可用: {ocr.error_message}")
