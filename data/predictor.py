# data/predictor.py
"""
预测算法模块，使用统一的热冷号分析器
"""

import logging
import random
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Union
from collections import Counter
from datetime import datetime
from utils.window_config import WindowConfigManager

from .models import DoubleBallRecord
from .database import DoubleBallDatabase
from utils.data_utils import generate_red_balls, is_valid_red_combination

# 导入统一的热冷号分析器
try:
    from analysis.hot_cold_analyzer import get_hot_cold_analyzer

    HOT_COLD_ANALYZER_AVAILABLE = True
except ImportError as e:
    HOT_COLD_ANALYZER_AVAILABLE = False
    print(f"警告: 未找到统一的热冷号分析器。导入错误: {e}")

logger = logging.getLogger('predictor')


class BasePredictor:
    """基础预测器"""

    def __init__(self, database: DoubleBallDatabase):
        self.db = database

        # 从配置读取默认窗口
        try:
            from config import config
            self.default_window = WindowConfigManager.get_window_by_name('short_term')
        except (ImportError, AttributeError):
            self.default_window = 30

        # 初始化缓存属性（确保它们存在）
        self._cached_categories = None
        self._cached_window = None
        self._cache_time = None

        # 初始化统一的热冷号分析器
        if HOT_COLD_ANALYZER_AVAILABLE:
            self.hot_cold_analyzer = get_hot_cold_analyzer(database)
            logger.info(f"预测器已使用统一热冷号分析器，默认窗口: {self.default_window}期")
        else:
            self.hot_cold_analyzer = None
            logger.warning("预测器使用旧版热冷号算法")

    def get_number_categories(self, window: int = None) -> Dict[str, List[int]]:
        """获取热号、温号、冷号（简化版本，不带复杂缓存）"""
        # 使用默认窗口
        if window is None:
            window = self.default_window

        # 如果统一分析器可用，使用它
        if self.hot_cold_analyzer:
            result = self.hot_cold_analyzer.analyze(window=window)
            return {
                'hot': result['hot'],
                'warm': result['warm'],
                'cold': result['cold']
            }

        # 回退到旧算法
        logger.warning("使用旧版热冷号算法")
        recent_records = self.db.get_recent_records(window)
        if not recent_records:
            return {'hot': [], 'warm': [], 'cold': []}

        # 旧算法：统计出现次数
        red_counts = Counter()
        for record in recent_records:
            reds = [record.red1, record.red2, record.red3,
                    record.red4, record.red5, record.red6]
            for ball in reds:
                red_counts[ball] += 1

        # 确保所有1-33号球都在计数器中
        for ball in range(1, 34):
            if ball not in red_counts:
                red_counts[ball] = 0

        # 按出现次数排序
        sorted_items = red_counts.most_common()

        # 前11名为热号，中间11名为温号，后11名为冷号
        hot = [ball for ball, _ in sorted_items[:11]]
        warm = [ball for ball, _ in sorted_items[11:22]]
        cold = [ball for ball, _ in sorted_items[22:]]

        return {'hot': hot, 'warm': warm, 'cold': cold}

    def get_hot_numbers(self, window: int = None, top_n: int = 11) -> List[int]:
        """获取热号"""
        categories = self.get_number_categories(window)
        hot_numbers = categories['hot'][:top_n] if top_n <= len(categories['hot']) else categories['hot']
        return hot_numbers

    def get_warm_numbers(self, window: int = None) -> List[int]:
        """获取温号"""
        categories = self.get_number_categories(window)
        return categories['warm']

    def get_cold_numbers(self, window: int = None, top_n: int = 11) -> List[int]:
        """获取冷号"""
        categories = self.get_number_categories(window)
        cold_numbers = categories['cold'][:top_n] if top_n <= len(categories['cold']) else categories['cold']
        return cold_numbers

    def get_ball_status(self, ball: int, window: int = None) -> str:
        """获取单个球的状态（热、温、冷）"""
        categories = self.get_number_categories(window)
        if ball in categories['hot']:
            return "热"
        elif ball in categories['warm']:
            return "温"
        else:
            return "冷"

    def predict_by_hot_cold(self, window: int = None) -> Dict[str, Any]:
        """基于热冷号预测（使用统一的热冷号分析器）"""
        if window is None:
            window = self.default_window

        # 获取热温冷号分类
        categories = self.get_number_categories(window)
        hot_reds = categories['hot']
        warm_reds = categories['warm']
        cold_reds = categories['cold']

        logger.debug(f"预测使用分类 - 热号: {len(hot_reds)}个, 温号: {len(warm_reds)}个, 冷号: {len(cold_reds)}个")

        # 组合预测：按照合理比例选择（比如：3热 + 2温 + 1冷）
        predicted_count_hot = min(3, len(hot_reds))
        hot_selection = random.sample(hot_reds, predicted_count_hot) if hot_reds else []

        predicted_count_warm = min(2, len(warm_reds))
        warm_selection = random.sample(warm_reds, predicted_count_warm) if warm_reds else []

        predicted_count_cold = min(1, len(cold_reds))
        cold_selection = random.sample(cold_reds, predicted_count_cold) if cold_reds else []

        # 合并并确保6个号码
        all_selected = hot_selection + warm_selection + cold_selection

        if len(all_selected) < 6:
            remaining = list(set(range(1, 34)) - set(all_selected))
            additional = random.sample(remaining, 6 - len(all_selected))
            all_selected.extend(additional)
        elif len(all_selected) > 6:
            all_selected = all_selected[:6]

        predicted_reds = sorted(all_selected)

        # 蓝球预测
        recent_data = self.db.get_recent_records(20)
        blue_counts = Counter(record.blue for record in recent_data)
        candidate_blues = [num for num in range(1, 17) if 1 <= blue_counts.get(num, 0) <= 2]
        if not candidate_blues:
            candidate_blues = [num for num in range(1, 17) if blue_counts.get(num, 0) <= 3]
        predicted_blue = random.choice(candidate_blues) if candidate_blues else random.randint(1, 16)

        # 计算置信度
        hot_count = len(set(predicted_reds) & set(hot_reds))
        cold_count = len(set(predicted_reds) & set(cold_reds))
        base_confidence = 60 + (hot_count * 5) - (cold_count * 3)

        # 获取每个红球的状态
        red_ball_status = {ball: self.get_ball_status(ball) for ball in predicted_reds}

        return {
            'red_balls': predicted_reds,
            'blue_ball': predicted_blue,
            'red_ball_status': red_ball_status,
            'confidence': min(base_confidence + random.uniform(-5, 5), 85),
            'strategy': '热冷号分析',
            'window': window
        }

    def predict_random(self) -> Dict[str, Any]:
        """随机预测（保持不变）"""
        reds = sorted(random.sample(range(1, 34), 6))
        blue = random.randint(1, 16)

        return {
            'red_balls': reds,
            'blue_ball': blue,
            'confidence': random.uniform(20, 40),
            'strategy': '随机策略'
        }

    def predict_mixed_strategy(self) -> Dict[str, Any]:
        """混合策略预测（保持不变）"""
        strategies = [self.predict_by_hot_cold, self.predict_random]
        weights = [0.7, 0.3]  # 热冷号策略权重70%，随机策略30%

        selected_strategy = random.choices(strategies, weights=weights)[0]
        return selected_strategy()


class EnhancedPredictor(BasePredictor):
    """增强预测器，集成概率分析"""

    def __init__(self, database):
        # 必须调用父类的初始化
        super().__init__(database)

        # 可以在这里初始化概率分析器
        try:
            from analysis.probability_analyzer import ProbabilityAnalyzer
            self.probability_analyzer = ProbabilityAnalyzer(database)
        except ImportError:
            self.probability_analyzer = None
            logger.warning("概率分析器未找到，将使用基础预测")

    def predict_6_plus_1(self) -> Dict[str, Any]:
        """6+1基础预测"""
        return self.predict_by_hot_cold()

    def predict_7_plus_1(self) -> Dict[str, Any]:
        """7+1预测"""
        base_prediction = self.predict_by_hot_cold()
        reds = base_prediction['red_balls'].copy()  # 注意：复制一份，避免修改原列表

        # 确保有6个红球
        if len(reds) != 6:
            reds = sorted(random.sample(range(1, 34), 6))

        # 从热门号码中补充一个
        hot_reds = self.get_hot_numbers(self.default_window, 15)
        additional_candidates = [x for x in hot_reds if x not in reds]

        if additional_candidates:
            additional = random.choice(additional_candidates)
        else:
            # 从剩余号码中随机选择一个
            remaining = [x for x in range(1, 34) if x not in reds]
            additional = random.choice(remaining) if remaining else random.randint(1, 33)

        reds.append(additional)
        reds.sort()

        # 调整置信度
        confidence = base_prediction['confidence'] * 0.9  # 7+1置信度稍低

        # 获取每个红球的状态（包括新增的）
        red_ball_status = {ball: self.get_ball_status(ball) for ball in reds}

        return {
            'red_balls': reds,
            'blue_ball': base_prediction['blue_ball'],
            'red_ball_status': red_ball_status, # 添加状态
            'confidence': confidence,
            'strategy': '7+1增强',
            'num_reds': 7  # 明确标记红球数量
        }

    def predict_8_plus_1(self) -> Dict[str, Any]:
        """8+1预测"""
        # 获取6+1基础预测
        base_prediction = self.predict_by_hot_cold()
        reds = base_prediction['red_balls'].copy()  # 修复：添加这一行

        # 确保有6个红球
        if len(reds) != 6:
            reds = sorted(random.sample(range(1, 34), 6))

        # 补充两个号码
        hot_reds = self.get_hot_numbers(self.default_window, 20)
        additional_candidates = [x for x in hot_reds if x not in reds]

        # 第一个从热门中选
        if additional_candidates:
            additional1 = random.choice(additional_candidates)
            reds.append(additional1)
            additional_candidates = [x for x in additional_candidates if x != additional1]
        else:
            remaining = [x for x in range(1, 34) if x not in reds]
            additional1 = random.choice(remaining) if remaining else random.randint(1, 33)
            reds.append(additional1)

        # 第二个从剩余中随机选
        remaining_all = [x for x in range(1, 34) if x not in reds]
        if remaining_all:
            additional2 = random.choice(remaining_all)
        else:
            additional2 = random.randint(1, 33)
            while additional2 in reds:
                additional2 = random.randint(1, 33)

        reds.append(additional2)
        reds.sort()

        # 调整置信度
        confidence = base_prediction['confidence'] * 0.8  # 8+1置信度更低

        # 获取每个红球的状态
        red_ball_status = {ball: self.get_ball_status(ball) for ball in reds}

        return {
            'red_balls': reds,
            'blue_ball': base_prediction['blue_ball'],
            'red_ball_status': red_ball_status,
            'confidence': confidence,
            'strategy': '8+1高级',
            'num_reds': 8  # 明确标记红球数量
        }

    def predict_all_combinations(self) -> Dict[str, Any]:
        """预测所有组合"""
        try:
            pred_6 = self.predict_6_plus_1()
            pred_7 = self.predict_7_plus_1()
            pred_8 = self.predict_8_plus_1()

            result = {
                '6_plus_1': pred_6,
                '7_plus_1': pred_7,
                '8_plus_1': pred_8,
                'timestamp': datetime.now().isoformat()
            }

            # 推荐最佳组合
            confidences = {
                '6+1': pred_6.get('confidence', 0),
                '7+1': pred_7.get('confidence', 0),
                '8+1': pred_8.get('confidence', 0)
            }
            best_combo = max(confidences.items(), key=lambda x: x[1])

            result['recommended_combination'] = best_combo[0]
            result['recommended_confidence'] = best_combo[1]

            return result
        except Exception as e:
            logger.error(f"预测所有组合失败: {e}", exc_info=True)
            # 返回一个安全的默认结构
            return {
                '6_plus_1': {'red_balls': [], 'blue_ball': 0, 'confidence': 0, 'strategy': '默认'},
                '7_plus_1': {'red_balls': [], 'blue_ball': 0, 'confidence': 0, 'strategy': '默认'},
                '8_plus_1': {'red_balls': [], 'blue_ball': 0, 'confidence': 0, 'strategy': '默认'},
                'timestamp': datetime.now().isoformat(),
                'recommended_combination': '6+1',
                'recommended_confidence': 0
            }

    def predict_with_probability(self) -> Dict[str, Any]:
        """基于概率分析的预测"""
        if not self.probability_analyzer:
            return self.predict_all_combinations()

        try:
            # 获取最新一期数据
            latest_record = None
            if hasattr(self.db, 'get_latest_record'):
                latest_record = self.db.get_latest_record()
            else:
                recent_records = self.db.get_recent_records(1)
                if recent_records:
                    latest_record = recent_records[0]

            if latest_record:
                # 获取概率分析
                probability_analysis = self.probability_analyzer.analyze_current_period_probability(latest_record)

                # 直接返回基础预测，不进行调整
                base_prediction = self.predict_all_combinations()

                # 添加概率分析信息
                base_prediction['probability_analysis'] = probability_analysis

                return base_prediction
            else:
                return self.predict_all_combinations()

        except Exception as e:
            logger.error(f"概率预测失败: {e}", exc_info=True)
            return self.predict_all_combinations()


# 全局预测器实例
predictor = None

def get_predictor(db_path=None):
    """获取预测器实例"""
    global predictor
    if predictor is None:
        db = DoubleBallDatabase(db_path)
        predictor = EnhancedPredictor(db)
    return predictor