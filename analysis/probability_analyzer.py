# analysis/probability_analyzer.py
"""
概率分析器 - 多窗口期实际重复统计
按照共识方案：只显示百分比，不显示次数
"""
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from collections import Counter
from datetime import datetime
from utils.window_config import WindowConfigManager

from data.database import DoubleBallDatabase
from data.models import DoubleBallRecord

logger = logging.getLogger('probability_analyzer')

class ProbabilityAnalyzer:
    """概率分析器 - 使用系统配置的窗口期进行实际重复统计"""
    
    def __init__(self, db: DoubleBallDatabase):
        self.db = db
        # 从系统配置获取窗口期设置
        self.window_config = self._get_window_config()
        logger.debug(f"概率分析器初始化完成，窗口配置: {self.window_config}")
    
    def _get_window_config(self) -> Dict[str, Optional[int]]:
        """获取窗口配置（基于现有config.py配置）"""
        try:
            # 延迟导入，避免循环依赖
            from config import config
            
            return {
                'short_term': WindowConfigManager.get_window_by_name('short_term'),      # 默认30期
                'medium_term': WindowConfigManager.get_window_by_name('short_term'),  # 默认50期
                'long_term': WindowConfigManager.get_window_by_name('short_term'),          # 默认100期
                'all_history': None  # 全部历史
            }
        except ImportError as e:
            logger.warning(f"无法导入config模块，使用默认窗口配置: {e}")
            # 回退到默认值（与config.py默认值一致）
            return {
                'short_term': 30,
                'medium_term': 50,
                'long_term': 100,
                'all_history': None
            }
    
    def analyze_current_period_probability(
        self, 
        current_record: Optional[DoubleBallRecord] = None,
        window_group: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        多窗口期概率分析 - 基于实际重复次数
        
        按照共识方案：只返回百分比，不返回次数
        """
        # 验证输入
        if not current_record:
            logger.warning("没有提供当前期数据")
            return self._get_empty_result()
        
        # 获取所有历史记录
        all_records = self.db.get_all_records()
        total_records = len(all_records)
        
        if total_records < 2:
            logger.warning(f"历史记录不足: {total_records} 条，无法进行概率分析")
            return self._get_empty_result(current_record)
        
        logger.info(f"开始概率分析: 当前期 {current_record.issue}, 总记录 {total_records} 条")
        
        # 确定使用的窗口组
        if window_group is None:
            window_group = ['short_term', 'medium_term', 'long_term', 'all_history']
        
        # 为每个窗口期计算分析
        window_results = {}
        for window_name in window_group:
            if window_name not in self.window_config:
                logger.warning(f"未知窗口类型: {window_name}，跳过")
                continue
            
            window_result = self._analyze_single_window(
                window_name, current_record, all_records, total_records
            )
            
            if window_result:
                window_results[window_name] = window_result
        
        # 综合所有窗口期结果
        result = self._combine_window_results(
            window_results, current_record, total_records
        )
        
        logger.info(f"概率分析完成，分析了 {len(window_results)} 个窗口期")
        return result
    
    def _analyze_single_window(
        self,
        window_name: str,
        current_record: DoubleBallRecord,
        all_records: List[DoubleBallRecord],
        total_records: int
    ) -> Optional[Dict[str, Any]]:
        """分析单个窗口期"""
        period_limit = self.window_config[window_name]
        
        # 获取该窗口期的数据
        if window_name == 'all_history' or period_limit is None:
            period_data = all_records
            effective_period = total_records
            logger.debug(f"窗口 '{window_name}': 使用全部历史数据 ({effective_period} 条记录)")
        else:
            # 确保不超过总记录数
            effective_period = min(period_limit, total_records)
            period_data = all_records[-effective_period:]
            logger.debug(f"窗口 '{window_name}'(配置{period_limit}期): 使用最近{effective_period}期数据")
        
        # 确保有足够的数据进行分析
        if len(period_data) < 2:
            logger.warning(f"窗口 '{window_name}' 数据不足 ({len(period_data)} 条)，跳过")
            return None
        
        # 计算该窗口期的实际重复统计
        return self._calculate_window_repeat_stats(
            window_name, current_record, period_data
        )
    
    def _calculate_window_repeat_stats(
        self,
        window_name: str,
        current_record: DoubleBallRecord,
        period_data: List[DoubleBallRecord]
    ) -> Dict[str, Any]:
        """
        计算单个窗口期的实际重复统计
        按照共识方案：只返回百分比，不返回次数
        """
        current_reds = [current_record.red1, current_record.red2, current_record.red3,
                        current_record.red4, current_record.red5, current_record.red6]
        current_blue = current_record.blue
        
        # 初始化统计
        repeat_counts = []  # 每期的重号数量 (0-6)
        blue_repeat_counts = []  # 每期蓝球是否重复 (0或1)
        
        logger.debug(f"计算窗口 '{window_name}' 的重复统计，共 {len(period_data)} 条记录")
        
        # 统计历史实际重复模式
        for i in range(len(period_data) - 1):
            record = period_data[i]
            next_record = period_data[i + 1]

            record_reds = [record.red1, record.red2, record.red3,
                           record.red4, record.red5, record.red6]
            next_reds = [next_record.red1, next_record.red2, next_record.red3,
                         next_record.red4, next_record.red5, next_record.red6]
            
            # 实际重复的红球
            repeat_reds = set(record_reds) & set(next_reds)
            repeat_count = len(repeat_reds)
            repeat_counts.append(repeat_count)
            
            # 实际重复的蓝球
            blue_repeat = 1 if record.blue == next_record.blue else 0
            blue_repeat_counts.append(blue_repeat)
        
        total_pairs = len(period_data) - 1
        
        # 计算重复数量的概率分布（按照共识方案：只返回百分比）
        repeat_prob_distribution = {}
        if total_pairs > 0:
            count_distribution = Counter(repeat_counts)
            for count in range(0, 7):  # 确保0到6都有值
                freq = count_distribution.get(count, 0)
                repeat_prob_distribution[count] = freq / total_pairs  # 直接计算百分比
        
        # 计算蓝球重复概率（百分比）
        blue_repeat_probability = 0.0
        if total_pairs > 0:
            blue_repeat_probability = sum(blue_repeat_counts) / total_pairs
        
        # 计算当前期号的重复预测（只返回百分比）
        current_predictions = self._calculate_current_predictions(
            current_record, period_data
        )
        
        return {
            'window_name': window_name,
            'period_limit': self.window_config[window_name],
            'effective_periods': len(period_data),
            'total_pairs': total_pairs,
            
            # 概率分布（按照共识方案：只返回百分比）
            'repeat_distribution': repeat_prob_distribution,  # 百分比形式
            'blue_repeat_probability': blue_repeat_probability,  # 百分比形式
            
            # 当前期预测
            'current_predictions': current_predictions,
            
            # 调试信息
            'statistics_based_on_actual': True,
            'similarity_filter_applied': False,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def _calculate_current_predictions(
        self,
        current_record: DoubleBallRecord,
        period_data: List[DoubleBallRecord]
    ) -> Dict[str, Any]:
        """计算当前期号的重复预测（只返回百分比）"""
        current_reds = [current_record.red1, current_record.red2, current_record.red3,
                        current_record.red4, current_record.red5, current_record.red6]
        
        # 统计历史中与当前期相似的情况
        similar_repeat_counts = []
        similar_blue_repeats = []
        red_repeat_predictions = {red: 0 for red in current_reds}
        
        total_comparisons = 0
        
        for i in range(len(period_data) - 1):
            record = period_data[i]
            next_record = period_data[i + 1]
            
            record_reds = [record.red1, record.red2, record.red3,
                           record.red4, record.red5, record.red6]
            
            # 比较当前期与历史期
            common_reds = set(current_reds) & set(record_reds)
            
            if len(common_reds) > 0:  # 只要有共同号码就考虑
                total_comparisons += 1
                
                next_reds = [next_record.red1, next_record.red2, next_record.red3,
                             next_record.red4, next_record.red5, next_record.red6]
                
                # 记录重复情况
                repeat_reds = set(record_reds) & set(next_reds)
                repeat_count = len(repeat_reds)
                similar_repeat_counts.append(repeat_count)
                
                # 蓝球重复
                blue_repeat = 1 if record.blue == next_record.blue else 0
                similar_blue_repeats.append(blue_repeat)
                
                # 预测每个红球的重复
                for red in current_reds:
                    if red in repeat_reds:
                        red_repeat_predictions[red] += 1
        
        # 计算预测概率（百分比）
        if total_comparisons > 0:
            # 平均重复数量
            avg_repeat_count = sum(similar_repeat_counts) / total_comparisons if similar_repeat_counts else 0
            
            # 红球重复概率（百分比）
            red_probabilities = {
                red: count / total_comparisons 
                for red, count in red_repeat_predictions.items()
            }
            
            # 蓝球重复概率（百分比）
            blue_repeat_prob = sum(similar_blue_repeats) / total_comparisons if similar_blue_repeats else 0
        else:
            avg_repeat_count = 0
            red_probabilities = {red: 0 for red in current_reds}
            blue_repeat_prob = 0
        
        return {
            'based_on_comparisons': total_comparisons,
            'avg_repeat_count': avg_repeat_count,
            'red_probabilities': red_probabilities,
            'blue_repeat_probability': blue_repeat_prob
        }
    
    def _combine_window_results(
        self,
        window_results: Dict[str, Dict[str, Any]],
        current_record: DoubleBallRecord,
        total_records: int
    ) -> Dict[str, Any]:
        """综合所有窗口期结果"""
        current_reds = [current_record.red1, current_record.red2, current_record.red3,
                        current_record.red4, current_record.red5, current_record.red6]
        current_blue = current_record.blue
        
        # 收集趋势分析数据
        trends_analysis = self._analyze_repeat_trends(window_results)
        
        return {
            'current_period': current_record.issue,
            'current_reds': current_reds,
            'current_blue': current_blue,
            'total_records': total_records,
            
            # 多窗口期分析结果
            'window_analysis': window_results,
            
            # 趋势分析结果
            'trends_analysis': trends_analysis,
            
            # 综合预测（基于长期窗口）
            'comprehensive_predictions': self._get_comprehensive_predictions(window_results),
            
            # 调试信息
            'analysis_method': 'multi_window_actual_repeat',
            'similarity_filter_applied': False,
            'windows_analyzed': list(window_results.keys()),
            'analysis_time': datetime.now().isoformat(),
            'window_config_used': self.window_config
        }
    
    def _analyze_repeat_trends(self, window_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """分析重号分布的跨窗口趋势"""
        trends = {}
        
        # 定义窗口期顺序
        window_order = ['short_term', 'medium_term', 'long_term', 'all_history']
        
        # 收集每个重复数量在四个窗口期的概率
        for repeat_count in range(0, 7):
            count_trends = {}
            
            for window_name in window_order:
                if window_name in window_results:
                    window_data = window_results[window_name]
                    repeat_dist = window_data.get('repeat_distribution', {})
                    prob = repeat_dist.get(repeat_count, 0.0)
                    count_trends[window_name] = prob
            
            if count_trends:
                # 判断趋势
                trend_type = self._determine_trend_type(count_trends, window_order)
                trends[repeat_count] = {
                    'probabilities': count_trends,
                    'trend': trend_type
                }
        
        # 找出最可能的重号数量（基于长期窗口）
        most_likely = 0
        max_prob = 0.0
        
        if 'long_term' in window_results:
            long_term_dist = window_results['long_term'].get('repeat_distribution', {})
            for count, prob in long_term_dist.items():
                if prob > max_prob:
                    max_prob = prob
                    most_likely = count
        
        return {
            'repeat_trends': trends,
            'most_likely_repeat_count': most_likely,
            'trend_summary': self._generate_trend_summary(trends, most_likely)
        }
    
    def _determine_trend_type(self, probabilities: Dict[str, float], window_order: List[str]) -> str:
        """判断趋势类型"""
        if len(probabilities) < 2:
            return "数据不足"
        
        values = [probabilities.get(window, 0.0) for window in window_order if window in probabilities]
        
        # 检查是否递增
        is_increasing = all(values[i] <= values[i+1] for i in range(len(values)-1))
        # 检查是否递减
        is_decreasing = all(values[i] >= values[i+1] for i in range(len(values)-1))
        
        # 计算最大差异
        max_diff = max(values) - min(values) if values else 0
        
        if len(values) == 4:
            if is_increasing and max_diff > 0.02:  # 差异大于2%才认为是明显趋势
                return "递增"
            elif is_decreasing and max_diff > 0.02:
                return "递减"
            elif max_diff <= 0.02:
                return "稳定"
            else:
                return "波动"
        else:
            return "数据不完整"
    
    def _generate_trend_summary(self, trends: Dict[int, Dict[str, Any]], most_likely: int) -> str:
        """生成趋势总结文本"""
        if not trends:
            return "趋势分析数据不足"
        
        summary_lines = []
        
        # 添加最可能重号数量
        summary_lines.append(f"最可能重复数量: {most_likely}个红球")
        
        # 分析每个重号数量的趋势
        for count in range(0, 7):
            if count in trends:
                trend_data = trends[count]
                probabilities = trend_data['probabilities']
                trend = trend_data['trend']
                
                # 只显示有意义的趋势
                if probabilities.get('long_term', 0) > 0.01 or trend != "稳定":  # 概率大于1%或趋势明显
                    probs_str = " → ".join([f"{probabilities.get(w, 0):.1%}" 
                                           for w in ['short_term', 'medium_term', 'long_term', 'all_history'] 
                                           if w in probabilities])
                    summary_lines.append(f"重复{count}个: {probs_str} ({trend})")
        
        return "\n".join(summary_lines)
    
    def _get_comprehensive_predictions(self, window_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """获取综合预测结果"""
        # 优先使用长期窗口
        if 'long_term' in window_results:
            long_term = window_results['long_term']
            return {
                'repeat_distribution': long_term.get('repeat_distribution', {}),
                'blue_repeat_probability': long_term.get('blue_repeat_probability', 0),
                'window_source': 'long_term',
                'window_display_name': '长期窗口'
            }
        elif window_results:
            # 使用第一个可用的窗口
            first_window = next(iter(window_results.values()))
            first_window_name = next(iter(window_results.keys()))
            return {
                'repeat_distribution': first_window.get('repeat_distribution', {}),
                'blue_repeat_probability': first_window.get('blue_repeat_probability', 0),
                'window_source': first_window_name,
                'window_display_name': self._get_window_display_name(first_window_name)
            }
        
        return {}
    
    def _get_window_display_name(self, window_name: str) -> str:
        """获取窗口的显示名称"""
        names = {
            'short_term': '短期',
            'medium_term': '中期',
            'long_term': '长期',
            'all_history': '全部历史'
        }
        return names.get(window_name, window_name)
    
    def _get_empty_result(
        self, 
        current_record: Optional[DoubleBallRecord] = None
    ) -> Dict[str, Any]:
        """获取空结果"""
        result = {
            'error': '数据不足或无当前期数据',
            'window_analysis': {},
            'analysis_time': datetime.now().isoformat()
        }
        
        if current_record:
            result.update({
                'current_period': current_record.issue,
                'current_reds': [current_record.red1, current_record.red2, current_record.red3,
                                current_record.red4, current_record.red5, current_record.red6],
                'current_blue': current_record.blue
            })
        
        return result
    
    def generate_probability_report(self, analysis_result: Dict[str, Any]) -> str:
        """生成概率分析报告 - 支持多窗口期趋势分析"""
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("双色球概率分析报告 (多窗口期趋势分析)")
        report_lines.append("=" * 60)
        report_lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"当前期号: {analysis_result.get('current_period', '未知')}")
        report_lines.append(f"当前红球: {analysis_result.get('current_reds', [])}")
        report_lines.append(f"当前蓝球: {analysis_result.get('current_blue', 0)}")
        report_lines.append(f"总记录数: {analysis_result.get('total_records', 0)}")
        
        # 多窗口期分析结果
        window_analysis = analysis_result.get('window_analysis', {})
        if window_analysis:
            report_lines.append("\n" + "=" * 60)
            report_lines.append("多窗口期重号概率分布")
            report_lines.append("=" * 60)
            
            # 显示每个窗口期的重号分布
            window_display_order = [
                ('short_term', '📱 短期窗口'),
                ('medium_term', '📊 中期窗口'), 
                ('long_term', '📈 长期窗口'),
                ('all_history', '📚 全部历史')
            ]
            
            for window_key, window_title in window_display_order:
                if window_key in window_analysis:
                    window_data = window_analysis[window_key]
                    period_limit = window_data.get('period_limit', '全部')
                    effective_periods = window_data.get('effective_periods', 0)
                    total_pairs = window_data.get('total_pairs', 0)
                    
                    # 获取窗口期描述
                    window_desc = {
                        'short_term': f'最近{period_limit}期' if period_limit else '全部历史',
                        'medium_term': f'最近{period_limit}期' if period_limit else '全部历史',
                        'long_term': f'最近{period_limit}期' if period_limit else '全部历史',
                        'all_history': '全部历史数据'
                    }.get(window_key, '')
                    
                    report_lines.append(f"\n{window_title} ({window_desc}):")
                    report_lines.append(f"  统计基数: {effective_periods}期数据，{total_pairs}个相邻期对")
                    
                    # 重号分布（按照共识方案：只显示百分比）
                    repeat_dist = window_data.get('repeat_distribution', {})
                    if repeat_dist:
                        report_lines.append("  重号数量概率分布:")
                        for count in range(0, 7):
                            prob = repeat_dist.get(count, 0.0)
                            report_lines.append(f"    重复{count}个红球: {prob:.2%}")
                    
                    # 蓝球重复概率
                    blue_prob = window_data.get('blue_repeat_probability', 0)
                    report_lines.append(f"  蓝球重复概率: {blue_prob:.2%}")
        
        # 趋势分析
        trends_analysis = analysis_result.get('trends_analysis', {})
        if trends_analysis:
            report_lines.append("\n" + "=" * 60)
            report_lines.append("🎯 重号分布趋势分析")
            report_lines.append("=" * 60)
            
            repeat_trends = trends_analysis.get('repeat_trends', {})
            most_likely = trends_analysis.get('most_likely_repeat_count', 0)
            trend_summary = trends_analysis.get('trend_summary', '')
            
            report_lines.append(f"\n最可能重复数量: {most_likely}个红球")
            report_lines.append("\n跨窗口期趋势分析:")
            
            for count in range(0, 7):
                if count in repeat_trends:
                    trend_data = repeat_trends[count]
                    probabilities = trend_data['probabilities']
                    trend = trend_data['trend']
                    
                    # 获取四个窗口期的概率
                    short_prob = probabilities.get('short_term', 0.0)
                    medium_prob = probabilities.get('medium_term', 0.0)
                    long_prob = probabilities.get('long_term', 0.0)
                    all_prob = probabilities.get('all_history', 0.0)
                    
                    # 只显示有意义的趋势
                    if long_prob > 0.01 or trend != "稳定":
                        report_lines.append(f"  重复{count}个红球:")
                        report_lines.append(f"    短期({short_prob:.1%}) → 中期({medium_prob:.1%}) → 长期({long_prob:.1%}) → 全部({all_prob:.1%})")
                        report_lines.append(f"    趋势判断: {trend}")
            
            if trend_summary:
                report_lines.append(f"\n趋势总结:\n{trend_summary}")
        
        # 综合预测
        comprehensive = analysis_result.get('comprehensive_predictions', {})
        if comprehensive:
            report_lines.append("\n" + "=" * 60)
            report_lines.append("💡 综合预测建议 (基于长期窗口)")
            report_lines.append("=" * 60)
            
            window_source = comprehensive.get('window_source', '未知')
            window_display = comprehensive.get('window_display_name', '未知')
            
            repeat_dist = comprehensive.get('repeat_distribution', {})
            if repeat_dist:
                report_lines.append(f"\n{window_display}重号分布:")
                for count in range(0, 7):
                    prob = repeat_dist.get(count, 0.0)
                    if prob > 0:
                        report_lines.append(f"  重复{count}个红球: {prob:.2%}")
                
                # 找出最高概率的重号数量
                max_prob = 0
                best_count = 0
                for count, prob in repeat_dist.items():
                    if prob > max_prob:
                        max_prob = prob
                        best_count = count
                
                if max_prob > 0:
                    report_lines.append(f"\n🎯 预测建议:")
                    report_lines.append(f"  最可能重复: {best_count}个红球 (概率: {max_prob:.2%})")
                    
                    # 根据概率给出建议
                    if best_count <= 1:
                        report_lines.append(f"  建议: 重点关注0-1个重号的情况")
                    elif best_count <= 3:
                        report_lines.append(f"  建议: 重点关注{best_count-1}-{best_count+1}个重号的范围")
                    else:
                        report_lines.append(f"  建议: 重号较多，需谨慎选择")
            
            # 蓝球重复概率
            blue_prob = comprehensive.get('blue_repeat_probability', 0)
            report_lines.append(f"\n🔵 蓝球重复概率: {blue_prob:.2%}")
            if blue_prob < 0.05:
                report_lines.append("  建议: 蓝球重复概率较低，不建议选择上期蓝球")
            elif blue_prob < 0.1:
                report_lines.append("  建议: 蓝球重复概率一般，可适当考虑")
            else:
                report_lines.append("  建议: 蓝球重复概率较高，值得关注")
        
        # 调试信息
        debug_info = {
            '分析模式': '多窗口期实际重复统计',
            '相似度筛选': '未使用',
            '统计方法': '基于实际发生的重复次数',
            '数据来源': '全部历史数据分窗口统计'
        }
        
        report_lines.append("\n" + "=" * 60)
        report_lines.append("分析说明")
        report_lines.append("=" * 60)
        for key, value in debug_info.items():
            report_lines.append(f"  {key}: {value}")
        
        return "\n".join(report_lines)
    
    def _calculate_similarity(self, list1: List[int], list2: List[int]) -> float:
        """
        计算两个列表的相似度（保留方法以兼容，但不再使用）
        现在基于实际重复统计，不进行相似度筛选
        """
        # 此方法保留但不主动使用
        set1 = set(list1)
        set2 = set(list2)
        return len(set1 & set2) / len(set1 | set2) if len(set1 | set2) > 0 else 0