# data/advanced_processor.py
import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
import numpy as np
from datetime import datetime
from .database import DoubleBallDatabase
from .models import DoubleBallRecord

logger = logging.getLogger('advanced_processor')

class AdvancedFeatureProcessor:
    """高级特征处理器"""
    
    def __init__(self, config=None):
        self.history_cache = {}
        # 如果config为None，使用默认配置
        if config is None:
            self.config = type('DefaultConfig', (), {
                'heat_cold_window': 15,
                'recent_analysis_window': 10,
                'trend_analysis_window': 5
            })()
        else:
            self.config = config
    
    def process_all_features(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """处理所有高级特征"""
        if len(records) < 2:
            return records
            
        logger.info("开始计算所有高级特征...")
        
        # 第一阶段：基础特征（已在processor.py中处理）
        # 第二阶段：遗漏值和热温冷分析
        records = self.process_stage2_features(records)
        
        # 第三阶段：遗传和趋势分析
        records = self.process_stage3_features(records)
        
        logger.info(f"高级特征计算完成，共处理{len(records)}条记录")
        return records
    
    def process_stage2_features(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """处理第二阶段特征：遗漏值和热温冷分析"""
        if len(records) < 2:
            return records
            
        logger.info("开始计算第二阶段特征（遗漏值和热温冷分析）...")
        
        # 计算遗漏值
        records = self._calculate_omission_features(records)
        
        # 计算热温冷状态
        records = self._calculate_heat_status_features(records)
        
        # 热冷号分析
        records = self._calculate_hot_cold_analysis(records)
        
        logger.info("第二阶段特征计算完成")
        return records
    
    def process_stage3_features(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """处理第三阶段特征：遗传和趋势分析"""
        if len(records) < 2:
            return records
            
        logger.info("开始计算第三阶段特征（遗传和趋势分析）...")
        
        # 计算遗传特征
        records = self._calculate_genetic_features(records)
        
        # 计算趋势特征
        records = self._calculate_trend_features(records)
        
        # 计算模式识别
        records = self._calculate_pattern_features(records)
        
        logger.info("第三阶段特征计算完成")
        return records
    
    def _calculate_omission_features(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """计算遗漏值特征"""
        red_omission_history = {i: 0 for i in range(1, 34)}
        blue_omission_history = {i: 0 for i in range(1, 17)}
        
        for i, record in enumerate(records):
            current_reds = {record.red1, record.red2, record.red3, 
                           record.red4, record.red5, record.red6}
            current_blue = record.blue
            
            # 更新红球遗漏值
            record_red_omission = {}
            for ball in range(1, 34):
                if ball in current_reds:
                    record_red_omission[ball] = 0
                    red_omission_history[ball] = 0
                else:
                    red_omission_history[ball] += 1
                    record_red_omission[ball] = red_omission_history[ball]
            
            record.red_omission = record_red_omission
            
            # 更新蓝球遗漏值
            for ball in range(1, 17):
                if ball == current_blue:
                    blue_omission_history[ball] = 0
                    record.blue_omission = 0
                else:
                    blue_omission_history[ball] += 1
            
        return records
    
    def _calculate_heat_status_features(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """计算热温冷状态"""
        if len(records) < 20:
            return records
            
        # 计算全局频率
        all_red_freq = Counter()
        all_blue_freq = Counter()
        
        for record in records:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            for ball in reds:
                all_red_freq[ball] += 1
            all_blue_freq[record.blue] += 1
        
        avg_red_freq = sum(all_red_freq.values()) / len(all_red_freq)
        avg_blue_freq = sum(all_blue_freq.values()) / len(all_blue_freq)
        
        for i, record in enumerate(records):
            # 计算近期频率（最近15期）
            recent_start = max(0, i - self.config.heat_cold_window)
            recent_records = records[recent_start:i+1]
            
            recent_red_freq = Counter()
            recent_blue_freq = Counter()
            
            for rec in recent_records:
                reds = [rec.red1, rec.red2, rec.red3, rec.red4, rec.red5, rec.red6]
                for ball in reds:
                    recent_red_freq[ball] += 1
                recent_blue_freq[rec.blue] += 1
            
            # 红球热温冷
            red_heat_status = {}
            for ball in range(1, 34):
                recent_count = recent_red_freq.get(ball, 0)
                if recent_count >= avg_red_freq * 1.3:
                    red_heat_status[ball] = "热"
                elif recent_count <= avg_red_freq * 0.7:
                    red_heat_status[ball] = "冷"
                else:
                    red_heat_status[ball] = "温"
            
            record.red_heat_status = red_heat_status
            
            # 蓝球热温冷
            blue_recent = recent_blue_freq.get(record.blue, 0)
            if blue_recent >= avg_blue_freq * 1.5:
                record.blue_heat_status = "热"
            elif blue_recent <= avg_blue_freq * 0.5:
                record.blue_heat_status = "冷"
            else:
                record.blue_heat_status = "温"
        
        return records
    
    def _calculate_hot_cold_analysis(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """热冷号分析"""
        if len(records) < 10:
            return records
            
        for i, record in enumerate(records):
            # 近期热门号码（出现次数最多的）
            recent_start = max(0, i - self.config.recent_analysis_window)
            recent_records = records[recent_start:i+1]
            
            recent_freq = Counter()
            for rec in recent_records:
                reds = [rec.red1, rec.red2, rec.red3, rec.red4, rec.red5, rec.red6]
                for ball in reds:
                    recent_freq[ball] += 1
            
            # 热门号码（出现3次以上）
            hot_balls = [ball for ball, count in recent_freq.items() if count >= 3]
            record.hot_red_balls = hot_balls[:8]  # 取前8个
            
            # 冷门号码（遗漏值大于10期）
            if record.red_omission:
                cold_balls = [ball for ball, omission in record.red_omission.items() 
                            if omission > 10]
                record.cold_red_balls = cold_balls[:10]  # 取前10个
        
        return records
    
    def _calculate_genetic_features(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """计算遗传特征"""
        for i in range(1, len(records)):
            current = records[i]
            previous = records[i-1]
            
            current_reds = {current.red1, current.red2, current.red3,
                           current.red4, current.red5, current.red6}
            previous_reds = {previous.red1, previous.red2, previous.red3,
                            previous.red4, previous.red5, previous.red6}
            
            inherited_count = len(current_reds & previous_reds)
            current.inherited_reds = inherited_count
            current.inherited_blue = 1 if current.blue == previous.blue else 0
        
        return records
    
    def _calculate_trend_features(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """计算趋势特征"""
        if len(records) < 5:
            return records
            
        for i in range(4, len(records)):
            current = records[i]
            
            # 和值趋势
            recent_sums = [
                records[i-4].red_sum or 0,
                records[i-3].red_sum or 0,
                records[i-2].red_sum or 0,
                records[i-1].red_sum or 0,
                current.red_sum or 0
            ]
            
            # 简单趋势判断
            if recent_sums[-1] > recent_sums[-2] > recent_sums[-3]:
                current.trend_direction = "上升"
            elif recent_sums[-1] < recent_sums[-2] < recent_sums[-3]:
                current.trend_direction = "下降"
            else:
                current.trend_direction = "震荡"
            
            # 连出次数
            current_reds = {current.red1, current.red2, current.red3,
                           current.red4, current.red5, current.red6}
            
            consecutive = 0
            for j in range(i-1, max(-1, i-5), -1):
                prev_reds = {records[j].red1, records[j].red2, records[j].red3,
                            records[j].red4, records[j].red5, records[j].red6}
                if current_reds & prev_reds:
                    consecutive += 1
                else:
                    break
            
            current.consecutive_appear = consecutive
            
            # 平均遗漏期数
            if current.red_omission:
                avg_omission = np.mean(list(current.red_omission.values()))
                current.missing_periods = int(avg_omission)
        
        return records
    
    def _calculate_pattern_features(self, records: List[DoubleBallRecord]) -> List[DoubleBallRecord]:
        """计算模式识别特征"""
        for record in records:
            # 根据AC值判断模式
            if record.ac_value is not None:
                if record.ac_value >= 8:
                    record.pattern_type = "复杂"
                elif record.ac_value <= 5:
                    record.pattern_type = "简单"
                else:
                    record.pattern_type = "中等"
            
            # 风险等级评估
            risk_factors = 0
            
            # 连号过多风险
            if record.big_interval_count and record.big_interval_count >= 3:
                risk_factors += 1
            
            # 奇偶比例极端风险
            if record.red_odd_count in [0, 6]:
                risk_factors += 1
            
            # 和值极端风险
            if record.red_sum and (record.red_sum < 70 or record.red_sum > 140):
                risk_factors += 1
            
            # 确定风险等级
            if risk_factors >= 2:
                record.risk_level = "高风险"
            elif risk_factors == 1:
                record.risk_level = "中风险"
            else:
                record.risk_level = "低风险"
        
        return records
    
    def get_advanced_analysis(self, records: List[DoubleBallRecord]) -> Dict[str, Any]:
        """获取高级分析结果"""
        if not records:
            return {}
            
        latest = records[-1]
        analysis = {
            'stage1': {
                'ac_value': latest.ac_value,
                'sum_tail': latest.sum_tail,
                'head_tail_range': latest.head_tail_range,
                'zone_distribution': latest.zone_distribution
            },
            'stage2': {
                'hot_balls': latest.hot_red_balls[:6] if hasattr(latest, 'hot_red_balls') else [],
                'cold_balls': latest.cold_red_balls[:6] if hasattr(latest, 'cold_red_balls') else [],
                'avg_omission': latest.missing_periods or 0,
                'red_heat_status': latest.red_heat_status if hasattr(latest, 'red_heat_status') else {}
            },
            'stage3': {
                'inherited_reds': latest.inherited_reds or 0,
                'trend': latest.trend_direction or "未知",
                'pattern': latest.pattern_type or "未知",
                'risk': latest.risk_level or "未知",
                'consecutive_appear': latest.consecutive_appear or 0
            }
        }
        
        return analysis

# 全局处理器实例
advanced_processor = AdvancedFeatureProcessor()

if __name__ == "__main__":
    # 测试代码
    print("高级特征处理器模块加载成功")
    print("功能包括：遗漏值分析、热温冷分析、遗传趋势分析、模式识别等")