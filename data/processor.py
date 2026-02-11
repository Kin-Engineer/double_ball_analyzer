# data/processor.py
"""
基础数据处理模块
"""
import logging
from typing import List
from .models import DoubleBallRecord
from utils.data_utils import calculate_ac_value, get_sum_range, calculate_interval_features, calculate_zone_distribution

logger = logging.getLogger('processor')

class BaseDataProcessor:
    """基础数据处理器"""
    
    @staticmethod
    def process_record(record: DoubleBallRecord) -> DoubleBallRecord:
        """处理单条记录的基础特征"""
        red_balls = [record.red1, record.red2, record.red3, 
                    record.red4, record.red5, record.red6]
        red_balls_sorted = sorted(red_balls)
        
        # 计算基础特征（如果尚未计算）
        if not record.red_sum:
            record.calculate_basic_features()
        
        # 计算第一阶段特征
        record.ac_value = calculate_ac_value(red_balls_sorted)
        
        if record.red_sum:
            record.sum_tail = record.red_sum % 10
            record.sum_range = get_sum_range(record.red_sum)
        
        # 计算间距特征
        interval_features = calculate_interval_features(red_balls_sorted)
        record.max_interval = interval_features['max_interval']
        record.min_interval = interval_features['min_interval']
        record.avg_interval = interval_features['avg_interval']
        record.big_interval_count = interval_features['big_interval_count']
        record.interval_pattern = interval_features['interval_pattern']
        
        # 计算位置特征
        record.head_number = red_balls_sorted[0]
        record.tail_number = red_balls_sorted[-1]
        record.head_tail_range = red_balls_sorted[-1] - red_balls_sorted[0]
        
        # 计算区间分布
        record.zone_distribution = calculate_zone_distribution(red_balls_sorted)
        
        return record
    
    def process_records(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """批量处理记录"""
        processed = []
        for record in records:
            try:
                processed_record = self.process_record(record)
                processed.append(processed_record)
            except Exception as e:
                logger.error(f"处理记录 {record.issue} 时出错: {e}")
        return processed

# 全局处理器实例
processor = BaseDataProcessor()