"""
run.py
快速启动脚本
"""
#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_dependencies():
    """检查依赖"""
    required_packages = [
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'scikit-learn',
        'xgboost',
        'colorama',
        'pyyaml',
        'requests',
        'beautifulsoup4'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def setup_environment():
    """设置环境"""
    # 创建必要目录
    directories = [
        'data',
        'charts',
        'logs',
        'reports',
        'exports'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    # 检查配置文件
    config_file = 'config.yaml'
    if not Path(config_file).exists():
        print(f"⚠️  配置文件 {config_file} 不存在，正在创建默认配置...")
        from config import ConfigManager
        config = ConfigManager(config_file)
        config.save()
        print(f"✅ 默认配置文件已创建: {config_file}")

def run_system():
    """运行系统"""
    from main import main
    return main()

def install_dependencies():
    """安装依赖包"""
    print("正在安装依赖包...")
    
    requirements_file = 'requirements.txt'
    if Path(requirements_file).exists():
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
    else:
        # 创建requirements.txt
        requirements = [
            'numpy>=1.21.0',
            'pandas>=1.3.0',
            'matplotlib>=3.4.0',
            'scipy>=1.7.0',
            'scikit-learn>=0.24.0',
            'xgboost>=1.5.0',
            'colorama>=0.4.4',
            'pyyaml>=5.4.1',
            'requests>=2.26.0',
            'beautifulsoup4>=4.10.0',
            'seaborn>=0.11.0'
        ]
        
        with open(requirements_file, 'w') as f:
            f.write('\n'.join(requirements))
        
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
    
    print("✅ 依赖包安装完成")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="双色球分析系统 - 快速启动")
    parser.add_argument('--install', action='store_true', help='安装依赖包')
    parser.add_argument('--setup', action='store_true', help='初始化环境')
    parser.add_argument('--check', action='store_true', help='检查环境')
    
    args = parser.parse_args()
    
    if args.install:
        install_dependencies()
        return 0
    
    if args.setup:
        setup_environment()
        print("✅ 环境设置完成")
        return 0
    
    if args.check:
        missing = check_dependencies()
        if missing:
            print(f"❌ 缺少依赖包: {', '.join(missing)}")
            print("请运行: python run.py --install")
            return 1
        else:
            print("✅ 所有依赖包已安装")
            return 0
    
    # 检查环境
    missing = check_dependencies()
    if missing:
        print(f"❌ 缺少依赖包: {', '.join(missing)}")
        print("请运行: python run.py --install")
        return 1
    
    # 设置环境
    setup_environment()
    
    # 运行系统
    print("🚀 启动双色球分析系统...")
    return run_system()

if __name__ == "__main__":
    sys.exit(main())