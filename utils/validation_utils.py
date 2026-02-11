# utils/validation_utils.py
"""
数据验证工具函数
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger('validation_utils')

def validate_red_balls(red_balls: List[int]) -> Tuple[bool, str]:
    """验证红球号码"""
    if not isinstance(red_balls, list):
        return False, "红球必须是列表"
    
    if len(red_balls) != 6:
        return False, f"红球数量必须是6个，当前为{len(red_balls)}个"
    
    # 检查号码范围
    for ball in red_balls:
        if not isinstance(ball, int):
            return False, f"红球必须是整数，当前为{type(ball)}"
        if ball < 1 or ball > 33:
            return False, f"红球必须在1-33范围内，当前为{ball}"
    
    # 检查重复
    if len(set(red_balls)) != 6:
        return False, "红球号码不能重复"
    
    # 检查排序
    if red_balls != sorted(red_balls):
        return False, "红球号码必须按升序排列"
    
    return True, "验证通过"

def validate_blue_ball(blue_ball: int) -> Tuple[bool, str]:
    """验证蓝球号码"""
    if not isinstance(blue_ball, int):
        return False, f"蓝球必须是整数，当前为{type(blue_ball)}"
    
    if blue_ball < 1 or blue_ball > 16:
        return False, f"蓝球必须在1-16范围内，当前为{blue_ball}"
    
    return True, "验证通过"

def validate_issue_number(issue: str) -> Tuple[bool, str]:
    """验证期号格式"""
    if not isinstance(issue, str):
        return False, f"期号必须是字符串，当前为{type(issue)}"
    
    # 期号格式：年份+3位序号，如2023001
    pattern = r'^\d{7}$'
    if not re.match(pattern, issue):
        return False, f"期号格式错误，应为7位数字，当前为{issue}"
    
    # 验证年份（2003年及以后）
    year = int(issue[:4])
    if year < 2003 or year > datetime.now().year + 1:
        return False, f"期号年份不合理，当前为{year}"
    
    # 验证序号
    sequence = int(issue[4:])
    if sequence < 1 or sequence > 154:
        return False, f"期号序号不合理，当前为{sequence}"
    
    return True, "验证通过"

def validate_date(date_str: str) -> Tuple[bool, str]:
    """验证日期格式"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True, "验证通过"
    except ValueError:
        return False, f"日期格式错误，应为YYYY-MM-DD，当前为{date_str}"

def validate_record_data(record_data: Dict[str, Any]) -> Tuple[bool, str]:
    """验证完整的开奖记录数据"""
    required_fields = ['issue', 'date', 'red1', 'red2', 'red3', 'red4', 'red5', 'red6', 'blue']
    
    # 检查必填字段
    for field in required_fields:
        if field not in record_data:
            return False, f"缺少必填字段: {field}"
    
    # 验证期号
    issue_valid, issue_msg = validate_issue_number(record_data['issue'])
    if not issue_valid:
        return False, issue_msg
    
    # 验证日期
    date_valid, date_msg = validate_date(record_data['date'])
    if not date_valid:
        return False, date_msg
    
    # 验证红球
    red_balls = [
        record_data['red1'], record_data['red2'], record_data['red3'],
        record_data['red4'], record_data['red5'], record_data['red6']
    ]
    
    red_valid, red_msg = validate_red_balls(red_balls)
    if not red_valid:
        return False, red_msg
    
    # 验证蓝球
    blue_valid, blue_msg = validate_blue_ball(record_data['blue'])
    if not blue_valid:
        return False, blue_msg
    
    return True, "所有验证通过"

def validate_prediction_result(prediction: Dict[str, Any]) -> Tuple[bool, str]:
    """验证预测结果"""
    if not isinstance(prediction, dict):
        return False, "预测结果必须是字典"
    
    # 检查至少有一种组合
    valid_combinations = []
    for key in ['6_plus_1', '7_plus_1', '8_plus_1']:
        if key in prediction:
            combo = prediction[key]
            if isinstance(combo, dict):
                reds = combo.get('red_balls', [])
                blue = combo.get('blue_ball', 0)
                
                # 验证红球数量
                expected_reds = int(key[0])  # 从键名中提取数字
                if len(reds) != expected_reds:
                    return False, f"{key}组合应有{expected_reds}个红球，当前为{len(reds)}个"
                
                # 验证蓝球
                if not (1 <= blue <= 16):
                    return False, f"{key}组合蓝球应在1-16范围内，当前为{blue}"
                
                valid_combinations.append(key)
    
    if not valid_combinations:
        return False, "预测结果中至少应包含一种组合"
    
    return True, f"验证通过，有效的组合: {', '.join(valid_combinations)}"

def validate_config(config: Dict[str, Any]) -> Tuple[bool, str]:
    """验证配置数据"""
    required_sections = ['paths', 'analysis', 'prediction', 'database', 'system']
    
    for section in required_sections:
        if section not in config:
            return False, f"缺少配置节: {section}"
    
    # 验证路径配置
    paths = config.get('paths', {})
    required_paths = ['DATABASE_PATH', 'LOGS_DIR']
    for path_key in required_paths:
        if path_key not in paths:
            return False, f"缺少路径配置: {path_key}"
    
    # 验证分析配置
    analysis = config.get('analysis', {})
    required_windows = ['BASIC_STATS_WINDOW', 'TREND_ANALYSIS_WINDOW', 'FREQUENCY_ANALYSIS_WINDOW']
    for window in required_windows:
        if window not in analysis:
            return False, f"缺少分析窗口配置: {window}"
        if not isinstance(analysis[window], int) or analysis[window] <= 0:
            return False, f"分析窗口配置必须为正整数: {window}"
    
    return True, "配置验证通过"

def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_number_range(value: Any, min_val: float, max_val: float) -> Tuple[bool, str]:
    """验证数值范围"""
    try:
        num = float(value)
        if min_val <= num <= max_val:
            return True, f"数值{num}在范围[{min_val}, {max_val}]内"
        else:
            return False, f"数值{num}超出范围[{min_val}, {max_val}]"
    except (ValueError, TypeError):
        return False, f"无法转换为数值: {value}"