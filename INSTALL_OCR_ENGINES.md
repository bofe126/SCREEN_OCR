# OCR 引擎安装说明

## 支持的 OCR 引擎

ScreenOCR 支持以下 OCR 引擎：
- **WeChatOCR**（默认）- 快速、准确、体积小
- **PaddleOCR**（可选）- 离线、高准确度、体积大

## 快速开始

ScreenOCR 默认使用 **WeChatOCR** 引擎，无需额外安装 Python 包。

### 最小安装（仅 WeChatOCR）

```bash
pip install -r requirements.txt
```

这将安装：
- ✅ pywin32（Windows API）
- ✅ Pillow（图像处理）
- ✅ pystray（系统托盘）
- ✅ pyinstaller（打包工具）

**然后安装 wcocr：**
1. 下载 `wcocr.pyd` from [GitHub](https://github.com/swigger/wechat-ocr)
2. 放在项目根目录

**系统要求：**
- 安装微信客户端（3.x 或 4.x）

## 可选 OCR 引擎

### PaddleOCR（可选 - 准确度高）

适合需要离线识别、高准确度的场景。

```bash
# Windows CPU 版本
pip install paddlepaddle
pip install paddleocr
pip install numpy
```

**体积**: ~200MB

**优点**:
- ⭐⭐⭐ 识别准确度高
- 支持多种语言
- 完全离线

**缺点**:
- 体积较大
- 首次加载稍慢

## OCR 引擎对比

| 引擎 | 安装难度 | 速度 | 准确度 | 体积 | 需要联网 |
|------|---------|------|--------|------|---------|
| WeChatOCR | ⭐ 简单 | ⚡ 快 | ⭐⭐⭐ 高 | ~10MB | ❌ |
| PaddleOCR | ⭐⭐ 中等 | ⚙️ 中 | ⭐⭐⭐ 高 | ~200MB | ❌ |

## 验证安装

### 验证 WeChatOCR

```bash
python -c "from wechat_ocr_wrapper import get_wechat_ocr; ocr = get_wechat_ocr(); print('✓ WeChatOCR 可用' if ocr.is_available() else '✗ WeChatOCR 不可用')"
```

### 验证 PaddleOCR

```bash
python -c "from paddleocr import PaddleOCR; print('✓ PaddleOCR 已安装')"
```

## 切换 OCR 引擎

运行程序后：
1. 右键点击系统托盘图标
2. 选择"设置"
3. 在"OCR 引擎"下拉框中选择
4. 点击"保存"

或编辑 `config.json`：

```json
{
    "ocr_engine": "WeChatOCR"  // 或 "PaddleOCR"
}
```

## 打包时的注意事项

### 最小打包（推荐）

默认打包脚本会**排除** PaddleOCR 和 Tesseract，只包含 WeChatOCR：

```bash
python build_exe.py
```

**优点**:
- ✅ exe 体积小（~25MB）
- ✅ 启动快
- ✅ 识别速度快

### 包含 PaddleOCR 的打包

如果需要在 exe 中包含 PaddleOCR，修改 `build_exe.py`：

```python
# 移除 --exclude-module 参数中的 paddleocr 和 numpy
'--exclude-module=paddleocr',  # 删除这行
'--exclude-module=numpy',       # 删除这行
```

**注意**: exe 体积会增加到 ~250MB

## 常见问题

### Q: 为什么默认使用 WeChatOCR？

A: 
- ✅ 无需额外安装 Python 包
- ✅ 识别速度快
- ✅ 准确度高
- ✅ 打包后体积小

### Q: 我必须安装微信吗？

A: 如果只使用 WeChatOCR，是的。如果使用 PaddleOCR，不需要。

### Q: 可以同时安装多个 OCR 引擎吗？

A: 可以！程序支持运行时切换引擎。

### Q: 哪个引擎最准确？

A: 中文识别：**WeChatOCR** ≈ **PaddleOCR**

### Q: 哪个引擎最快？

A: **WeChatOCR** > PaddleOCR

### Q: 打包后可以切换引擎吗？

A: 可以，但需要在打包时包含对应的依赖。

## 推荐配置

### 个人使用（推荐）

```bash
# 只安装核心依赖
pip install -r requirements.txt

# 下载 wcocr.pyd
# 使用 WeChatOCR
```

**优点**: 安装简单，体积小，速度快

### 开发/测试

```bash
# 安装所有 OCR 引擎
pip install -r requirements.txt
pip install paddlepaddle paddleocr numpy
```

**优点**: 可以测试对比不同引擎

### 离线环境

```bash
# 推荐使用 PaddleOCR
pip install paddlepaddle paddleocr numpy

# 不依赖微信客户端
```

**优点**: 完全离线可用

---

**需要帮助？** 查看 [GitHub Issues](https://github.com/your-repo/issues)

