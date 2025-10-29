# ScreenOCR 打包版使用说明

## 📦 分发包内容

```
ScreenOCR/
├── ScreenOCR.exe       # 主程序
├── wcocr.pyd           # WeChatOCR 引擎（必需）
└── config.json         # 配置文件（首次运行自动生成）
```

## 🚀 快速开始

### 1. 首次运行

双击 `ScreenOCR.exe` 即可启动。

### 2. 系统要求

- ✅ Windows 10/11
- ✅ 微信客户端（用于 WeChatOCR 引擎）
- ✅ `wcocr.pyd` 文件（与 exe 同目录）

### 3. 使用方法

1. **启动程序** - 程序会在系统托盘显示图标
2. **按住 ALT 键** - 鼠标拖动选择文字区域
3. **松开鼠标** - 自动识别并复制文字
4. **Ctrl+V 粘贴** - 在任何地方粘贴识别的文字

## ⚙️ 配置

右键点击系统托盘图标 → 设置

可配置项：
- OCR 引擎（WeChatOCR / PaddleOCR / Tesseract）
- 触发延迟
- 热键（ALT / CTRL / SHIFT / F1-F12）
- 自动复制
- 图像预处理

## 🔧 故障排查

### 程序无法启动

1. 检查 `wcocr.pyd` 是否在同目录
2. 检查是否安装了微信客户端
3. 以管理员身份运行

### WeChatOCR 不可用

1. 确认已安装微信客户端（3.x 或 4.x）
2. 确认 `wcocr.pyd` 存在
3. 查看日志输出（如果有）

### 识别不准确

1. 系统托盘 → 设置 → 启用"图像预处理"
2. 尝试调整触发延迟
3. 确保文字清晰可见

## 📝 配置文件

`config.json` 示例：

```json
{
    "ocr_engine": "WeChatOCR",
    "trigger_delay_ms": 300,
    "hotkey": "ALT",
    "auto_copy": true,
    "show_debug": false,
    "image_preprocess": false
}
```

## 🆚 OCR 引擎对比

| 引擎 | 速度 | 准确度 | 依赖 |
|------|------|--------|------|
| WeChatOCR | ⚡ 快 | ⭐⭐⭐ 高 | 微信 + wcocr.pyd |
| PaddleOCR | ⚙️ 中 | ⭐⭐⭐ 高 | 大型依赖（未打包） |
| Tesseract | 🐌 慢 | ⭐⭐ 中 | Tesseract.exe（未打包） |

**推荐使用 WeChatOCR**

## 💡 提示

- 程序会随系统启动（如果配置）
- 可在系统托盘右键菜单退出
- 配置会自动保存
- 支持中文、英文和数字识别

## 📋 版本信息

查看版本：右键托盘图标 → 关于

## 🆘 获取帮助

如遇问题，请提供：
1. Windows 版本
2. 微信版本
3. 错误信息
4. `config.json` 内容

---

**开发者**: [Your Name]
**项目地址**: [GitHub链接]

