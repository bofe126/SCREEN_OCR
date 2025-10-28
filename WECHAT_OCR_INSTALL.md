# WeChatOCR 安装指南

## 前提条件

1. ✅ 已安装微信客户端（Windows 版）
2. ✅ 微信至少登录过一次

## 安装步骤

### 1. 下载 wcocr.pyd

访问 GitHub 项目：https://github.com/swigger/wechat-ocr

- 进入 [Releases 页面](https://github.com/swigger/wechat-ocr/releases)
- 下载最新版本（例如 `demo-7.zip`）
- 解压后找到 `wcocr.dll` 文件
- **将 `wcocr.dll` 重命名为 `wcocr.pyd`**
- 将 `wcocr.pyd` 复制到项目根目录（与 `screen_ocr_overlay.py` 同级）

### 2. 启用 WeChatOCR

1. 运行程序：`python screen_ocr_overlay.py`
2. 右键点击系统托盘图标
3. 选择"设置"
4. 在"OCR引擎"下拉框中选择"WeChatOCR"
5. 关闭设置窗口

### 3. 验证安装

程序会自动查找 WeChatOCR.exe，通常位于：
```
C:\Users\[用户名]\AppData\Roaming\Tencent\WeChat\XPlugin\Plugins\WeChatOCR\[版本号]\extracted\WeChatOCR.exe
```

如果找到，会显示"WeChatOCR 初始化成功"。

## 替代方案

如果不想安装 WeChatOCR，程序默认使用 **PaddleOCR** 引擎，无需额外配置。

## 故障排除

### 问题：提示"wcocr 模块未安装"

**解决方案：**
1. 确认 `wcocr.pyd` 文件在项目根目录
2. 确认文件名是 `wcocr.pyd`（不是 `wcocr.dll`）
3. 确认下载的是 64 位版本（如果使用 64 位 Python）

### 问题：提示"未找到 WeChatOCR.exe"

**解决方案：**
1. 确认已安装微信客户端
2. 确认微信至少登录过一次
3. 尝试重启微信
4. 或者切换到 PaddleOCR 引擎

## OCR 引擎对比

| 引擎 | 优势 | 安装难度 |
|------|------|---------|
| **WeChatOCR** | 识别准确，速度快 | 中等（需下载额外文件） |
| **PaddleOCR** | 已内置，开箱即用 | 简单 |
| **Tesseract** | 支持多语言 | 中等（需安装软件） |

## 相关链接

- WeChatOCR 项目：https://github.com/swigger/wechat-ocr
- 本项目：https://github.com/your-repo/screenocr

