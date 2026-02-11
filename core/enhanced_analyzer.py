# core/enhanced_analyzer.py
"""
增强分析器，整合enhanced_analyzer.py的功能
"""
import logging
from typing import List, Dict, Any, Optional
from collections import Counter

from data.database import DoubleBallDatabase
from analysis.statistics import StatisticsAnalyzer

logger = logging.getLogger('enhanced_analyzer')

class EnhancedDoubleBallAnalyzer:
    """增强双色球分析器（整合enhanced_analyzer.py）"""
    
    def __init__(self, db_path: str = "double_ball.db"):
        self.db = DoubleBallDatabase(db_path)
        self.statistics = StatisticsAnalyzer(self.db)
    
    def analyze_hot_cold_with_trends(self) -> Dict[str, Any]:
        """热号冷号分析（带趋势）"""
        analysis = self.statistics.analyze_hot_cold(30, 100)
        trends = self.statistics.analyze_trends(30)
        
        return {
            'hot_cold': analysis,
            'trends': trends,
            'basic_stats': self.statistics.get_basic_statistics(50)
        }
    
    def find_best_matches(self, predicted_reds: List[int], top_n: int = 3) -> Dict[str, Any]:
        """寻找与预测号码匹配度最高的历史期数"""
        all_records = self.db.get_all_records()
        
        matches = []
        for record in all_records:
            historical_reds = set([record.red1, record.red2, record.red3, 
                                  record.red4, record.red5, record.red6])
            predicted_set = set(predicted_reds)
            
            # 计算匹配度
            match_count = len(historical_reds.intersection(predicted_set))
            if match_count >= 3:  # 至少匹配3个才考虑
                try:
                    issue_num = int(record.issue)
                    recent_weight = 1 + (issue_num / 10000)  # 简单加权
                except ValueError:
                    recent_weight = 1.0
                    
                weighted_score = match_count * recent_weight
                
                matches.append({
                    'issue': record.issue,
                    'match_count': match_count,
                    'matched_numbers': list(historical_reds.intersection(predicted_set)),
                    'score': weighted_score
                })
        
        # 按匹配度和权重排序
        sorted_matches = sorted(matches, key=lambda x: x['score'], reverse=True)[:top_n]
        
        # 计算重号概率
        latest_records = self.db.get_recent_records(1)
        if latest_records:
            latest = latest_records[0]
            latest_reds = set([latest.red1, latest.red2, latest.red3,
                              latest.red4, latest.red5, latest.red6])
            repeat_count = len(latest_reds.intersection(set(predicted_reds)))
            repeat_probability = self._calculate_repeat_probability()
            
            return {
                'top_matches': sorted_matches,
                'repeat_with_last': repeat_count,
                'repeat_probability': repeat_probability
            }
        
        return {'top_matches': sorted_matches}
    
    def _calculate_repeat_probability(self) -> float:
        """计算重号概率（基于历史数据）"""
        all_records = self.db.get_all_records()
        
        if len(all_records) < 2:
            return 0
        
        repeat_counts = []
        for i in range(1, len(all_records)):
            prev_reds = set([all_records[i-1].red1, all_records[i-1].red2, all_records[i-1].red3,
                            all_records[i-1].red4, all_records[i-1].red5, all_records[i-1].red6])
            curr_reds = set([all_records[i].red1, all_records[i].red2, all_records[i].red3,
                            all_records[i].red4, all_records[i].red5, all_records[i].red6])
            repeat_counts.append(len(prev_reds.intersection(curr_reds)))
        
        if repeat_counts:
            # 统计重号数量的分布
            repeat_distribution = Counter(repeat_counts)
            total = sum(repeat_distribution.values())
            
            # 计算至少重1个的概率
            at_least_one = sum([count for num, count in repeat_distribution.items() if num >= 1])
            return (at_least_one / total) * 100 if total > 0 else 0
        
        return 0
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """生成综合分析报告"""
        # 基础分析
        hot_cold = self.analyze_hot_cold_with_trends()
        
        # 数据库信息
        db_info = self.db.get_database_info()
        
        # 预测匹配度（示例）
        # 这里可以使用predictor生成预测后再匹配
        predicted_reds = [1, 5, 10, 15, 20, 25]  # 示例
        matches = self.find_best_matches(predicted_reds, 3)
        
        return {
            'database_info': db_info,
            'hot_cold_analysis': hot_cold,
            'matching_analysis': matches,
            'basic_statistics': self.statistics.get_basic_statistics(100)
        }

# 全局增强分析器实例
enhanced_analyzer = None

def get_enhanced_analyzer(db_path=None):
    """获取增强分析器实例"""
    global enhanced_analyzer
    if enhanced_analyzer is None:
        enhanced_analyzer = EnhancedDoubleBallAnalyzer(db_path)
    return enhanced_analyzer