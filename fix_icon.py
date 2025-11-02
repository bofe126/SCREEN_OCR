# -*- coding: utf-8 -*-
"""
修复图标 - 重新生成完整的多尺寸 ICO 文件
"""
from PIL import Image
from cairosvg import svg2png
from io import BytesIO
import os

print("重新生成图标...")

# 删除旧的 icon.ico
if os.path.exists('icon.ico'):
    os.remove('icon.ico')
    print("已删除旧图标")

# 读取 SVG
with open('icon.svg', 'rb') as f:
    svg_data = f.read()

# 生成所有需要的尺寸
sizes = [256, 128, 64, 48, 32, 16]  # 从大到小
images = []

for size in sizes:
    print(f"生成 {size}x{size}...")
    png_data = svg2png(bytestring=svg_data, output_width=size, output_height=size)
    img = Image.open(BytesIO(png_data))
    # 确保是 RGBA 模式
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    images.append(img)

# 保存为 ICO（Windows 格式）
print("保存为 icon.ico...")
images[0].save(
    'icon.ico',
    format='ICO',
    sizes=[(img.width, img.height) for img in images],
    append_images=images[1:]
)

print("OK 图标生成完成!")
print("文件: icon.ico")
print(f"包含尺寸: {', '.join(f'{s}x{s}' for s in sizes)}")
print("")
print("现在运行打包命令:")
print("  build.bat")
print("  或")
print("  python build_exe.py")

