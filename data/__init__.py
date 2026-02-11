# data/__init__.py
"""
数据模块
"""

from .database import DoubleBallDatabase
from .models import DoubleBallRecord
from .predictor import BasePredictor, get_predictor
from .crawler import DoubleBallCrawler

# 如果使用增强预测器，也可以导入
# try:
#     from .enhanced_predictor import ProbabilityEnhancedPredictor
# except ImportError:
#     pass  # 如果文件不存在就跳过

__all__ = [
    'DoubleBallDatabase',
    'DoubleBallRecord',
    'BasePredictor',
    'EnhancedPredictor',
    'get_predictor',
    'DoubleBallCrawler'
]
