# ScreenOCR 打包说明

## 快速打包

### 方法 1：自动打包（推荐）

```bash
# 双击运行（会自动安装 PyInstaller）
build.bat
```

### 方法 2：简易打包

```bash
# 如果方法1失败，使用这个
build_simple.bat
```

### 方法 3：手动打包

```bash
# 1. 安装 PyInstaller
pip install pyinstaller

# 2. 运行打包脚本
python build_exe.py

# 3. 获取 exe
# 位置: dist/ScreenOCR.exe
```

## 手动打包（高级）

如果需要自定义打包选项：

```bash
pyinstaller --name=ScreenOCR ^
    --windowed ^
    --onefile ^
    --add-data=icon.svg;. ^
    --add-data=wcocr.pyd;. ^
    --hidden-import=PIL ^
    --hidden-import=pystray._win32 ^
    --exclude-module=paddleocr ^
    --exclude-module=numpy ^
    screen_ocr_overlay.py
```

## 打包选项说明

| 选项 | 说明 |
|------|------|
| `--windowed` | 不显示控制台窗口 |
| `--onefile` | 打包成单个 exe（推荐） |
| `--add-data` | 添加数据文件（图标、wcocr.pyd等） |
| `--hidden-import` | 包含隐藏的依赖 |
| `--exclude-module` | 排除不需要的模块，减小体积 |

## 打包后的文件结构

```
dist/
├── ScreenOCR.exe       # 主程序
├── wcocr.pyd           # WeChatOCR 依赖（需要手动复制）
└── config.json         # 配置文件（可选）
```

## 注意事项

### 1. pystray 库的已知 bug

**重要：** 项目包含自动修复脚本来解决 pystray 库的菜单位置 bug。

**问题说明：**
- pystray 库在 Windows 上存在一个 bug，导致系统托盘右键菜单位置不正确
- Bug 原因：库源代码中将菜单标志位写在了注释里（`| win32.TPM_BOTTOMALIGN` 在 `#` 后面）
- 影响：菜单会显示在鼠标右下角，而不是正确的右上角

**自动修复：**
- 打包脚本会在打包前自动运行 `fix_pystray_before_build.py`
- 该脚本会自动修复本地安装的 pystray 库
- 无需手动操作，打包即可自动修复

**手动修复（可选）：**
```bash
# 如果自动修复失败，可以手动运行
python fix_pystray_before_build.py
```

**技术细节：**
```python
# Bug 代码（位于 pystray/_win32.py 第217行）：
win32.TPM_LEFTALIGN  # ... | win32.TPM_BOTTOMALIGN  # ...

# 修复后：
win32.TPM_LEFTALIGN | win32.TPM_BOTTOMALIGN
```

### 2. wcocr.pyd

打包脚本会自动将 `wcocr.pyd` 复制到 `dist/` 目录。如果没有这个文件：
- 从 [swigger/wechat-ocr](https://github.com/swigger/wechat-ocr) 下载
- 放在项目根目录或 `dist/` 目录

### 3. 首次运行

首次运行 exe 时：
- 会自动创建 `config.json`
- 需要安装微信客户端（用于 WeChatOCR）
- 程序会自动查找微信路径

### 4. 体积优化

单文件 exe 体积约 **20-30MB**（已排除 PaddleOCR/Tesseract）

如需进一步减小体积：
- 使用 `--onedir` 替代 `--onefile`（生成目录，体积更小但文件多）
- 使用 UPX 压缩（`--upx-dir=/path/to/upx`）

### 5. 依赖说明

**包含的依赖：**
- ✅ pywin32（Windows API）
- ✅ Pillow（图像处理）
- ✅ pystray（系统托盘）
- ✅ tkinter（GUI）

**不包含的依赖（可选）：**
- ❌ PaddleOCR（体积大，已排除）
- ❌ Tesseract（已排除）
- ✅ WeChatOCR（通过 wcocr.pyd 支持）

## 常见问题

### Q: 打包时出现 "FileNotFoundError: pyinstaller"？

A: PyInstaller 未正确安装。解决方法：

```bash
# 方法1：使用 pip 安装
pip install pyinstaller

# 方法2：使用 python -m 方式
python -m pip install pyinstaller

# 方法3：使用简易打包脚本
build_simple.bat
```

### Q: 打包时出现 "系統找不到指定的檔案"？

A: 
1. 确认 Python 在 PATH 中：`python --version`
2. 确认 pip 可用：`pip --version`
3. 使用 `build_simple.bat` 而不是 `build_exe.py`

### Q: exe 无法运行？

A: 检查：
1. `wcocr.pyd` 是否在同目录
2. 是否安装了微信客户端
3. 查看日志文件（如果有）

### Q: 如何分发给其他人？

A: 分发 `dist/` 目录下的所有文件：
- `ScreenOCR.exe`
- `wcocr.pyd`
- `config.json`（可选）

### Q: 如何更新配置？

A: 编辑 `config.json` 或通过程序的系统托盘菜单"设置"

## 开发模式 vs 打包模式

| 特性 | 开发模式 | 打包模式 |
|------|---------|---------|
| 启动 | `python screen_ocr_overlay.py` | `ScreenOCR.exe` |
| 依赖 | 需要 Python 环境 | 自包含 |
| 体积 | - | ~25MB |
| 更新 | 修改代码即可 | 需要重新打包 |

## 自动化打包（可选）

创建 `build.bat` 批处理文件：

```batch
@echo off
echo 清理旧文件...
rmdir /s /q build dist
del ScreenOCR.spec

echo 开始打包...
python build_exe.py

echo 完成！
pause
```

然后直接双击 `build.bat` 即可打包。

