# Screen OCR Tool

一个基于Python的屏幕OCR工具，支持快捷键触发、实时文字识别和选择复制。

## 功能特点

- 按住Alt键0.3秒触发OCR识别
- 支持按字符级别选择文本
- 支持右键复制选中文本
- 支持高分辨率显示器(DPI缩放)
- 实时显示识别结果
- 支持多种OCR引擎（Tesseract/PaddleOCR）

## 安装要求

1. Python 3.6+
2. 必需的Python包：
bash pip install pywin32 pillow pytesseract beautifulsoup4
3. Tesseract OCR引擎：
   - 从[这里](https://github.com/UB-Mannheim/tesseract/wiki)下载并安装
   - 安装时选择中文语言包
   - 默认安装路径：`C:\Program Files\Tesseract-OCR\`

## 使用方法

1. 按住Alt键0.3秒，程序会自动截取当前屏幕
2. 等待OCR识别完成，识别结果会显示在原位置
3. 使用鼠标拖动选择需要的文字
4. 右键点击选中区域，选择"复制"
5. 按ESC键退出识别界面

## 实现细节

1. 截图实现：
   - 使用win32api实现屏幕捕获
   - 自动处理DPI缩放问题

2. OCR识别：
   - 使用Tesseract引擎进行文字识别
   - 支持中英文混合识别
   - 按字符级别进行文本定位

3. 交互设计：
   - 使用tkinter实现透明覆盖层
   - 支持文本选择和复制
   - 模拟文本编辑器的选择体验

## 已知问题

1. 在某些高DPI设置下可能存在轻微的坐标偏差
2. 识别速度受机器性能影响

## 待优化

1. 提高OCR识别准确率
2. 优化高DPI下的显示效果
3. 增加更多文本处理功能

## 开发环境

- Windows 10/11
- Python 3.12
- Tesseract 5.3.1

## 许可证

MIT License

## 作者

bofe126
