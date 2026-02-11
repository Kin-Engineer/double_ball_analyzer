# analysis/trend_analysis.py
"""
趋势分析模块
"""
import logging
from typing import List, Dict, Any
import numpy as np
from collections import Counter

from data.models import DoubleBallRecord
from data.database import DoubleBallDatabase

logger = logging.getLogger('trend_analysis')

class TrendAnalyzer:
    """趋势分析器"""
    
    def __init__(self, database: DoubleBallDatabase):
        self.db = database
    
    def analyze_recent_trends(self, window: int = None) -> Dict[str, Any]:  # 修改：window参数默认为None
        """分析近期趋势"""
        # 如果未指定window，从WindowConfigManager获取
        if window is None:
            try:
                from utils.window_config import WindowConfigManager
                window = WindowConfigManager.get_window_by_name('short_term')
                logger.info(f"使用统一窗口配置: {window}期")
            except (ImportError, AttributeError):
                window = 30  # 备用值
                logger.warning(f"使用默认窗口: {window}期")
        
        records = self.db.get_recent_records(window)
        if len(records) < 10:
            return {}
        
        # 和值趋势
        sums = []
        for record in records:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            sums.append(sum(reds))
        
        sum_trend = self._calculate_trend_direction(sums[-5:])
        
        # 奇偶比趋势
        odd_ratios = []
        for record in records:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            odd_count = sum(1 for ball in reds if ball % 2 == 1)
            odd_ratios.append(odd_count)
        
        odd_trend = self._calculate_trend_direction(odd_ratios[-5:])
        
        # 热门号码趋势
        hot_reds = self._get_hot_numbers(records)
        
        return {
            'sum_trend': sum_trend,
            'odd_trend': odd_trend,
            'hot_reds': hot_reds[:10],
            'current_sum': sums[-1] if sums else 0,
            'current_odd_ratio': odd_ratios[-1] if odd_ratios else 0,
            'window_used': window  # 添加使用的窗口信息
        }
    
    def _calculate_trend_direction(self, values: List[float]) -> str:
        """计算趋势方向"""
        if len(values) < 2:
            return "未知"
        
        # 简单线性趋势判断
        increasing = 0
        decreasing = 0
        
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                increasing += 1
            elif values[i] < values[i-1]:
                decreasing += 1
        
        if increasing > decreasing * 1.5:
            return "上升"
        elif decreasing > increasing * 1.5:
            return "下降"
        else:
            return "震荡"
    
    def _get_hot_numbers(self, records: List[DoubleBallRecord]) -> List[tuple]:
        """获取热门号码"""
        red_counts = Counter()
        for record in records:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            for ball in reds:
                red_counts[ball] += 1
        
        return red_counts.most_common()

# 全局趋势分析器实例
trend_analyzer = None

def get_trend_analyzer(db_path=None):
    """获取趋势分析器实例"""
    global trend_analyzer
    if trend_analyzer is None:
        db = DoubleBallDatabase(db_path)
        trend_analyzer = TrendAnalyzer(db)
    return trend_analyzer