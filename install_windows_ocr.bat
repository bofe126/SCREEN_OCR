@echo off
echo ============================================================
echo 安装 Windows OCR 依赖
echo ============================================================
echo.

pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage winrt-Windows.Storage.Streams winrt-Windows.Globalization winrt-Windows.Foundation winrt-Windows.Foundation.Collections

echo.
echo ============================================================
echo 安装完成！
echo ============================================================
pause
