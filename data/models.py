# data/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger('models')

@dataclass
class DoubleBallRecord:
    """双色球开奖记录数据模型 - 增强版"""
    
    # 基本开奖信息
    issue: str
    draw_date: str
    red1: int
    red2: int
    red3: int
    red4: int
    red5: int
    red6: int
    blue: int
    sales: float = 0.0
    pool_money: float = 0.0
    
    # 时间特征
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    weekday: Optional[str] = None
    weekday_num: Optional[int] = None
    quarter: Optional[int] = None
    season: Optional[str] = None
    month_type: Optional[str] = None
    is_weekend: Optional[int] = None
    
    # 基础统计特征
    red_sum: Optional[int] = None
    red_avg: Optional[float] = None
    red_odd_count: Optional[int] = None
    red_even_count: Optional[int] = None
    red_prime_count: Optional[int] = None
    red_range: Optional[int] = None
    blue_zone: Optional[str] = None
    
    # === 第一阶段：新增基础特征 ===
    ac_value: Optional[int] = None
    sum_tail: Optional[int] = None
    sum_range: Optional[str] = None
    max_interval: Optional[int] = None
    min_interval: Optional[int] = None
    avg_interval: Optional[float] = None
    head_number: Optional[int] = None
    tail_number: Optional[int] = None
    head_tail_range: Optional[int] = None
    big_interval_count: Optional[int] = None
    interval_pattern: Optional[str] = None
    zone_distribution: Optional[Dict[str, int]] = field(default_factory=dict)
    
    # === 第二阶段：遗漏和热温冷特征 ===
    red_omission: Optional[Dict[int, int]] = field(default_factory=dict)
    blue_omission: Optional[int] = None
    red_heat_status: Optional[Dict[int, str]] = field(default_factory=dict)
    blue_heat_status: Optional[str] = None
    cold_red_balls: Optional[List[int]] = field(default_factory=list)
    hot_red_balls: Optional[List[int]] = field(default_factory=list)
    hot_cold_analysis: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    # === 第三阶段：遗传和高级特征 ===
    inherited_reds: Optional[int] = None
    inherited_blue: Optional[int] = None
    consecutive_appear: Optional[int] = None
    missing_periods: Optional[int] = None
    trend_direction: Optional[str] = None
    pattern_type: Optional[str] = None
    risk_level: Optional[str] = None

    def __post_init__(self):
        """初始化后计算基础特征"""
        # data/models.py
        from dataclasses import dataclass, field
        from datetime import datetime
        from typing import Optional, Dict, List, Any
        import logging

        logger = logging.getLogger('models')

        @dataclass
        class DoubleBallRecord:
            """双色球开奖记录数据模型 - 增强版"""

            # 基本开奖信息
            issue: str
            red1: int
            red2: int
            red3: int
            red4: int
            red5: int
            red6: int
            blue: int
            draw_date: str = ""  # 添加默认值
            sales: float = 0.0
            pool_money: float = 0.0

        try:
            # 确保所有必需的属性都存在
            if not hasattr(self, 'red_sum'):
                red_balls = [self.red1, self.red2, self.red3, self.red4, self.red5, self.red6]
                self.red_sum = sum(red_balls)

            # 调用计算方法
            self.calculate_basic_features()
            self.calculate_stage1_features()
        except Exception as e:
            logger.error(f"初始化 DoubleBallRecord 时出错（期号: {self.issue}）: {e}")
            # 设置默认值避免后续错误
            if not hasattr(self, 'red_sum'):
                self.red_sum = 0
            if not hasattr(self, 'sum_tail'):
                self.sum_tail = None
            if not hasattr(self, 'sum_range'):
                self.sum_range = None

    def calculate_basic_features(self):
        """计算基础特征"""
        red_balls = [self.red1, self.red2, self.red3, self.red4, self.red5, self.red6]

        # 基本统计
        self.red_sum = sum(red_balls)
        self.red_avg = round(self.red_sum / 6, 2) if self.red_sum else 0

    def calculate_stage1_features(self):
        """计算第一阶段特征 - 修复版本"""
        red_balls = [self.red1, self.red2, self.red3, self.red4, self.red5, self.red6]
        red_balls_sorted = sorted(red_balls)

        # AC值计算
        self.ac_value = self._calculate_ac_value(red_balls_sorted)

        # 和值特征 - 安全访问
        if hasattr(self, 'red_sum') and self.red_sum is not None:
            self.sum_tail = self.red_sum % 10
            self.sum_range = self._get_sum_range(self.red_sum)
        else:
            # 如果 red_sum 不存在，重新计算
            self.red_sum = sum(red_balls)
            self.sum_tail = self.red_sum % 10
            self.sum_range = self._get_sum_range(self.red_sum)

        # 间距特征
        interval_features = self._calculate_interval_features(red_balls_sorted)
        self.max_interval = interval_features['max_interval']
        self.min_interval = interval_features['min_interval']
        self.avg_interval = interval_features['avg_interval']
        self.big_interval_count = interval_features['big_interval_count']
        self.interval_pattern = interval_features['interval_pattern']

        # 位置特征
        self.head_number = red_balls_sorted[0]
        self.tail_number = red_balls_sorted[-1]
        self.head_tail_range = red_balls_sorted[-1] - red_balls_sorted[0]

        # 区间分布
        self.zone_distribution = self._calculate_zone_distribution(red_balls_sorted)

    def _calculate_ac_value(self, red_balls):
        """计算AC值"""
        if len(red_balls) != 6:
            return 0
            
        diffs = set()
        for i in range(len(red_balls)):
            for j in range(i+1, len(red_balls)):
                diffs.add(abs(red_balls[i] - red_balls[j]))
        return len(diffs) - 5
    
    def _get_sum_range(self, red_sum):
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
    
    def _calculate_interval_features(self, red_balls):
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
    
    def _calculate_zone_distribution(self, red_balls):
        """计算三区分布"""
        zone1 = sum(1 for x in red_balls if 1 <= x <= 11)
        zone2 = sum(1 for x in red_balls if 12 <= x <= 22)
        zone3 = sum(1 for x in red_balls if 23 <= x <= 33)
        
        return {
            '一区(01-11)': zone1,
            '二区(12-22)': zone2, 
            '三区(23-33)': zone3
        }
    
    def get_numbers_string(self) -> str:
        """获取号码字符串表示"""
        reds = [f"{self.red1:02d}", f"{self.red2:02d}", f"{self.red3:02d}", 
                f"{self.red4:02d}", f"{self.red5:02d}", f"{self.red6:02d}"]
        return f"{' '.join(reds)} + {self.blue:02d}"
    
    def is_valid(self) -> bool:
        """验证数据是否有效"""
        try:
            red_balls = [self.red1, self.red2, self.red3, self.red4, self.red5, self.red6]
            
            if any(ball < 1 or ball > 33 for ball in red_balls):
                return False
            
            if self.blue < 1 or self.blue > 16:
                return False
            
            if len(set(red_balls)) != 6:
                return False
            
            # 注意：原始数据可能不是排序的，所以这里不能强制要求排序
            # 如果需要排序，可以在创建对象后排序
            return True
        except:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'issue': self.issue,
            'draw_date': self.draw_date,
            'red1': self.red1, 'red2': self.red2, 'red3': self.red3,
            'red4': self.red4, 'red5': self.red5, 'red6': self.red6,
            'blue': self.blue,
            'sales': self.sales,
            'pool_money': self.pool_money,
            'year': self.year, 'month': self.month, 'day': self.day,
            'weekday': self.weekday, 'weekday_num': self.weekday_num,
            'quarter': self.quarter, 'season': self.season,
            'month_type': self.month_type, 'is_weekend': self.is_weekend,
            'red_sum': self.red_sum, 'red_avg': self.red_avg,
            'red_odd_count': self.red_odd_count, 'red_even_count': self.red_even_count,
            'red_prime_count': self.red_prime_count, 'red_range': self.red_range,
            'blue_zone': self.blue_zone,
            # 第一阶段特征
            'ac_value': self.ac_value, 'sum_tail': self.sum_tail, 'sum_range': self.sum_range,
            'max_interval': self.max_interval, 'min_interval': self.min_interval,
            'avg_interval': self.avg_interval, 'head_number': self.head_number,
            'tail_number': self.tail_number, 'head_tail_range': self.head_tail_range,
            'big_interval_count': self.big_interval_count, 'interval_pattern': self.interval_pattern,
            'zone_distribution': self.zone_distribution
        }
        
        # 第二阶段特征
        if self.red_omission:
            result['red_omission'] = self.red_omission
        if self.blue_omission is not None:
            result['blue_omission'] = self.blue_omission
        if self.red_heat_status:
            result['red_heat_status'] = self.red_heat_status
        if self.blue_heat_status:
            result['blue_heat_status'] = self.blue_heat_status
        if self.cold_red_balls:
            result['cold_red_balls'] = self.cold_red_balls
        if self.hot_red_balls:
            result['hot_red_balls'] = self.hot_red_balls
        
        # 第三阶段特征
        if self.inherited_reds is not None:
            result['inherited_reds'] = self.inherited_reds
        if self.inherited_blue is not None:
            result['inherited_blue'] = self.inherited_blue
        if self.consecutive_appear is not None:
            result['consecutive_appear'] = self.consecutive_appear
        if self.trend_direction:
            result['trend_direction'] = self.trend_direction
        
        return result
    