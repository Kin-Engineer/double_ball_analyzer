# utils/config_validator.py
"""
配置验证工具 - 验证所有模块是否使用统一窗口配置
"""
import ast
import os
import logging
from typing import Dict, Any, List, Set
import importlib.util

logger = logging.getLogger('config_validator')

class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.window_config_class = "WindowConfigManager"
        self.window_config_methods = {
            'get_instance',
            'get_default_window',
            'get_window_by_name',
            'get_all_windows',
            'get_trend_windows'
        }
        
    def validate_window_config_usage(self) -> Dict[str, Any]:
        """验证所有模块是否使用统一窗口配置"""
        results = {
            'valid_files': [],
            'invalid_files': [],
            'direct_config_imports': [],
            'hardcoded_windows': [],
            'summary': {}
        }
        
        # 扫描Python文件
        python_files = self._find_python_files()
        
        for file_path in python_files:
            logger.debug(f"检查文件: {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_result = self._analyze_file(file_path, content)
                
                if file_result['is_valid']:
                    results['valid_files'].append(file_path)
                else:
                    results['invalid_files'].append({
                        'file': file_path,
                        'issues': file_result['issues']
                    })
                
                # 检查硬编码窗口
                if file_result.get('has_hardcoded_windows'):
                    results['hardcoded_windows'].append(file_path)
                    
                # 检查直接导入config的情况
                if file_result.get('has_direct_config_import'):
                    results['direct_config_imports'].append(file_path)
                    
            except Exception as e:
                logger.warning(f"无法分析文件 {file_path}: {e}")
        
        # 生成总结
        total_files = len(python_files)
        valid_count = len(results['valid_files'])
        invalid_count = len(results['invalid_files'])
        
        results['summary'] = {
            'total_python_files': total_files,
            'valid_files_count': valid_count,
            'invalid_files_count': invalid_count,
            'hardcoded_windows_count': len(results['hardcoded_windows']),
            'direct_config_imports_count': len(results['direct_config_imports']),
            'compliance_rate': (valid_count / total_files * 100) if total_files > 0 else 0
        }
        
        return results
    
    def _find_python_files(self) -> List[str]:
        """查找所有Python文件"""
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # 忽略某些目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', '.git']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def _analyze_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """分析单个文件"""
        result = {
            'file': file_path,
            'is_valid': True,
            'issues': [],
            'has_hardcoded_windows': False,
            'has_direct_config_import': False
        }
        
        try:
            tree = ast.parse(content)
            
            # 检查导入
            imports = self._check_imports(tree)
            
            # 检查硬编码窗口数字
            hardcoded_windows = self._check_hardcoded_windows(tree)
            
            # 检查对config的直接引用
            config_references = self._check_config_references(tree, content)
            
            # 组合结果
            if hardcoded_windows:
                result['is_valid'] = False
                result['issues'].extend([f"硬编码窗口: {hw}" for hw in hardcoded_windows])
                result['has_hardcoded_windows'] = True
            
            if config_references:
                result['is_valid'] = False
                result['issues'].extend([f"直接引用config: {cr}" for cr in config_references])
                result['has_direct_config_import'] = True
            
            # 验证是否使用了WindowConfigManager
            if not self._check_window_config_usage(tree, content):
                if not result['has_hardcoded_windows'] and not result['has_direct_config_import']:
                    result['issues'].append("未使用WindowConfigManager也未硬编码窗口")
            
        except SyntaxError as e:
            result['is_valid'] = False
            result['issues'].append(f"语法错误: {e}")
        
        return result
    
    def _check_imports(self, tree: ast.AST) -> Set[str]:
        """检查导入语句"""
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.add(f"{module}.{alias.name}")
        
        return imports
    
    def _check_hardcoded_windows(self, tree: ast.AST) -> List[str]:
        """检查硬编码的窗口数字"""
        hardcoded_windows = []
        window_keywords = ['window', 'period', 'recent', 'history', 'analyse']
        
        for node in ast.walk(tree):
            # 检查数字字面量
            if isinstance(node, ast.Num):
                value = node.n
                # 检查是否是常见的窗口值（如30, 50, 100等）
                if isinstance(value, int) and 10 <= value <= 200:
                    # 获取上下文，判断是否可能是窗口参数
                    parent = getattr(node, 'parent', None)
                    if parent and isinstance(parent, ast.Call):
                        # 检查函数名是否包含窗口相关关键词
                        if isinstance(parent.func, ast.Name):
                            func_name = parent.func.id.lower()
                            if any(keyword in func_name for keyword in window_keywords):
                                hardcoded_windows.append(f"函数 {func_name} 使用了硬编码窗口 {value}")
        
        return hardcoded_windows
    
    def _check_config_references(self, tree: ast.AST, content: str) -> List[str]:
        """检查对config的直接引用"""
        config_references = []
        
        # 检查导入config模块
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('from config import') or line.startswith('import config'):
                if 'config.analysis' in line or 'TREND_ANALYSIS_WINDOW' in line:
                    config_references.append(f"第{i+1}行: {line}")
        
        # 检查代码中的config引用
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    if node.value.id == 'config':
                        if hasattr(node, 'attr'):
                            config_references.append(f"使用了 config.{node.attr}")
        
        return config_references
    
    def _check_window_config_usage(self, tree: ast.AST, content: str) -> bool:
        """检查是否使用了WindowConfigManager"""
        # 检查导入
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if 'window_config' in alias.name:
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module and 'window_config' in node.module:
                    return True
        
        # 检查代码中的使用
        if self.window_config_class in content:
            for method in self.window_config_methods:
                if f"{self.window_config_class}.{method}" in content:
                    return True
        
        return False
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成验证报告"""
        report = []
        report.append("=" * 80)
        report.append("窗口配置使用验证报告")
        report.append("=" * 80)
        
        summary = results['summary']
        report.append(f"\n📊 总体统计:")
        report.append(f"   总Python文件数: {summary['total_python_files']}")
        report.append(f"   合规文件数: {summary['valid_files_count']}")
        report.append(f"   不合规文件数: {summary['invalid_files_count']}")
        report.append(f"   合规率: {summary['compliance_rate']:.1f}%")
        report.append(f"   硬编码窗口文件数: {summary['hardcoded_windows_count']}")
        report.append(f"   直接引用config文件数: {summary['direct_config_imports_count']}")
        
        if results['invalid_files']:
            report.append("\n⚠️ 不合规文件详情:")
            for item in results['invalid_files']:
                report.append(f"\n  📄 {item['file']}")
                for issue in item['issues']:
                    report.append(f"    • {issue}")
        
        if results['hardcoded_windows']:
            report.append("\n🔴 硬编码窗口的文件:")
            for file in results['hardcoded_windows']:
                report.append(f"  • {file}")
        
        if results['direct_config_imports']:
            report.append("\n🔴 直接引用config的文件:")
            for file in results['direct_config_imports']:
                report.append(f"  • {file}")
        
        if results['valid_files']:
            report.append("\n✅ 合规文件:")
            for file in results['valid_files'][:10]:  # 只显示前10个
                report.append(f"  • {file}")
            if len(results['valid_files']) > 10:
                report.append(f"  ... 还有 {len(results['valid_files']) - 10} 个文件")
        
        report.append("\n" + "=" * 80)
        report.append("建议:")
        
        if summary['hardcoded_windows_count'] > 0:
            report.append("1. 将硬编码窗口值替换为WindowConfigManager调用")
        
        if summary['direct_config_imports_count'] > 0:
            report.append("2. 移除对config的直接引用，改用WindowConfigManager")
        
        if summary['compliance_rate'] < 100:
            report.append("3. 完善剩余文件的窗口配置迁移")
        
        report.append("=" * 80)
        
        return "\n".join(report)

def validate_window_config_usage(project_root: str = None) -> Dict[str, Any]:
    """验证所有模块是否使用统一窗口配置"""
    validator = ConfigValidator(project_root)
    results = validator.validate_window_config_usage()
    report = validator.generate_report(results)
    
    print(report)
    return results

if __name__ == "__main__":
    # 命令行入口
    import argparse
    
    parser = argparse.ArgumentParser(description='验证窗口配置使用情况')
    parser.add_argument('--project-root', type=str, default='.', help='项目根目录路径')
    parser.add_argument('--output', type=str, help='输出报告文件路径')
    
    args = parser.parse_args()
    
    results = validate_window_config_usage(args.project_root)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(validator.generate_report(results))
        print(f"\n报告已保存到: {args.output}")
