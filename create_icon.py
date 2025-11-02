"""
直接从 SVG 生成 ICO 图标文件
"""
from PIL import Image
from cairosvg import svg2png
from io import BytesIO

print("正在生成图标...")

# 读取 SVG
with open('icon.svg', 'rb') as f:
    svg_data = f.read()

# 转换为多个尺寸的 ICO
sizes = [16, 32, 48, 64, 128, 256]
images = []

for size in sizes:
    print(f"  生成 {size}x{size} 尺寸...")
    png_data = svg2png(bytestring=svg_data, output_width=size, output_height=size)
    img = Image.open(BytesIO(png_data))
    images.append(img)

# 保存为 ICO
print("  保存为 icon.ico...")
images[0].save('icon.ico', format='ICO', sizes=[(s, s) for s in sizes], append_images=images[1:])

print("✅ 图标生成完成: icon.ico")
print("\n现在可以运行打包命令了:")
print("  python build_exe.py")
print("  或")
print("  build.bat")

