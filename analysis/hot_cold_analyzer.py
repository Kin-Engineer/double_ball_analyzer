# analysis/hot_cold_analyzer.py
"""
统一的热冷号分析器
支持多窗口期热冷号分析和趋势分析
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter
import time

logger = logging.getLogger('hot_cold_analyzer')

class HotColdAnalyzer:
    """统一的热冷号分析器 - 支持多窗口分析"""
    
    def __init__(self, database=None):
        """
        初始化热冷号分析器
        
        Args:
            database: 数据库实例（可选）
        """
        self.db = database
        
        # 缓存最近的分类结果
        self._cached_results = {}
        self._trend_cache = {}
        self._cache_ttl = 300  # 缓存5分钟
        
        # 从统一窗口配置管理器获取窗口配置
        try:
            from utils.window_config import WindowConfigManager
            
            # 获取所有窗口配置
            self.window_config = WindowConfigManager.get_all_windows()
            
            # 获取各个窗口期数（为了兼容性）
            self.short_term_window = WindowConfigManager.get_window_by_name('short_term')
            self.medium_term_window = WindowConfigManager.get_window_by_name('medium_term')
            self.long_term_window = WindowConfigManager.get_window_by_name('long_term')
            
            # 获取趋势窗口配置
            self.trend_window_sizes = WindowConfigManager.get_trend_windows()
            
            # 保持向后兼容：设置一个默认窗口（短期窗口）
            self.window = self.short_term_window
            
            logger.info(f"热冷号分析器初始化，窗口配置: {self.window_config}")
            
        except Exception as e:
            # 使用静态默认值（向后兼容）
            self.window_config = {
                'short_term': 30,  # 保留默认值用于日志显示
                'medium_term': 50,
                'long_term': 100,
                'all_history': None
            }
            # 但实际使用WindowConfigManager的默认值
            try:
                # 尝试重新导入WindowConfigManager
                from utils.window_config import WindowConfigManager
                self.short_term_window = WindowConfigManager.DEFAULT_WINDOWS['short_term']
                self.medium_term_window = WindowConfigManager.DEFAULT_WINDOWS['medium_term']
                self.long_term_window = WindowConfigManager.DEFAULT_WINDOWS['long_term']
                self.window = self.short_term_window
                self.trend_window_sizes = [
                    self.short_term_window,
                    self.medium_term_window,
                    self.long_term_window,
                    None
                ]
            except:
                # 如果WindowConfigManager也失败，使用静态默认值
                self.short_term_window = 30
                self.medium_term_window = 50
                self.long_term_window = 100
                self.window = 30
                self.trend_window_sizes = [30, 50, 100, None]
            logger.warning(f"初始化WindowConfigManager失败，使用备用配置，错误: {e}")

    def analyze(self, records: List = None, window: int = None, force_refresh: bool = False) -> Dict[str, Any]:
        """
        分析热温冷号码（单个窗口期）
        
        按出现次数排名：
        - 前11名：热号
        - 中间11名：温号  
        - 后11名：冷号
        
        Args:
            records: 记录列表，如果为None则从数据库获取
            window: 分析窗口期数，如果为None则使用短期窗口
            force_refresh: 是否强制刷新缓存
            
        Returns:
            分析结果字典
        """
        # 如果未指定窗口，使用短期窗口
        if window is None:
            window = self.short_term_window
        
        # 检查缓存
        cache_key = f"window_{window}"
        if not force_refresh and cache_key in self._cached_results:
            cached_result = self._cached_results[cache_key]
            # 检查缓存是否过期
            if time.time() - cached_result.get('_cache_time', 0) < self._cache_ttl:
                logger.debug(f"使用缓存的热冷号分析结果，窗口: {window}期")
                return cached_result
        
        # 如果未传入records，则从数据库获取
        if records is None and self.db:
            records = self.db.get_recent_records(window)
        
        if not records:
            logger.warning(f"没有获取到数据，窗口: {window}")
            return self._get_empty_result(window)
        
        logger.info(f"分析热冷号，数据量: {len(records)}期，窗口: {window}期")
        
        # 统计红球出现次数
        red_counts = Counter()
        for record in records:
            reds = [record.red1, record.red2, record.red3,
                    record.red4, record.red5, record.red6]
            for ball in reds:
                red_counts[ball] += 1
        
        # 确保所有1-33号球都在计数器中
        for ball in range(1, 34):
            if ball not in red_counts:
                red_counts[ball] = 0
        
        # 按出现次数降序排序，次数相同的按球号升序
        sorted_items = sorted(red_counts.items(), 
                            key=lambda x: (-x[1], x[0]))
        
        # 分类
        hot = [ball for ball, _ in sorted_items[:11]]
        warm = [ball for ball, _ in sorted_items[11:22]]
        cold = [ball for ball, _ in sorted_items[22:33]]
        
        # 创建快速查找字典
        ball_status = {}
        for ball in hot:
            ball_status[ball] = "热"
        for ball in warm:
            ball_status[ball] = "温"
        for ball in cold:
            ball_status[ball] = "冷"
        
        result = {
            'hot': hot,
            'warm': warm, 
            'cold': cold,
            'ball_status': ball_status,  # 添加快速查找字典
            'total_records': len(records),
            'red_counts': dict(red_counts),
            'window': window,
            '_cache_time': time.time()  # 添加缓存时间戳
        }
        
        # 缓存结果
        self._cached_results[cache_key] = result
        
        logger.debug(f"热冷号分析完成: 热号{len(hot)}个，温号{len(warm)}个，冷号{len(cold)}个")
        return result
    
    def analyze_multiple_windows(self, windows: List[int] = None, force_refresh: bool = False) -> Dict[str, Any]:
        """
        分析多个窗口期的热冷号
        
        Args:
            windows: 窗口期列表，如 [30, 50, 100]
            force_refresh: 是否强制刷新缓存
            
        Returns:
            多窗口分析结果
        """
        if windows is None:
            # 使用短、中、长期窗口
            windows = [self.short_term_window, self.medium_term_window, self.long_term_window]
        
        # 检查缓存
        cache_key = f"multi_windows_{str(windows)}"
        if not force_refresh and cache_key in self._cached_results:
            cached_result = self._cached_results[cache_key]
            if time.time() - cached_result.get('_cache_time', 0) < self._cache_ttl:
                logger.debug(f"使用缓存的多窗口热冷号分析结果")
                return cached_result
        
        results = {}
        for window in windows:
            if window is None:
                continue
                
            # 分析单个窗口
            analysis_result = self.analyze(window=window, force_refresh=force_refresh)
            
            # 添加显示名称
            if window == self.short_term_window:
                display_name = f"短期 ({window}期)"
            elif window == self.medium_term_window:
                display_name = f"中期 ({window}期)"
            elif window == self.long_term_window:
                display_name = f"长期 ({window}期)"
            else:
                display_name = f"{window}期"
            
            results[window] = {
                'display_name': display_name,
                'window': window,
                'hot': analysis_result['hot'],
                'warm': analysis_result['warm'],
                'cold': analysis_result['cold'],
                'total_records': analysis_result['total_records']
            }
        
        # 分析跨窗口的一致性
        consistency_analysis = self._analyze_cross_window_consistency(results)
        
        result = {
            'windows': results,
            'consistency': consistency_analysis,
            'analysis_time': time.strftime("%Y-%m-%d %H:%M:%S"),
            '_cache_time': time.time()
        }
        
        # 缓存结果
        self._cached_results[cache_key] = result
        
        logger.info(f"多窗口热冷号分析完成: {len(windows)}个窗口")
        return result
    
    def _analyze_cross_window_consistency(self, window_results: Dict[int, Any]) -> Dict[str, Any]:
        """分析跨窗口的一致性"""
        if len(window_results) < 2:
            return {'message': '至少需要两个窗口进行一致性分析'}
        
        consistency = {
            'consistent_hot': [],      # 在所有窗口都是热号
            'consistent_warm': [],     # 在所有窗口都是温号
            'consistent_cold': [],     # 在所有窗口都是冷号
            'varying': [],             # 在不同窗口状态不同
            'heat_transitions': {},    # 热度变化趋势
        }
        
        # 收集所有号码在不同窗口的状态
        ball_statuses = {}
        for ball in range(1, 34):
            ball_statuses[ball] = []
        
        # 填充每个号码在不同窗口的状态
        for window_data in window_results.values():
            hot_set = set(window_data['hot'])
            warm_set = set(window_data['warm'])
            cold_set = set(window_data['cold'])
            
            for ball in range(1, 34):
                if ball in hot_set:
                    ball_statuses[ball].append('热')
                elif ball in warm_set:
                    ball_statuses[ball].append('温')
                else:
                    ball_statuses[ball].append('冷')
        
        # 分析一致性
        for ball, statuses in ball_statuses.items():
            # 检查是否所有状态相同
            if len(set(statuses)) == 1:
                status = statuses[0]
                if status == '热':
                    consistency['consistent_hot'].append(ball)
                elif status == '温':
                    consistency['consistent_warm'].append(ball)
                else:
                    consistency['consistent_cold'].append(ball)
            else:
                consistency['varying'].append({
                    'ball': ball,
                    'statuses': statuses,
                    'trend': self._determine_heat_trend(statuses)
                })
        
        # 排序
        for key in ['consistent_hot', 'consistent_warm', 'consistent_cold']:
            if consistency[key]:
                consistency[key].sort()
        
        return consistency
    
    def _determine_heat_trend(self, statuses: List[str]) -> str:
        """确定热度变化趋势"""
        if len(statuses) < 2:
            return "数据不足"
        
        # 简化趋势判断
        heat_map = {'冷': 1, '温': 2, '热': 3}
        heat_values = [heat_map.get(status, 0) for status in statuses]
        
        if all(heat_values[i] <= heat_values[i+1] for i in range(len(heat_values)-1)):
            return "升温"
        elif all(heat_values[i] >= heat_values[i+1] for i in range(len(heat_values)-1)):
            return "降温"
        else:
            return "波动"
    
    def analyze_ball_trends(self, window_sizes: List[int] = None, force_refresh: bool = False) -> Dict[str, Any]:
        """
        分析每个球在多个窗口期的出现趋势
        
        Args:
            window_sizes: 窗口期列表，如果为None则使用趋势窗口配置
            force_refresh: 是否强制刷新缓存
            
        Returns:
            每个球的趋势分析结果
        """
        if window_sizes is None:
            window_sizes = self.trend_window_sizes
        
        # 检查缓存
        cache_key = f"trends_{str(window_sizes)}"
        if not force_refresh and cache_key in self._trend_cache:
            cached_result = self._trend_cache[cache_key]
            if time.time() - cached_result.get('_cache_time', 0) < self._cache_ttl:
                logger.debug(f"使用缓存的趋势分析结果")
                return cached_result
        
        try:
            total_records = self.db.get_record_count() if self.db else 0
            
            if total_records == 0:
                return {'error': '没有数据'}
            
            # 分析每个窗口期
            window_results = {}
            for window_size in window_sizes:
                if window_size is None:
                    # 全部历史
                    period_data = self.db.get_all_records() if self.db else []
                    window_name = 'all_history'
                    display_name = '全部历史'
                    period_size = total_records
                else:
                    # 最近N期
                    period_size = min(window_size, total_records)
                    period_data = self.db.get_recent_records(period_size) if self.db and period_size > 0 else []
                    window_name = f'window_{window_size}'
                    display_name = f'最近{period_size}期'
                
                if len(period_data) < 10:
                    logger.warning(f"窗口 {display_name} 数据不足，跳过分析")
                    continue
                
                # 统计红球出现次数
                red_counts = self._count_red_balls(period_data)
                
                # 计算百分比
                total_games = len(period_data)
                red_percentages = {}
                for ball, count in red_counts.items():
                    red_percentages[ball] = count / total_games if total_games > 0 else 0
                
                window_results[window_name] = {
                    'display_name': display_name,
                    'period_size': period_size,
                    'window_size': window_size,
                    'red_counts': dict(red_counts),
                    'red_percentages': red_percentages,
                    'total_games': total_games
                }
            
            # 分析每个球的趋势
            ball_trends = self._analyze_individual_ball_trends(window_results)
            
            result = {
                'total_records': total_records,
                'window_results': window_results,
                'ball_trends': ball_trends,
                'summary': self._generate_ball_trend_summary(ball_trends, window_results),
                '_cache_time': time.time()
            }
            
            # 缓存结果
            self._trend_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            import traceback
            logger.error(f"分析球趋势失败: {e}\n{traceback.format_exc()}")
            return {'error': str(e)}
    
    def _count_red_balls(self, records: List) -> Counter:
        """统计红球出现次数"""
        red_counts = Counter()
        for record in records:
            reds = [record.red1, record.red2, record.red3,
                    record.red4, record.red5, record.red6]
            for ball in reds:
                red_counts[ball] += 1
        
        # 确保所有1-33号球都在计数器中
        for ball in range(1, 34):
            if ball not in red_counts:
                red_counts[ball] = 0
        
        return red_counts

    def _count_red_balls_with_frequency(self, records: List) -> Tuple[Dict[int, int], Dict[int, float]]:
        """统计红球出现次数和频率"""
        from collections import Counter
        red_counts = Counter()
        for record in records:
            reds = [record.red1, record.red2, record.red3,
                    record.red4, record.red5, record.red6]
            for ball in reds:
                red_counts[ball] += 1
        # 确保所有1-33号球都在计数器中
        for ball in range(1, 34):
            if ball not in red_counts:
                red_counts[ball] = 0

        total_games = len(records)
        red_frequencies = {}
        for ball, count in red_counts.items():
            red_frequencies[ball] = count / total_games if total_games > 0 else 0

        return dict(red_counts), red_frequencies

    def _analyze_individual_ball_trends(self, window_results: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """分析每个红球的出现趋势"""
        ball_trends = {}
        
        # 定义窗口期顺序
        window_order = []
        for size in self.trend_window_sizes:
            if size is None:
                window_order.append('all_history')
            else:
                window_order.append(f'window_{size}')
        
        for ball in range(1, 34):
            counts = []
            percentages = []
            window_names = []
            
            for window_name in window_order:
                if window_name in window_results:
                    window_data = window_results[window_name]
                    counts.append(window_data['red_counts'].get(ball, 0))
                    percentages.append(window_data['red_percentages'].get(ball, 0))
                    window_names.append(window_data['display_name'])
            
            if len(counts) >= 2:  # 至少需要两个窗口期
                # 判断趋势
                trend = self._determine_ball_trend(percentages)
                trend_strength = self._calculate_trend_strength(percentages)
                
                ball_trends[ball] = {
                    'counts': counts,
                    'percentages': percentages,
                    'window_names': window_names,
                    'trend': trend,
                    'trend_strength': trend_strength,
                    'current_percentage': percentages[-1] if percentages else 0,
                    'historical_percentage': percentages[0] if percentages else 0
                }
        
        return ball_trends
    
    def _determine_ball_trend(self, percentages: List[float]) -> str:
        """判断球的出现趋势"""
        if len(percentages) < 2:
            return "数据不足"
        
        # 基于百分比判断趋势
        if len(percentages) >= 4:
            # 检查是否递增
            is_increasing = all(percentages[i] <= percentages[i + 1]
                               for i in range(len(percentages) - 1))
            # 检查是否递减
            is_decreasing = all(percentages[i] >= percentages[i + 1]
                               for i in range(len(percentages) - 1))
            
            # 计算最大差异
            max_diff = max(percentages) - min(percentages) if percentages else 0
            
            if is_increasing and max_diff > 0.05:  # 差异大于5%才认为是明显趋势
                return "递增"
            elif is_decreasing and max_diff > 0.05:
                return "递减"
            elif max_diff <= 0.03:  # 差异小于3%认为是稳定
                return "稳定"
            else:
                return "波动"
        else:
            # 只有两个窗口期的情况
            if percentages[0] < percentages[-1] and percentages[-1] - percentages[0] > 0.05:
                return "上升"
            elif percentages[0] > percentages[-1] and percentages[0] - percentages[-1] > 0.05:
                return "下降"
            else:
                return "稳定"
    
    def _calculate_trend_strength(self, percentages: List[float]) -> float:
        """计算趋势强度（0-1之间的值）"""
        if len(percentages) < 2:
            return 0.0
        
        # 计算斜率
        x = list(range(len(percentages)))
        y = percentages
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x_i ** 2 for x_i in x)
        
        if n * sum_x2 - sum_x ** 2 == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # 归一化到0-1，考虑百分比的最大可能变化
        return min(abs(slope) * 20, 1.0)  # 乘以20放大差异
    
    def _generate_ball_trend_summary(self, ball_trends: Dict[int, Dict[str, Any]],
                                   window_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成球的趋势总结"""
        summary = {
            'increasing_reds': [],
            'decreasing_reds': [],
            'stable_reds': [],
            'high_frequency_reds': [],
            'low_frequency_reds': []
        }
        
        # 获取历史数据（全部历史窗口）
        all_history_data = window_results.get('all_history')
        if all_history_data:
            all_history_percentages = all_history_data.get('red_percentages', {})
            
            # 分析每个球的趋势
            for ball, data in ball_trends.items():
                trend = data.get('trend', '')
                current_percentage = data.get('current_percentage', 0)
                historical_percentage = all_history_percentages.get(ball, 0)
                
                if trend == "递增":
                    summary['increasing_reds'].append({
                        'ball': ball,
                        'current_percentage': current_percentage,
                        'historical_percentage': historical_percentage,
                        'trend': trend,
                        'trend_strength': data.get('trend_strength', 0)
                    })
                elif trend == "递减":
                    summary['decreasing_reds'].append({
                        'ball': ball,
                        'current_percentage': current_percentage,
                        'historical_percentage': historical_percentage,
                        'trend': trend,
                        'trend_strength': data.get('trend_strength', 0)
                    })
                elif trend == "稳定":
                    summary['stable_reds'].append({
                        'ball': ball,
                        'current_percentage': current_percentage,
                        'historical_percentage': historical_percentage,
                        'trend': trend,
                        'trend_strength': data.get('trend_strength', 0)
                    })
                
                # 判断高频/低频（基于历史出现频率）
                if historical_percentage > 0.25:  # 历史出现频率大于25%
                    summary['high_frequency_reds'].append({
                        'ball': ball,
                        'percentage': historical_percentage
                    })
                elif historical_percentage < 0.10:  # 历史出现频率小于10%
                    summary['low_frequency_reds'].append({
                        'ball': ball,
                        'percentage': historical_percentage
                    })
        
        # 排序
        for key in ['increasing_reds', 'decreasing_reds', 'high_frequency_reds', 'low_frequency_reds']:
            if summary[key]:
                if key in ['high_frequency_reds', 'low_frequency_reds']:
                    summary[key].sort(key=lambda x: x.get('percentage', 0), reverse=True)
                else:
                    summary[key].sort(key=lambda x: x.get('trend_strength', 0), reverse=True)
        
        return summary
    
    # 保留原有的辅助方法，保持向后兼容
    def get_ball_status(self, ball: int, categories: Dict[str, List[int]] = None) -> str:
        """获取单个球的状态（短期窗口）"""
        if not 1 <= ball <= 33:
            return "无效"
        
        if categories is None:
            categories = self.analyze()  # 默认使用短期窗口
        
        # 使用快速查找字典提高效率
        if 'ball_status' in categories:
            return categories['ball_status'].get(ball, "冷")
        
        # 向后兼容
        if ball in categories['hot']:
            return "热"
        elif ball in categories['warm']:
            return "温"
        else:
            return "冷"
    
    def get_hot_numbers(self, window: int = None, top_n: int = None) -> List[int]:
        """获取热号列表（单个窗口）"""
        categories = self.analyze(window=window)
        hot_numbers = categories['hot']
        
        if top_n is not None and top_n < len(hot_numbers):
            return hot_numbers[:top_n]
        
        return hot_numbers
    
    def get_cold_numbers(self, window: int = None, top_n: int = None) -> List[int]:
        """获取冷号列表（单个窗口）"""
        categories = self.analyze(window=window)
        cold_numbers = categories['cold']
        
        if top_n is not None and top_n < len(cold_numbers):
            return cold_numbers[:top_n]
        
        return cold_numbers
    
    def get_warm_numbers(self, window: int = None, top_n: int = None) -> List[int]:
        """获取温号列表（单个窗口）"""
        categories = self.analyze(window=window)
        warm_numbers = categories['warm']
        
        if top_n is not None and top_n < len(warm_numbers):
            return warm_numbers[:top_n]
        
        return warm_numbers
    
    def clear_cache(self, window: int = None):
        """清除缓存"""
        if window is None:
            self._cached_results.clear()
            self._trend_cache.clear()
            logger.debug("清除所有热冷号分析缓存")
        else:
            cache_key = f"window_{window}"
            if cache_key in self._cached_results:
                del self._cached_results[cache_key]
                logger.debug(f"清除窗口 {window} 的热冷号分析缓存")
    
    def _get_empty_result(self, window: int) -> Dict[str, Any]:
        """获取空结果"""
        return {
            'hot': [],
            'warm': [], 
            'cold': [],
            'ball_status': {},
            'total_records': 0,
            'red_counts': {},
            'window': window,
            '_cache_time': time.time()
        }

# 全局热冷号分析器实例（单例模式）
_hot_cold_analyzer = None

def get_hot_cold_analyzer(db=None):
    """获取热冷号分析器实例（单例）"""
    global _hot_cold_analyzer
    if _hot_cold_analyzer is None:
        _hot_cold_analyzer = HotColdAnalyzer(db)
    return _hot_cold_analyzer