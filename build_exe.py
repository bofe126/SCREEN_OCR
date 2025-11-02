"""
ScreenOCR 打包脚本
使用 PyInstaller 将程序打包成 exe
"""
import os
import sys
import shutil
import subprocess

def clean_build():
    """清理之前的构建文件"""
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"清理 {dir_name}...")
            shutil.rmtree(dir_name)
    
    spec_file = 'ScreenOCR.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)

def convert_svg_to_ico():
    """将 SVG 转换为 ICO 格式"""
    print("转换图标格式...")
    try:
        from PIL import Image
        from cairosvg import svg2png
        from io import BytesIO
        
        # 读取 SVG
        with open('icon.svg', 'rb') as f:
            svg_data = f.read()
        
        # 转换为多个尺寸的 ICO
        sizes = [16, 32, 48, 64, 128, 256]
        images = []
        
        for size in sizes:
            png_data = svg2png(bytestring=svg_data, output_width=size, output_height=size)
            img = Image.open(BytesIO(png_data))
            images.append(img)
        
        # 保存为 ICO
        images[0].save('icon.ico', format='ICO', sizes=[(s, s) for s in sizes], append_images=images[1:])
        print("✅ 图标转换完成: icon.ico")
        return True
    except Exception as e:
        print(f"⚠️ 图标转换失败: {e}")
        print("   将使用默认图标")
        return False

def build_exe():
    """构建 exe"""
    print("开始构建 ScreenOCR.exe...")
    
    # 检查或生成图标
    if not os.path.exists('icon.ico'):
        print("icon.ico 不存在，尝试从 SVG 生成...")
        has_icon = convert_svg_to_ico()
    else:
        print(f"✓ 找到图标文件: icon.ico")
        has_icon = True
    
    # PyInstaller 命令（使用 python -m 方式调用）
    cmd = [
        sys.executable,  # 使用当前 Python 解释器
        '-m',
        'PyInstaller',
        '--name=ScreenOCR',
        '--windowed',  # 不显示控制台窗口
        '--onefile',   # 打包成单个 exe
        '--clean',
        '--noconfirm',  # 不询问，直接覆盖
        
        # 设置图标
        f'--icon={os.path.abspath("icon.ico")}' if has_icon else '',
        
        # 添加数据文件
        '--add-data=icon.svg;.',
        '--add-data=wcocr.pyd;.' if os.path.exists('wcocr.pyd') else '',
        
        # 隐藏导入
        '--hidden-import=PIL',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=pystray._win32',
        
        # 排除不需要的模块（减小体积）
        '--exclude-module=paddleocr',
        '--exclude-module=paddlepaddle',
        '--exclude-module=numpy',
        '--exclude-module=pytesseract',
        '--exclude-module=bs4',
        '--exclude-module=matplotlib',
        '--exclude-module=scipy',
        
        # 主程序入口
        'screen_ocr_overlay.py'
    ]
    
    # 移除空字符串
    cmd = [c for c in cmd if c]
    
    # 执行构建
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("\n✅ 构建成功！")
        print(f"📦 程序位置: {os.path.abspath('dist/ScreenOCR.exe')}")
        
        # 复制必要的文件到 dist
        if os.path.exists('wcocr.pyd'):
            shutil.copy('wcocr.pyd', 'dist/')
            print("✅ 已复制 wcocr.pyd 到 dist/")
        
        if os.path.exists('config.json'):
            shutil.copy('config.json', 'dist/')
            print("✅ 已复制 config.json 到 dist/")
        
        print("\n📝 运行程序:")
        print("   cd dist")
        print("   ScreenOCR.exe")
    else:
        print("\n❌ 构建失败！")
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("ScreenOCR - PyInstaller 打包工具")
    print("=" * 60)
    print()
    
    # 检查 PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("❌ 未安装 PyInstaller")
        print()
        print("正在尝试安装 PyInstaller...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
            print("✅ PyInstaller 安装成功")
            import PyInstaller
        except Exception as e:
            print(f"❌ 安装失败: {e}")
            print()
            print("请手动运行: pip install pyinstaller")
            sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]}")
    print()
    
    # 清理旧文件
    clean_build()
    
    # 构建
    build_exe()

