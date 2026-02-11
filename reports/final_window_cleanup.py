# scripts/final_window_cleanup.py
"""
最终窗口配置清理 - 处理剩余的config.analysis引用
"""
import re
from pathlib import Path

def cleanup_file(file_path_str):
    """清理单个文件"""
    file_path = Path(file_path_str)
    
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    print(f"\n📄 处理: {file_path_str}")
    
    # 1. 检查是否需要添加WindowConfigManager导入
    if "from utils.window_config import WindowConfigManager" not in content:
        import_match = re.search(r'(^from.*?\n|^import.*?\n)+', content, re.MULTILINE)
        if import_match:
            insert_pos = import_match.end()
            content = content[:insert_pos] + "from utils.window_config import WindowConfigManager\n" + content[insert_pos:]
            print("  ✅ 添加WindowConfigManager导入")
    
    # 2. 处理FREQUENCY_ANALYSIS_WINDOW和BASIC_STATS_WINDOW
    # 这些可以映射到短期窗口或使用默认值
    replacements = [
        (r'config\.analysis\.FREQUENCY_ANALYSIS_WINDOW', "WindowConfigManager.get_window_by_name('short_term')"),
        (r'config\.analysis\.BASIC_STATS_WINDOW', "WindowConfigManager.get_window_by_name('short_term')"),
        
        # 处理其他可能的窗口配置
        (r'config\.analysis\.(\w+_WINDOW)', lambda m: f"WindowConfigManager.get_window_by_name('short_term')"),
    ]
    
    changes_made = False
    for pattern, replacement in replacements:
        if isinstance(replacement, str):
            if re.search(pattern, content):
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    changes_made = True
                    print(f"  ✅ 替换: {pattern}")
        else:
            # 可调用对象
            if re.search(pattern, content):
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    changes_made = True
                    print(f"  ✅ 替换模式: {pattern}")
    
    # 3. 保存文件（如果有变化）
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        print(f"  ✅ 文件已更新")
        return True
    else:
        print(f"  ℹ️  文件无需修改")
        return False

def main():
    """主函数"""
    print("🧹 最终窗口配置清理")
    print("=" * 60)
    
    # 直接从项目根目录查找文件
    project_root = Path.cwd()
    
    # 需要清理的文件（相对于项目根目录）
    files_to_cleanup = [
        "analysis/probability_analyzer.py",
        "services/prediction_service.py",
        "main.py",  # 如果存在的话
    ]
    
    results = []
    for file_path_str in files_to_cleanup:
        full_path = project_root / file_path_str
        success = cleanup_file(full_path)
        results.append((file_path_str, success))
    
    # 统计结果
    print("\n" + "=" * 60)
    print("📊 清理统计:")
    
    success_count = 0
    for file_name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {file_name}: {status}")
        if success:
            success_count += 1
    
    print(f"\n🎯 清理完成: {success_count}/{len(results)} 个文件已处理")
    
    if success_count == len(results):
        print("🎉 所有文件清理成功！")
    else:
        print("⚠️  部分文件清理失败")

if __name__ == "__main__":
    main()