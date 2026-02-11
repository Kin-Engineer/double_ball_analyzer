# core/analyzer.py
"""
主分析器，整合double_ball_master.py的核心功能
"""
import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from data.database import DoubleBallDatabase
from data.predictor import EnhancedPredictor
from analysis.statistics import StatisticsAnalyzer
from analysis.visualization import Visualization
from analysis.trend_analysis import TrendAnalyzer
from utils.color_utils import print_success, print_warning, print_error, print_info
from utils.window_config import WindowConfigManager  # 新增导入

logger = logging.getLogger('analyzer')

class DoubleBallAnalyzer:
    """双色球分析器（整合double_ball_master.py）"""
    
    def __init__(self, db_path: str = "double_ball.db"):
        self.db = DoubleBallDatabase(db_path)
        self.predictor = EnhancedPredictor(self.db)
        self.statistics = StatisticsAnalyzer(self.db)
        self.visualization = Visualization(self.db)
        self.trend_analyzer = TrendAnalyzer(self.db)
        
        # 获取窗口配置
        try:
            self.window_config = WindowConfigManager.get_instance()
            self.short_window = self.window_config.get_window_by_name('short_term')
            self.long_window = self.window_config.get_window_by_name('long_term')
            logger.info(f"分析器初始化，窗口配置: 短期={self.short_window}期, 长期={self.long_window}期")
        except Exception as e:
            self.short_window = 30
            self.long_window = 100
            logger.warning(f"使用默认窗口配置: 短期={self.short_window}期, 长期={self.long_window}期，错误: {e}")
    
    def generate_analysis_report(self) -> Dict[str, Any]:
        """生成分析报告"""
        print_success("开始生成分析报告...")
        
        # 基本统计信息
        stats = self.db.get_statistics()
        
        # 热号冷号分析 - 使用统一窗口配置
        hot_cold_analysis = self.statistics.analyze_hot_cold(self.short_window, self.long_window)
        
        # 趋势分析 - 使用统一窗口配置
        trends = self.trend_analyzer.analyze_recent_trends(self.short_window)
        
        # 预测
        predictions = self.predictor.predict_all_combinations()
        
        # 构建报告
        report = {
            'basic_stats': stats,
            'hot_cold_analysis': hot_cold_analysis,
            'trends': trends,
            'predictions': predictions,
            'generated_at': datetime.now().isoformat(),
            'window_used': {
                'short_term': self.short_window,
                'long_term': self.long_window
            }
        }
        
        print_success("分析报告生成完成")
        return report
    
    def get_recommendations(self) -> List[Dict[str, Any]]:
        """获取推荐组合"""
        recommendations = []
        
        # 策略1: 热号优先 - 使用统一窗口配置
        hot_reds = self.predictor.get_hot_numbers(self.short_window, 15)
        if len(hot_reds) >= 6:
            reds = sorted(random.sample(hot_reds, 6))
            blue = random.randint(1, 16)
            odd_count = sum(1 for x in reds if x % 2 == 1)
            recommendations.append({
                'reds': reds,
                'blue': blue,
                'strategy': '热号优先策略',
                'window_used': self.short_window,
                'odd_even_ratio': f"{odd_count}:{6-odd_count}",
                'red_sum': sum(reds)
            })
        
        # 策略2: 均衡策略 - 使用统一窗口配置
        hot_reds = self.predictor.get_hot_numbers(self.short_window, 10)
        cold_reds = self.predictor.get_cold_numbers(self.short_window, 10)
        warm_numbers = [num for num in range(1, 34) 
                       if num not in hot_reds and num not in cold_reds]
        
        if len(hot_reds) >= 2 and len(warm_numbers) >= 2 and len(cold_reds) >= 2:
            reds = sorted(random.sample(hot_reds, 2) + 
                         random.sample(warm_numbers, 2) + 
                         random.sample(cold_reds, 2))
            blue = random.randint(1, 16)
            odd_count = sum(1 for x in reds if x % 2 == 1)
            recommendations.append({
                'reds': reds,
                'blue': blue,
                'strategy': '均衡策略 (2热2温2冷)',
                'window_used': self.short_window,
                'odd_even_ratio': f"{odd_count}:{6-odd_count}",
                'red_sum': sum(reds)
            })
        
        # 策略3: 随机策略
        reds = sorted(random.sample(range(1, 34), 6))
        blue = random.randint(1, 16)
        odd_count = sum(1 for x in reds if x % 2 == 1)
        recommendations.append({
            'reds': reds,
            'blue': blue,
            'strategy': '随机选择策略',
            'odd_even_ratio': f"{odd_count}:{6-odd_count}",
            'red_sum': sum(reds)
        })
        
        return recommendations
    
    def create_visualizations(self, output_dir: str = "visualizations") -> bool:
        """创建可视化图表"""
        return self.visualization.create_all_visualizations(output_dir)
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        return self.db.get_database_info()
    
    def get_window_info(self) -> Dict[str, int]:
        """获取窗口配置信息"""
        return {
            'short_window': self.short_window,
            'long_window': self.long_window
        }

# 全局分析器实例
analyzer = None

def get_analyzer(db_path=None):
    """获取分析器实例"""
    global analyzer
    if analyzer is None:
        analyzer = DoubleBallAnalyzer(db_path)
    return analyzer