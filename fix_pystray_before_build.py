"""
修复 pystray 库的菜单位置 bug

在打包前运行此脚本，自动修复 pystray 库中的菜单位置问题。
这个 bug 存在于 pystray 库的源代码中，需要在打包前修复。

Bug 描述：
- pystray._win32.py 第217行将菜单标志位写在了注释中
- 导致 TPM_BOTTOMALIGN 标志无效，菜单显示在错误位置

修复方法：
- 将 `win32.TPM_LEFTALIGN  # FIXED: ... | win32.TPM_BOTTOMALIGN  # FIXED: ...`
- 改为 `win32.TPM_LEFTALIGN | win32.TPM_BOTTOMALIGN`
"""

import sys
import os


def find_pystray_win32():
    """查找 pystray._win32 模块文件"""
    try:
        import pystray._win32
        return pystray._win32.__file__
    except ImportError:
        print("[错误] 未安装 pystray 库")
        print("请运行: pip install pystray")
        return None


def fix_pystray_menu():
    """修复 pystray 菜单位置"""
    print("=" * 60)
    print("修复 pystray 菜单位置 bug")
    print("=" * 60)
    
    # 查找文件
    win32_file = find_pystray_win32()
    if not win32_file:
        return False
    
    print(f"[信息] 文件位置: {win32_file}")
    
    # 读取文件
    try:
        with open(win32_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"[错误] 无法读取文件: {e}")
        return False
    
    # 检查是否需要修复
    if 'win32.TPM_LEFTALIGN | win32.TPM_BOTTOMALIGN' in content:
        print("[信息] pystray 库已经修复，无需再次修复")
        return True
    
    # 查找需要修复的行
    if '| win32.TPM_BOTTOMALIGN' not in content:
        print("[信息] 未找到需要修复的代码，可能已经是正确版本")
        return True
    
    print("[发现] 找到需要修复的 bug")
    
    # 查找并修复
    lines = content.split('\n')
    fixed = False
    
    for i, line in enumerate(lines):
        # 查找包含 TrackPopupMenuEx 后面的标志位行
        if 'TPM_LEFTALIGN' in line and '#' in line and '| win32.TPM_BOTTOMALIGN' in line:
            print(f"  第{i+1}行: 发现 bug")
            print(f"    原始: {line.strip()}")
            
            # 提取缩进
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * indent
            
            # 修复：移除注释，保留代码
            new_line = f"{indent_str}win32.TPM_LEFTALIGN | win32.TPM_BOTTOMALIGN"
            lines[i] = new_line
            
            print(f"    修复: {new_line.strip()}")
            fixed = True
            break
    
    if not fixed:
        print("[警告] 未能自动修复，请手动检查")
        return False
    
    # 备份原文件
    backup_file = win32_file + '.backup_auto'
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[成功] 已备份到: {backup_file}")
    except:
        print("[警告] 无法创建备份文件")
    
    # 写入修复后的内容
    try:
        with open(win32_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("[成功] 已修复 pystray 菜单位置 bug")
        return True
    except Exception as e:
        print(f"[错误] 无法写入文件: {e}")
        return False


def main():
    """主函数"""
    success = fix_pystray_menu()
    
    print()
    print("=" * 60)
    if success:
        print("[完成] pystray 库修复完成")
        print()
        print("说明:")
        print("  - TPM_LEFTALIGN    → 菜单在鼠标右侧")
        print("  - TPM_BOTTOMALIGN  → 菜单在鼠标上方")
        print("  - 最终效果         → 菜单在鼠标右上角")
        print()
        print("现在可以正常打包了！")
    else:
        print("[失败] 修复失败")
        print()
        print("请手动修复或联系开发者")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

