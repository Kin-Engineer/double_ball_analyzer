# core/unified_analyzer.py
"""
统一分析接口，整合所有分析功能
"""
import logging
from typing import Dict, Any

from core.analyzer import DoubleBallAnalyzer
from core.enhanced_analyzer import EnhancedDoubleBallAnalyzer
from data.predictor import EnhancedPredictor
from analysis.statistics import StatisticsAnalyzer
from analysis.visualization import Visualization
from analysis.trend_analysis import TrendAnalyzer

logger = logging.getLogger('unified_analyzer')

class UnifiedAnalyzer:
    """统一分析器，提供所有分析功能"""
    
    def __init__(self, db_path: str = "double_ball.db"):
        self.db_path = db_path
        
        # 初始化各个分析器
        self.analyzer = DoubleBallAnalyzer(db_path)
        self.enhanced_analyzer = EnhancedDoubleBallAnalyzer(db_path)
        self.predictor = EnhancedPredictor(self.analyzer.db)
        self.statistics = StatisticsAnalyzer(self.analyzer.db)
        self.visualization = Visualization(self.analyzer.db)
        self.trend_analyzer = TrendAnalyzer(self.analyzer.db)
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """运行完整分析"""
        result = {}
        
        # 1. 基础统计
        result['basic_stats'] = self.statistics.get_basic_statistics(100)
        
        # 2. 热号冷号分析
        result['hot_cold'] = self.statistics.analyze_hot_cold(30, 100)
        
        # 3. 趋势分析
        result['trends'] = self.trend_analyzer.analyze_recent_trends(30)
        
        # 4. 预测
        result['predictions'] = self.predictor.predict_all_combinations()
        
        # 5. 数据库信息
        result['database'] = self.analyzer.db.get_database_info()
        
        # 6. 推荐组合
        result['recommendations'] = self.analyzer.get_recommendations()
        
        return result
    
    def run_prediction_only(self) -> Dict[str, Any]:
        """仅运行预测"""
        return self.predictor.predict_all_combinations()
    
    def run_analysis_only(self) -> Dict[str, Any]:
        """仅运行分析"""
        result = {}
        result['basic_stats'] = self.statistics.get_basic_statistics(100)
        result['hot_cold'] = self.statistics.analyze_hot_cold(30, 100)
        result['trends'] = self.trend_analyzer.analyze_recent_trends(30)
        return result
    
    def generate_visual_report(self, output_dir: str = "reports") -> bool:
        """生成可视化报告"""
        return self.visualization.create_all_visualizations(output_dir)

# 全局统一分析器实例
unified_analyzer = None

def get_unified_analyzer(db_path=None):
    """获取统一分析器实例"""
    global unified_analyzer
    if unified_analyzer is None:
        unified_analyzer = UnifiedAnalyzer(db_path)
    return unified_analyzer