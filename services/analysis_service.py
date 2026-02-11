# services/analysis_service.py
"""
分析服务 - 提供统一的统计分析接口
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.db_manager import DatabaseManager
from utils.window_config import WindowConfigManager
from analysis.hot_cold_analyzer import get_hot_cold_analyzer

logger = logging.getLogger('analysis_service')

class AnalysisService:
    """分析服务 - 提供统一的统计分析接口"""
    
    def __init__(self, db_path: str = None):
        self.db_manager = DatabaseManager()

        if db_path is None:
            try:
                from config import config
                db_path = config.paths.DATABASE_PATH
            except ImportError:
                db_path = "double_ball.db"

        self.db = self.db_manager.get_db(db_path)
        
        # 初始化热冷号分析器
        self.hot_cold_analyzer = get_hot_cold_analyzer(self.db)

        # 使用窗口配置管理器获取默认窗口
        try:
            # WindowConfigManager是静态类，直接使用类方法
            self.default_window = WindowConfigManager.get_window_by_name('short_term')
            logger.info(f"Analysis service initialized, default window: {self.default_window}")
        except Exception as e:
            self.default_window = 30
            logger.warning(f"Failed to read window config, using default: {self.default_window}, error: {e}")
    
    def get_basic_statistics(self, window: int = None) -> Dict[str, Any]:
        """获取基本统计信息"""
        if window is None:
            window = self.default_window
        
        try:
            stats = self.db.get_statistics_with_period(window)
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'error': str(e)}
    
    def get_frequency_analysis(self, window: int = None) -> Dict[str, Any]:
        """获取频率分析"""
        if window is None:
            window = self.default_window
        
        try:
            records = self.db.get_recent_records(window)
            
            from collections import Counter
            red_counts = Counter()
            blue_counts = Counter()
            
            for record in records:
                reds = [record.red1, record.red2, record.red3,
                        record.red4, record.red5, record.red6]
                for ball in reds:
                    red_counts[ball] += 1
                
                blue_counts[record.blue] += 1
            
            for ball in range(1, 34):
                if ball not in red_counts:
                    red_counts[ball] = 0
            
            for ball in range(1, 17):
                if ball not in blue_counts:
                    blue_counts[ball] = 0
            
            sorted_reds = sorted(red_counts.items(), key=lambda x: (-x[1], x[0]))
            sorted_blues = sorted(blue_counts.items(), key=lambda x: (-x[1], x[0]))
            
            return {
                'window': window,
                'total_records': len(records),
                'red_frequencies': dict(red_counts),
                'blue_frequencies': dict(blue_counts),
                'sorted_reds': sorted_reds,
                'sorted_blues': sorted_blues,
                'analysis_time': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"频率分析失败: {e}")
            return {'error': str(e)}
    
    def get_hot_cold_numbers(self, window: int = None) -> Dict[str, Any]:
        """获取热冷号分析"""
        try:
            return self.hot_cold_analyzer.analyze(window=window)
        except Exception as e:
            logger.error(f"热冷号分析失败: {e}")
            return {'error': str(e)}
    
    def get_sum_statistics(self, window: int = None) -> Dict[str, Any]:
        """获取和值统计"""
        if window is None:
            window = self.default_window
        
        try:
            records = self.db.get_recent_records(window)
            
            sums = []
            for record in records:
                red_sum = record.red1 + record.red2 + record.red3 + \
                         record.red4 + record.red5 + record.red6
                sums.append({
                    'issue': record.issue,
                    'red_sum': red_sum,
                    'blue': record.blue,
                    'total_sum': red_sum + record.blue
                })
            
            if sums:
                sum_values = [item['red_sum'] for item in sums]
                avg_sum = sum(sum_values) / len(sum_values)
                min_sum = min(sum_values)
                max_sum = max(sum_values)
                
                sum_ranges = {
                    'low': (min_sum, 80),
                    'medium_low': (81, 100),
                    'medium': (101, 120),
                    'medium_high': (121, 140),
                    'high': (141, max_sum)
                }
                
                range_counts = {key: 0 for key in sum_ranges.keys()}
                for value in sum_values:
                    for range_name, (low, high) in sum_ranges.items():
                        if low <= value <= high:
                            range_counts[range_name] += 1
                            break
                
                recent_trend = []
                for i in range(min(5, len(sums))):
                    recent_trend.append(sums[i]['red_sum'])
                
                trend_direction = "稳定"
                if len(recent_trend) >= 2:
                    if recent_trend[0] > recent_trend[-1]:
                        trend_direction = "下降"
                    elif recent_trend[0] < recent_trend[-1]:
                        trend_direction = "上升"
                
                return {
                    'window': window,
                    'total_records': len(records),
                    'sums': sums,
                    'statistics': {
                        'average': avg_sum,
                        'minimum': min_sum,
                        'maximum': max_sum,
                        'range_counts': range_counts,
                        'recent_trend': recent_trend,
                        'trend_direction': trend_direction
                    }
                }
            else:
                return {'error': '没有数据'}
                
        except Exception as e:
            logger.error(f"和值统计失败: {e}")
            return {'error': str(e)}
    
    def get_analysis_summary(self, window: int = None) -> Dict[str, Any]:
        """获取分析摘要"""
        summary = {
            'analysis_time': datetime.now().isoformat(),
            'window_used': window if window else self.default_window
        }
        
        hot_cold = self.get_hot_cold_numbers(window)
        if 'error' not in hot_cold:
            summary['hot_cold_analysis'] = {
                'hot_count': len(hot_cold.get('hot', [])),
                'warm_count': len(hot_cold.get('warm', [])),
                'cold_count': len(hot_cold.get('cold', []))
            }
        
        sum_stats = self.get_sum_statistics(window)
        if 'error' not in sum_stats:
            summary['sum_analysis'] = {
                'average_sum': sum_stats.get('statistics', {}).get('average', 0),
                'trend_direction': sum_stats.get('statistics', {}).get('trend_direction', '未知')
            }
        
        freq_analysis = self.get_frequency_analysis(window)
        if 'error' not in freq_analysis:
            sorted_reds = freq_analysis.get('sorted_reds', [])
            if sorted_reds:
                top_hot = sorted_reds[:3]
                top_cold = sorted_reds[-3:] if len(sorted_reds) >= 3 else sorted_reds
                summary['top_numbers'] = {
                    'hottest': [ball for ball, _ in top_hot],
                    'coldest': [ball for ball, _ in top_cold]
                }
        
        return summary

    def get_individual_ball_trend_analysis(self, window_sizes: List[int] = None) -> Dict[str, Any]:
        """
        获取单个球的出现趋势分析 - 使用hot_cold_analyzer中的功能
        
        按照四个窗口期（30期、50期、100期、全部历史）分析每个球的出现次数和百分比趋势
        """
        try:
            # 首先从hot_cold_analyzer获取红球趋势分析
            ball_trends_result = self.hot_cold_analyzer.analyze_ball_trends(window_sizes=window_sizes)
            
            if 'error' in ball_trends_result:
                return ball_trends_result
            
            # 获取蓝球趋势分析
            blue_ball_trends = self._analyze_blue_ball_trends(window_sizes, ball_trends_result.get('total_records', 0))
            
            # 合并红球和蓝球趋势分析
            trend_analysis = {
                'red_ball_trends': ball_trends_result.get('ball_trends', {}),
                'blue_ball_trends': blue_ball_trends,
                'summary': ball_trends_result.get('summary', {})
            }
            
            return {
                'total_records': ball_trends_result.get('total_records', 0),
                'window_results': ball_trends_result.get('window_results', {}),
                'trend_analysis': trend_analysis,
                'analysis_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"单个球趋势分析失败: {e}")
            return {'error': str(e)}
    
    def _analyze_blue_ball_trends(self, window_sizes: List[int], total_records: int) -> Dict[str, Any]:
        """分析蓝球趋势"""
        if window_sizes is None:
            try:
                # 使用WindowConfigManager类方法获取趋势窗口
                window_sizes = WindowConfigManager.get_trend_windows()
            except Exception:
                window_sizes = [30, 50, 100, None]
        
        blue_trends = {}
        
        # 获取所有记录
        all_records = self.db.get_all_records()
        
        # 分析每个窗口期
        for window_size in window_sizes:
            if window_size is None:
                period_data = all_records
            else:
                effective_period = min(window_size, total_records)
                period_data = all_records[-effective_period:]
            
            if len(period_data) < 10:
                continue
            
            # 统计蓝球出现次数
            from collections import Counter
            blue_counts = Counter()
            
            for record in period_data:
                blue_counts[record.blue] += 1
            
            # 确保所有1-16号蓝球都在计数器中
            for ball in range(1, 17):
                if ball not in blue_counts:
                    blue_counts[ball] = 0
            
            # 计算百分比
            total_games = len(period_data)
            blue_percentages = {}
            for ball, count in blue_counts.items():
                blue_percentages[ball] = count / total_games if total_games > 0 else 0
            
            # 为每个蓝球收集数据
            for ball in range(1, 17):
                if ball not in blue_trends:
                    blue_trends[ball] = {
                        'counts': [],
                        'percentages': [],
                        'window_names': []
                    }
                
                blue_trends[ball]['counts'].append(blue_counts[ball])
                blue_trends[ball]['percentages'].append(blue_percentages[ball])
                blue_trends[ball]['window_names'].append(
                    f"最近{len(period_data)}期" if window_size else "全部历史"
                )
        
        # 判断每个蓝球的趋势
        for ball, data in blue_trends.items():
            if len(data['percentages']) >= 2:
                data['trend'] = self._determine_ball_trend(data['percentages'])
            else:
                data['trend'] = "数据不足"
        
        return blue_trends
    
    def _determine_ball_trend(self, percentages: List[float]) -> str:
        """判断球的出现趋势 - 简化版本，直接从hot_cold_analyzer借用逻辑"""
        if len(percentages) < 2:
            return "数据不足"
        
        # 检查是否递增
        is_increasing = all(percentages[i] <= percentages[i + 1] for i in range(len(percentages) - 1))
        # 检查是否递减
        is_decreasing = all(percentages[i] >= percentages[i + 1] for i in range(len(percentages) - 1))
        
        # 计算最大差异
        max_diff = max(percentages) - min(percentages) if percentages else 0
        
        if is_increasing and max_diff > 0.005:
            return "递增"
        elif is_decreasing and max_diff > 0.005:
            return "递减"
        elif max_diff <= 0.005:
            return "稳定"
        else:
            return "波动"
    
    def get_ball_trend_report(self, ball_type: str = "red", ball_number: int = None) -> str:
        """获取单个球的趋势报告"""
        if ball_type not in ["red", "blue"]:
            return "错误: 球类型必须是'red'或'blue'"
        
        if ball_type == "red" and (ball_number is None or not 1 <= ball_number <= 33):
            return "错误: 红球号码必须在1-33之间"
        elif ball_type == "blue" and (ball_number is None or not 1 <= ball_number <= 16):
            return "错误: 蓝球号码必须在1-16之间"
        
        try:
            trend_analysis = self.get_individual_ball_trend_analysis()
            
            if 'error' in trend_analysis:
                return f"分析失败: {trend_analysis['error']}"
            
            trend_key = f"{ball_type}_ball_trends"
            ball_data = trend_analysis['trend_analysis'].get(trend_key, {}).get(ball_number)
            
            if not ball_data:
                return f"没有找到{ball_type}球{ball_number:02d}的趋势数据"
            
            report_lines = []
            report_lines.append(f"📊 {ball_type.capitalize()}球 {ball_number:02d} 出现趋势分析")
            report_lines.append("=" * 60)
            
            counts = ball_data['counts']
            percentages = ball_data['percentages']
            window_names = ball_data['window_names']
            trend = ball_data.get('trend', '未知')
            
            for i in range(len(window_names)):
                report_lines.append(f"  {window_names[i]}: {counts[i]}次 ({percentages[i]:.1%})")
            
            report_lines.append(f"\n🎯 趋势判断: {trend}")
            
            if trend == "递增":
                report_lines.append("  💡 建议: 该球出现频率正在增加，值得关注")
            elif trend == "递减":
                report_lines.append("  💡 建议: 该球出现频率正在减少，需谨慎")
            elif trend == "稳定":
                report_lines.append("  💡 建议: 该球出现频率稳定，可作为常规选择")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"获取球趋势报告失败: {e}")
            return f"生成报告失败: {str(e)}"

# 全局分析服务实例（单例模式）
_analysis_service = None

def get_analysis_service(db_path=None):
    """获取分析服务实例（单例）"""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService(db_path)
    return _analysis_service