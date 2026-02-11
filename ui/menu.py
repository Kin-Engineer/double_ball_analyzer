# ui/menu.py
"""
菜单系统
"""
from typing import List, Dict, Any

def create_menu(title: str, options: List[Dict[str, str]]) -> str:
    """创建菜单"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    for i, option in enumerate(options, 1):
        print(f"{i}. {option.get('name', '未知选项')}")
        if 'description' in option:
            print(f"   {option.get('description', '')}")
    
    print(f"{'='*60}")
    return input("请选择: ")

def create_simple_menu(options: List[str]) -> str:
    """创建简单菜单"""
    print("\n" + "="*60)
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    print("="*60)
    return input("请选择: ")