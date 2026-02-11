# analysis/statistics.py
"""
统计分析模块，从enhanced_analyzer.py提取
"""
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
import numpy as np

from data.models import DoubleBallRecord
from data.database import DoubleBallDatabase

logger = logging.getLogger('statistics')

class StatisticsAnalyzer:
    """统计分析器"""
    
    def __init__(self, database: DoubleBallDatabase):
        self.db = database
    
    def analyze_hot_cold(self, recent_n: int = 30, all_data_n: int = 100) -> Optional[Dict[str, Any]]:
        """热号冷号分析"""
        # 获取数据
        recent_data = self.db.get_recent_records(recent_n)
        all_data = self.db.get_recent_records(all_data_n) if all_data_n > recent_n else recent_data
        
        if not recent_data or not all_data:
            return None
        
        # 统计最近N期号码出现次数
        red_counts = Counter()
        blue_counts = Counter()
        
        for record in recent_data:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            for ball in reds:
                red_counts[ball] += 1
            blue_counts[record.blue] += 1
        
        # 计算阈值：前30%为热号，后30%为冷号
        red_numbers = list(red_counts.keys())
        if not red_numbers:
            return None
        
        red_sorted = sorted(red_counts.items(), key=lambda x: x[1], reverse=True)
        hot_threshold = max(1, int(len(red_sorted) * 0.3))
        hot_numbers = [num for num, _ in red_sorted[:hot_threshold]]
        cold_numbers = [num for num, _ in red_sorted[-hot_threshold:]] if len(red_sorted) >= hot_threshold*2 else []
        
        # 计算历史频率（用于预测概率）
        historical_red_counts = Counter()
        for record in all_data:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            for ball in reds:
                historical_red_counts[ball] += 1
        
        total_draws = len(all_data)
        
        # 计算每个号码的出现概率
        red_probabilities = {}
        for num in range(1, 34):
            count = historical_red_counts.get(num, 0)
            # 使用拉普拉斯平滑
            probability = (count + 1) / (total_draws + 33)
            red_probabilities[num] = probability
        
        # 分析最新一期
        latest_records = self.db.get_recent_records(1)
        if not latest_records:
            return None
        
        latest = latest_records[0]
        latest_reds = [latest.red1, latest.red2, latest.red3, 
                      latest.red4, latest.red5, latest.red6]
        latest_blue = latest.blue
        
        latest_analysis = []
        for red in latest_reds:
            status = "热号" if red in hot_numbers else ("冷号" if red in cold_numbers else "温号")
            prob = red_probabilities.get(red, 0)
            latest_analysis.append({
                'number': red,
                'status': status,
                'frequency': red_counts.get(red, 0),
                'probability': prob,
                'next_probability': self._calculate_next_probability(red, red_counts, total_draws)
            })
        
        # 蓝球分析
        blue_freq = blue_counts.get(latest_blue, 0)
        blue_status = "热号" if blue_freq >= 2 else ("冷号" if blue_freq == 0 else "温号")
        
        return {
            'hot_reds': hot_numbers,
            'cold_reds': cold_numbers,
            'red_probabilities': red_probabilities,
            'latest_analysis': latest_analysis,
            'latest_blue': {
                'number': latest_blue,
                'status': blue_status,
                'frequency': blue_freq
            },
            'recent_n': recent_n
        }
    
    def _calculate_next_probability(self, number, red_counts, total_draws):
        """计算下一期出现的概率（使用贝叶斯方法）"""
        # 当前频率
        current_freq = red_counts.get(number, 0)
        
        # 基础概率（历史平均）
        base_prob = 6 / 33  # 每个红球的理论概率
        
        # 加权概率：70%基于近期表现，30%基于理论概率
        if total_draws > 0:
            recent_prob = current_freq / total_draws
            weighted_prob = 0.7 * recent_prob + 0.3 * base_prob
            return min(weighted_prob * 100, 30)  # 限制最大概率
        return base_prob * 100
    
    def analyze_trends(self, window_n: int = 30) -> Optional[List[Dict[str, Any]]]:
        """分析趋势"""
        all_data = self.db.get_recent_records(window_n)
        if not all_data:
            return None
        
        trends = []
        window_size = min(10, window_n // 3)
        
        for i in range(len(all_data) - window_size + 1):
            window_data = all_data[i:i+window_size]
            
            # 统计窗口内的号码频率
            red_counts = Counter()
            for record in window_data:
                reds = [record.red1, record.red2, record.red3, 
                       record.red4, record.red5, record.red6]
                for ball in reds:
                    red_counts[ball] += 1
            
            # 确定热号冷号
            sorted_counts = sorted(red_counts.items(), key=lambda x: x[1], reverse=True)
            hot_threshold = max(1, int(len(sorted_counts) * 0.3))
            hot_count = len([num for num, count in sorted_counts[:hot_threshold] if count >= 2])
            cold_count = len([num for num, count in sorted_counts[-hot_threshold:] if count == 0])
            
            trends.append({
                'window_start': all_data[i].issue,
                'hot_count': hot_count,
                'cold_count': cold_count,
                'avg_frequency': np.mean([count for _, count in sorted_counts]) if sorted_counts else 0
            })
        
        return trends
    
    def get_basic_statistics(self, limit: int = 100) -> Dict[str, Any]:
        """获取基本统计信息"""
        records = self.db.get_recent_records(limit)
        if not records:
            return {}
        
        stats = {
            'total_issues': len(records),
            'red_distribution': Counter(),
            'blue_distribution': Counter(),
            'sum_range': Counter(),
            'odd_even_ratio': [],
            'repeat_counts': []
        }
        
        # 统计号码分布
        for record in records:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            for ball in reds:
                stats['red_distribution'][ball] += 1
            stats['blue_distribution'][record.blue] += 1
            
            # 计算和值
            red_sum = sum(reds)
            sum_range = (red_sum // 10) * 10
            stats['sum_range'][f"{sum_range}-{sum_range+9}"] += 1
            
            # 计算奇偶比
            odd_count = sum(1 for ball in reds if ball % 2 == 1)
            stats['odd_even_ratio'].append(f"{odd_count}:{6-odd_count}")
        
        # 计算重号
        for i in range(1, len(records)):
            prev_reds = set([records[i-1].red1, records[i-1].red2, records[i-1].red3,
                            records[i-1].red4, records[i-1].red5, records[i-1].red6])
            curr_reds = set([records[i].red1, records[i].red2, records[i].red3,
                            records[i].red4, records[i].red5, records[i].red6])
            stats['repeat_counts'].append(len(prev_reds.intersection(curr_reds)))
        
        return stats

# 全局分析器实例
statistics_analyzer = None

def get_statistics_analyzer(db_path=None):
    """获取统计分析器实例"""
    global statistics_analyzer
    if statistics_analyzer is None:
        db = DoubleBallDatabase(db_path)
        statistics_analyzer = StatisticsAnalyzer(db)
    return statistics_analyzer