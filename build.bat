@echo off
chcp 65001 >nul
echo ========================================
echo   ScreenOCR 一键打包工具
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    echo 请先安装 Python: https://www.python.org/
    pause
    exit /b 1
)

REM 检查 PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [警告] 未安装 PyInstaller
    echo 正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)

echo [1/3] 清理旧文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ScreenOCR.spec del ScreenOCR.spec
echo      完成

echo.
echo [2/3] 开始打包...
python build_exe.py
if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo [3/3] 验证文件...
if exist dist\ScreenOCR.exe (
    echo      ✓ ScreenOCR.exe
) else (
    echo      ✗ ScreenOCR.exe 未找到
)

if exist dist\wcocr.pyd (
    echo      ✓ wcocr.pyd
) else (
    echo      ! wcocr.pyd 未找到（需要手动复制）
)

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 程序位置: dist\ScreenOCR.exe
echo.
echo 按任意键打开 dist 文件夹...
pause >nul
explorer dist

