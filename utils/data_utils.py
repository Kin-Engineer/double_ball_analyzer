# utils/data_utils.py
"""
数据工具函数
"""
import random
import numpy as np
from typing import List, Tuple

def generate_red_balls() -> List[int]:
    """生成符合双色球规律的红球号码"""
    while True:
        red_balls = random.sample(range(1, 34), 6)
        red_balls.sort()
        
        # 验证组合合理性
        if is_valid_red_combination(red_balls):
            return red_balls

def is_valid_red_combination(red_balls: List[int]) -> bool:
    """验证红球组合是否合理"""
    if len(red_balls) != 6 or len(set(red_balls)) != 6:
        return False
    
    ball_sum = sum(red_balls)
    if ball_sum < 60 or ball_sum > 150:
        return False
    
    ball_range = max(red_balls) - min(red_balls)
    if ball_range < 15 or ball_range > 32:
        return False
    
    odd_count = sum(1 for ball in red_balls if ball % 2 == 1)
    if odd_count == 0 or odd_count == 6:
        return False
    
    small_count = sum(1 for ball in red_balls if ball <= 16)
    if small_count == 0 or small_count == 6:
        return False
    
    consecutive_count = 0
    for i in range(len(red_balls) - 1):
        if red_balls[i + 1] - red_balls[i] == 1:
            consecutive_count += 1
    if consecutive_count > 2:
        return False
    
    return True

def calculate_ac_value(red_balls: List[int]) -> int:
    """计算AC值"""
    if len(red_balls) != 6:
        return 0
    
    diffs = set()
    for i in range(len(red_balls)):
        for j in range(i+1, len(red_balls)):
            diffs.add(abs(red_balls[i] - red_balls[j]))
    return len(diffs) - 5

def get_sum_range(red_sum: int) -> str:
    """获取和值区间分类"""
    if red_sum < 70:
        return "极小和(<70)"
    elif red_sum < 90:
        return "小和(70-89)"
    elif red_sum < 110:
        return "中和(90-109)"
    elif red_sum < 130:
        return "大和(110-129)"
    else:
        return "极大和(≥130)"

def calculate_interval_features(red_balls: List[int]) -> dict:
    """计算间距特征"""
    if len(red_balls) < 2:
        return {
            'max_interval': 0, 'min_interval': 0, 'avg_interval': 0,
            'big_interval_count': 0, 'interval_pattern': ''
        }
    
    intervals = []
    for i in range(1, len(red_balls)):
        interval = red_balls[i] - red_balls[i-1]
        intervals.append(interval)
    
    return {
        'max_interval': max(intervals) if intervals else 0,
        'min_interval': min(intervals) if intervals else 0,
        'avg_interval': sum(intervals) / len(intervals) if intervals else 0,
        'big_interval_count': sum(1 for x in intervals if x > 7),
        'interval_pattern': '-'.join(str(x) for x in intervals)
    }

def calculate_zone_distribution(red_balls: List[int]) -> dict:
    """计算三区分布"""
    zone1 = sum(1 for x in red_balls if 1 <= x <= 11)
    zone2 = sum(1 for x in red_balls if 12 <= x <= 22)
    zone3 = sum(1 for x in red_balls if 23 <= x <= 33)
    
    return {
        '一区(01-11)': zone1,
        '二区(12-22)': zone2, 
        '三区(23-33)': zone3
    }