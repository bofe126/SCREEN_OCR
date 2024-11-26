# Screen OCR Overlay Tool

一个强大的屏幕文字识别和选择工具 / A powerful screen text recognition and selection tool

## 功能特点 / Features

### 1. 智能文本选择 / Smart Text Selection
- 按行智能识别文本块 / Smart text block recognition by line
- 支持5像素垂直容差 / 5-pixel vertical tolerance support
- 自动合并相邻文本 / Auto-merge adjacent text
- 保持自然阅读顺序 / Maintain natural reading order

### 2. 智能空格处理 / Intelligent Space Handling
- 不添加空格的情况 / No Space Cases:
  * 中文字符前后 / Around Chinese characters
  * 标点符号前后 / Around punctuation marks
  * 连续数字之间 / Between consecutive numbers
- 添加空格的情况 / Add Space Cases:
  * 字母和数字之间（间距>10px）/ Between letters and numbers (gap>10px)
  * 不同类型字符之间 / Between different character types
  * 中英文混排时 / In Chinese-English mixed text

### 3. 视觉反馈 / Visual Feedback
- 统一半透明高亮层 / Unified semi-transparent highlight layer
  * 颜色：#4D94FF / Color: #4D94FF
  * 透明度：30% / Opacity: 30%
- 流畅的选择体验 / Smooth selection experience
- 即时视觉反馈 / Instant visual feedback

### 4. 使用方法 / Usage
1. 按住Alt键0.3秒触发 / Hold Alt for 0.3s to trigger
2. 拖动选择文本 / Drag to select text
3. 自动复制到剪贴板 / Auto-copy to clipboard

## 技术特点 / Technical Features

### OCR引擎 / OCR Engines
- 主要引擎：PaddleOCR（支持中文）/ Primary: PaddleOCR (Chinese support)
- 备选引擎：Tesseract / Secondary: Tesseract

### 依赖项 / Dependencies
- Python 3.6+
- tkinter
- win32api/win32gui
- pytesseract
- PaddleOCR
- PIL (Pillow)
- BeautifulSoup

### 系统要求 / System Requirements
- 操作系统：Windows 10/11 / OS: Windows 10/11
- 需要安装Tesseract OCR / Requires Tesseract OCR installation

## 性能优化 / Performance Optimization
- 最小化CPU使用 / Minimal CPU usage
- 动态DPI缩放支持 / Dynamic DPI scaling support
- 高效的文本块管理 / Efficient text block management
- 优化的图形渲染 / Optimized graphics rendering

## 安全特性 / Security Features
- 使用Windows低级键盘钩子 / Uses Windows low-level keyboard hooks
- 最小化持久状态 / Minimal persistent state
- 无外部数据传输 / No external data transmission

## 已知限制 / Known Limitations
- 高DPI环境可能有坐标偏差 / High DPI environments might have coordinate variations
- OCR识别准确度依赖图像质量 / OCR accuracy depends on image quality
- 性能因系统配置而异 / Performance varies with system specifications

## 开发计划 / Development Plans
1. 提升OCR准确度 / Improve OCR accuracy
2. 增强多显示器支持 / Enhance multi-monitor support
3. 添加可配置热键 / Add configurable hotkeys
4. 实现更强大的错误处理 / Implement robust error handling
5. 扩展语言支持 / Expand language support

## 贡献 / Contributing
欢迎提交Issue和Pull Request / Issues and Pull Requests are welcome

## 许可证 / License
[MIT License](LICENSE)
