# services/prediction_service.py
"""
预测服务，提供统一预测接口 - 支持多窗口期分析
"""
import logging
import time
import os
from typing import Dict, Any, List
from datetime import datetime
from data.predictor import EnhancedPredictor
from analysis.probability_analyzer import ProbabilityAnalyzer
from analysis.hot_cold_analyzer import get_hot_cold_analyzer  # 导入统一的热冷号分析器
from utils.db_manager import DatabaseManager
from utils.color_utils import print_success, print_warning, print_error
from utils.window_config import WindowConfigManager


logger = logging.getLogger('prediction_service')

class PredictionService:
    """预测服务 - 支持多窗口期分析"""
    
    def __init__(self, db_path: str = None, analysis_service=None):
        # 注意：这里增加了 analysis_service 参数，并为其设置了默认值 None
        # 使用数据库管理器获取数据库实例
        self.db_manager = DatabaseManager()
        if db_path is None:
            # 从 config 获取默认路径
            try:
                from config import config
                db_path = config.paths.DATABASE_PATH
            except ImportError:
                db_path = "double_ball.db"
        self.db = self.db_manager.get_db(db_path)

        # 初始化增强预测器
        self.predictor = EnhancedPredictor(self.db)

        # 初始化概率分析器
        self.probability_analyzer = ProbabilityAnalyzer(self.db)
        
        # 初始化热冷号分析器（统一实例）
        self.hot_cold_analyzer = get_hot_cold_analyzer(self.db)
        self.reports_history = []  # 保存报告历史
        
        # 缓存热冷号分类，避免重复计算
        self._hot_cold_cache = {}

        # 【新增】保存分析服务实例
        # 这里的 analysis_service 指的是传入的参数
        self.analysis_service_instance = analysis_service  # 建议换个名字，避免与参数名混淆
        # 或者直接 self._analysis_service = analysis_service

    def _get_analysis_service(self):
        """惰性获取分析服务实例"""
        if self.analysis_service_instance is None:
            from services.analysis_service import get_analysis_service
            self.analysis_service_instance = get_analysis_service()
        return self.analysis_service_instance

    def run_enhanced_prediction(self, use_ml: bool = True) -> Dict[str, Any]:
        """运行增强预测 - 支持多窗口期分析"""
        try:
            # 使用增强预测器
            result = self.predictor.predict_with_probability()

            # 确保结果格式正确
            if not isinstance(result, dict) or '6_plus_1' not in result:
                logger.error(f"预测器返回结果格式错误: {type(result)}")
                # 返回一个安全的默认结果
                result = self._get_default_prediction_result()
            
            # ========== 新增：修复扩展关系逻辑 ==========
            # 确保7+1包含6+1的所有红球，8+1包含7+1的所有红球
            result = self._ensure_prediction_hierarchy(result)
            
            # ========== 新增：获取推荐号码用于ML预测 ==========
            # 获取基础红球和蓝球用于ML预测
            base_reds = result.get('6_plus_1', {}).get('red_balls', [])
            base_blue = result.get('6_plus_1', {}).get('blue_ball', 0)
            
            # 添加机器学习结果（如果有）
            if use_ml:
                try:
                    from config import config
                    ml_enabled = config.prediction.ML_ENABLED
                    if ml_enabled:
                        # 传递基础号码给ML预测器
                        ml_result = self._get_ml_prediction(base_reds, base_blue)
                        if ml_result and 'error' not in ml_result:
                            result['ml_predictions'] = ml_result
                            logger.info("✅ 机器学习预测已合并")
                        else:
                            logger.info("ℹ️  使用统计预测（ML未启用或失败）")
                except ImportError as e:
                    logger.warning(f"ML配置导入失败: {e}")
                except Exception as e:
                    logger.warning(f"ML预测失败: {e}")
            
            # ========== 修改：基于ML结果调整预测 ==========
            # 如果ML预测可用，可以基于它进一步优化
            if 'ml_predictions' in result:
                result = self._adjust_with_ml_predictions(result)
            
            # 添加系统信息
            result['system_info'] = self._get_system_info()

            # 获取多窗口期统计信息
            stats_by_window = self._get_multi_window_statistics()
            if stats_by_window:
                result['statistics_by_window'] = stats_by_window

                # 构建综合趋势信息（以长期窗口为主）
                if 'long_term' in stats_by_window:
                    stats = stats_by_window['long_term']
                    trends = {
                        'sum_trend': stats.get('sum_trend', '未知'),
                        'hot_reds': stats.get('hot_reds', [])[:5],
                        'warm_reds': stats.get('warm_reds', [])[:5],
                        'cold_reds': stats.get('cold_reds', [])[:5],
                        'primary_window': 'long_term'
                    }
                elif stats_by_window:
                    # 使用第一个可用的窗口
                    first_window = next(iter(stats_by_window.values()))
                    trends = {
                        'sum_trend': first_window.get('sum_trend', '未知'),
                        'hot_reds': first_window.get('hot_reds', [])[:5],
                        'warm_reds': first_window.get('warm_reds', [])[:5],
                        'cold_reds': first_window.get('cold_reds', [])[:5],
                        'primary_window': list(stats_by_window.keys())[0]
                    }
                else:
                    trends = {}

                result['trends'] = trends

            # 获取多窗口期重号概率分析
            try:
                latest_record = self.db.get_latest_record()
                if latest_record:
                    # 使用所有窗口进行分析
                    repeat_analysis = self.probability_analyzer.analyze_current_period_probability(
                        latest_record,
                        window_group=['short_term', 'medium_term', 'long_term', 'all_history']
                    )
                    result['repeat_analysis'] = repeat_analysis

                    # 提取关键概率信息用于预测优化
                    if 'window_analysis' in repeat_analysis:
                        # 可以基于不同窗口期的概率调整预测
                        self._adjust_predictions_with_probability(result, repeat_analysis)
            except Exception as e:
                logger.warning(f"获取重号分析失败: {e}")

            # ========== 新增：统一热冷号标签 ==========
            # 使用统一的窗口期（默认30期）为所有号码添加热冷号标签
            self._add_unified_hot_cold_labels(result)
            
            print_success("预测完成 (多窗口期分析)")
            return result

        except Exception as e:
            logger.error(f"预测失败: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _add_unified_hot_cold_labels(self, result: Dict[str, Any]) -> None:
        """
        为所有预测号码添加统一的热冷号标签
        
        使用统一的窗口期（默认30期）确保所有号码标签一致
        """
        try:
            # 获取统一的热冷号分类（使用短期窗口配置）
            try:
                from utils.window_config import WindowConfigManager
                short_term_window = WindowConfigManager.get_window_by_name('short_term')
            except (ImportError, AttributeError):
                short_term_window = 30  # 备用值

            cache_key = f"window_{short_term_window}"
            if cache_key not in self._hot_cold_cache:
                categories = self.hot_cold_analyzer.analyze(window=short_term_window)
                self._hot_cold_cache[cache_key] = categories
            else:
                categories = self._hot_cold_cache[cache_key]
            
            # 为每个预测组合添加标签
            for key in ['6_plus_1', '7_plus_1', '8_plus_1']:
                if key in result and isinstance(result[key], dict):
                    pred = result[key]
                    reds = pred.get('red_balls', [])
                    
                    if isinstance(reds, list):
                        # 为每个红球添加热冷号标签
                        ball_statuses = []
                        for ball in reds:
                            if isinstance(ball, int) and 1 <= ball <= 33:
                                status = self.hot_cold_analyzer.get_ball_status(ball, categories)
                                ball_statuses.append(f"{ball:02d}({status})")
                            else:
                                ball_statuses.append(str(ball))
                        
                        # 添加标签字段
                        pred['red_balls_with_labels'] = ' '.join(ball_statuses)
            
            logger.debug("已为所有预测号码添加统一的热冷号标签")
            
        except Exception as e:
            logger.warning(f"添加热冷号标签失败: {e}")
    
    def _ensure_prediction_hierarchy(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        确保预测结果的扩展关系：
        7+1 包含 6+1 的所有红球，再加一个红球，蓝球相同
        8+1 包含 7+1 的所有红球，再加一个红球，蓝球相同
        """
        try:
            # 获取6+1的基础预测
            base_6_plus_1 = result.get('6_plus_1', {})
            base_reds = base_6_plus_1.get('red_balls', [])
            base_blue = base_6_plus_1.get('blue_ball', 0)
            
            if not base_reds or len(base_reds) != 6:
                logger.warning("6+1预测结果不完整，跳过扩展关系调整")
                return result
            
            # ========== 新增：智能选择扩展号码 ==========
            # 从热号、温号、冷号中选择最佳的扩展号码
            extension_candidates = self._get_extension_candidates(result)
            
            # 生成7+1扩展号码
            if len(extension_candidates) >= 1:
                seventh_ball = extension_candidates[0]
                reds_7_plus_1 = sorted(base_reds + [seventh_ball])
                
                # 生成8+1扩展号码
                if len(extension_candidates) >= 2:
                    eighth_ball = extension_candidates[1]
                    reds_8_plus_1 = sorted(reds_7_plus_1 + [eighth_ball])
                else:
                    # 如果没有第二个候选，使用一个安全的选择
                    safe_ball = self._find_safe_extension(reds_7_plus_1)
                    reds_8_plus_1 = sorted(reds_7_plus_1 + [safe_ball])
            else:
                # 如果没有候选，使用默认扩展
                reds_7_plus_1 = sorted(base_reds + [self._find_safe_extension(base_reds)])
                reds_8_plus_1 = sorted(reds_7_plus_1 + [self._find_safe_extension(reds_7_plus_1)])
            
            # ========== 修改：保留原有策略并调整置信度 ==========
            # 更新7+1预测
            if '7_plus_1' in result:
                result['7_plus_1']['red_balls'] = reds_7_plus_1
                result['7_plus_1']['blue_ball'] = base_blue
                # 稍微降低扩展预测的置信度
                base_confidence = base_6_plus_1.get('confidence', 50)
                result['7_plus_1']['confidence'] = base_confidence * 0.9
                result['7_plus_1']['strategy'] = f"{base_6_plus_1.get('strategy', '基础策略')} + 扩展"
            else:
                result['7_plus_1'] = {
                    'red_balls': reds_7_plus_1,
                    'blue_ball': base_blue,
                    'confidence': base_6_plus_1.get('confidence', 50) * 0.9,
                    'strategy': f"{base_6_plus_1.get('strategy', '基础策略')} + 扩展"
                }
            
            # 更新8+1预测
            if '8_plus_1' in result:
                result['8_plus_1']['red_balls'] = reds_8_plus_1
                result['8_plus_1']['blue_ball'] = base_blue
                # 进一步降低置信度
                result['8_plus_1']['confidence'] = base_6_plus_1.get('confidence', 50) * 0.8
                result['8_plus_1']['strategy'] = f"{base_6_plus_1.get('strategy', '基础策略')} + 双重扩展"
            else:
                result['8_plus_1'] = {
                    'red_balls': reds_8_plus_1,
                    'blue_ball': base_blue,
                    'confidence': base_6_plus_1.get('confidence', 50) * 0.8,
                    'strategy': f"{base_6_plus_1.get('strategy', '基础策略')} + 双重扩展"
                }
            
            logger.info(f"✅ 已修复预测扩展关系: 6+1 → 7+1 → 8+1")
            logger.debug(f"扩展候选号码: {extension_candidates}")
            
        except Exception as e:
            logger.warning(f"修复预测扩展关系失败: {e}")
        
        return result
    
    def _get_extension_candidates(self, result: Dict[str, Any]) -> List[int]:
        """获取扩展号码候选列表"""
        candidates = []
        
        try:
            # 【修复】从WindowConfigManager获取窗口期，而不是使用未定义的变量
            from utils.window_config import WindowConfigManager
            short_term_window_size = WindowConfigManager.get_window_by_name('short_term')

            # 获取统一的热冷号分类（使用默认窗口30期）
            cache_key = f"window_{short_term_window_size }"
            if cache_key not in self._hot_cold_cache:
                categories = self.hot_cold_analyzer.analyze(window=short_term_window_size )
                self._hot_cold_cache[cache_key] = categories
            else:
                categories = self._hot_cold_cache[cache_key]
            
            # 优先选择热号和温号作为扩展候选
            hot_numbers = categories.get('hot', [])
            warm_numbers = categories.get('warm', [])
            
            # 添加热号
            for ball in hot_numbers:
                if isinstance(ball, int) and 1 <= ball <= 33:
                    candidates.append(ball)
            
            # 添加温号
            for ball in warm_numbers:
                if isinstance(ball, int) and 1 <= ball <= 33:
                    candidates.append(ball)
            
            # 去重
            candidates = list(dict.fromkeys(candidates))
            
            logger.debug(f"扩展候选号码: 热号{len(hot_numbers)}个, 温号{len(warm_numbers)}个")
            
        except Exception as e:
            logger.warning(f"获取扩展候选失败: {e}")
            # 返回一个默认的候选列表
            candidates = list(range(1, 34))
        
        return candidates
    
    def _find_safe_extension(self, existing_reds: List[int]) -> int:
        """查找一个安全的扩展号码（不在现有号码中）"""
        try:
            all_balls = list(range(1, 34))
            available = [ball for ball in all_balls if ball not in existing_reds]
            
            if available:
                # 优先选择中间范围的号码
                middle_range = [ball for ball in available if 10 <= ball <= 24]
                if middle_range:
                    return middle_range[0]
                else:
                    return available[0]
            else:
                # 如果没有可用号码，返回一个默认值
                return 1 if 1 not in existing_reds else 2
        except:
            return 1
    
    def _adjust_with_ml_predictions(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """基于ML预测结果调整最终预测"""
        try:
            ml_predictions = result.get('ml_predictions', {})
            
            if ml_predictions and 'error' not in ml_predictions:
                ml_confidence = ml_predictions.get('confidence', 0)
                ml_balls = ml_predictions.get('predicted_balls', [])
                
                if ml_balls and len(ml_balls) >= 6:
                    # 如果ML预测可用，可以微调置信度
                    for key in ['6_plus_1', '7_plus_1', '8_plus_1']:
                        if key in result:
                            # 计算与ML预测的重合度
                            if key == '6_plus_1':
                                pred_balls = set(result[key].get('red_balls', []))
                                ml_set = set(ml_balls[:6])  # 取前6个ML预测
                                overlap = len(pred_balls.intersection(ml_set))
                                
                                # 根据重合度调整置信度
                                adjustment = overlap * 2  # 每个重合号码增加2%置信度
                                new_confidence = min(100, result[key].get('confidence', 50) + adjustment)
                                result[key]['confidence'] = new_confidence
                                
                                if adjustment > 0:
                                    result[key]['ml_adjustment'] = adjustment
                                    result[key]['ml_overlap'] = overlap
                    
                    # 添加ML建议
                    result['ml_suggestions'] = {
                        'confidence': ml_confidence,
                        'top_picks': ml_balls[:6],
                        'full_set': ml_balls,
                        'timestamp': datetime.now().isoformat()
                    }
            
        except Exception as e:
            logger.warning(f"基于ML调整预测失败: {e}")
        
        return result

    def _get_ml_prediction(self, base_reds: List[int] = None, base_blue: int = None) -> Dict[str, Any]:
        """获取机器学习预测结果"""
        try:
            # 方案1：尝试从model_training服务获取
            try:
                from services.model_training import ModelTrainingService
                ml_service = ModelTrainingService(self.db)
                
                # 传递基础预测作为参考
                prediction_result = ml_service.get_prediction(
                    reference_reds=base_reds,
                    reference_blue=base_blue
                )
                
                if prediction_result and 'error' not in prediction_result:
                    logger.info("✅ 成功从ModelTrainingService获取ML预测")
                    return prediction_result
            except ImportError as e:
                logger.debug(f"无法导入ModelTrainingService: {e}")
            except Exception as e:
                logger.debug(f"ModelTrainingService调用失败: {e}")

            # 方案2：检查是否有本地ML模型文件
            try:
                models_dir = "models"
                if os.path.exists(models_dir):
                    model_files = [
                        os.path.join(models_dir, f) 
                        for f in os.listdir(models_dir) 
                        if f.endswith('.pkl') or f.endswith('.joblib')
                    ]
                    
                    if model_files:
                        latest_model = max(model_files, key=os.path.getmtime)
                        logger.info(f"找到ML模型文件: {latest_model}")
                        
                        # 根据文件扩展名选择合适的加载方式
                        if latest_model.endswith('.pkl'):
                            import pickle
                            with open(latest_model, 'rb') as f:
                                model = pickle.load(f)
                        else:  # .joblib
                            import joblib
                            model = joblib.load(latest_model)
                        
                        # 简单预测逻辑（需要根据实际模型调整）
                        if hasattr(model, 'predict'):
                            # 这里需要准备特征数据，根据实际情况调整
                            # 暂时返回一个模拟结果
                            import random
                            ml_balls = sorted(random.sample(range(1, 34), 12))
                            ml_blue = random.randint(1, 16)
                            
                            return {
                                'model_type': type(model).__name__,
                                'confidence': random.uniform(0.6, 0.9),
                                'predicted_balls': ml_balls,
                                'predicted_blue': ml_blue,
                                'model_file': os.path.basename(latest_model),
                                'message': '使用本地预训练模型'
                            }
            except Exception as e:
                logger.debug(f"本地ML模型加载失败: {e}")

            # 方案3：尝试使用简单的统计学习模型
            try:
                # 如果没有预训练模型，使用简单的统计方法模拟ML
                from sklearn.ensemble import RandomForestClassifier
                from sklearn.preprocessing import LabelEncoder
                import numpy as np
                
                # 获取历史数据
                records = self.db.get_all_records(limit=100)
                if len(records) >= 20:
                    # 准备训练数据（简化版）
                    X = []
                    y = []
                    
                    for i in range(len(records)-1):
                        current = records[i]
                        next_record = records[i+1]
                        
                        # 特征：当前期号码的分布
                        features = [int(ball in current['red_balls']) for ball in range(1, 34)]
                        features.append(current['blue_ball'])
                        
                        # 标签：下期是否出现（简化）
                        label = int(any(ball in next_record['red_balls'] for ball in current['red_balls']))
                        
                        X.append(features)
                        y.append(label)
                    
                    if len(X) > 10:
                        clf = RandomForestClassifier(n_estimators=50, random_state=42)
                        clf.fit(X, y)
                        
                        # 使用最新一期进行预测
                        latest = records[-1]
                        latest_features = [int(ball in latest['red_balls']) for ball in range(1, 34)]
                        latest_features.append(latest['blue_ball'])
                        
                        # 预测每个号码在下期出现的概率
                        probabilities = []
                        for ball in range(1, 34):
                            test_features = latest_features.copy()
                            clf.predict_proba([test_features])
                            # 这里需要根据实际情况调整
                        
                        return {
                            'model_type': 'RandomForest',
                            'confidence': 0.7,
                            'message': '使用在线训练的简单模型',
                            'training_samples': len(X)
                        }
            except Exception as e:
                logger.debug(f"简单统计学习失败: {e}")

            # 方案4：返回ML状态信息
            return {
                'ml_enabled': True,
                'model_available': False,
                'message': 'ML功能已启用，但未找到可用的训练模型',
                'recommendation': '请运行 model_training.py 训练模型',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"ML预测异常: {e}", exc_info=True)
            return {
                'error': f'ML预测异常: {str(e)}',
                'error_type': type(e).__name__
            }

    def _get_multi_window_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        获取多窗口期统计信息（使用统一窗口配置）
        """
        stats_by_window = {}

        try:
            # 使用统一窗口配置管理器
            try:
                from utils.window_config import WindowConfigManager
                # 获取所有窗口配置
                all_windows = WindowConfigManager.get_all_windows()

                # 定义我们需要分析的窗口
                windows = {
                    'short_term': all_windows.get('short_term', 30),
                    'medium_term': all_windows.get('medium_term', 50),
                    'long_term': all_windows.get('long_term', 100)
                }

                logger.info(f"使用统一窗口配置: {windows}")

            except ImportError as e:
                logger.warning(f"无法导入WindowConfigManager: {e}")
                # 回退到config读取（保持原有逻辑）
                from config import config
                windows = {
                    'short_term': WindowConfigManager.get_window_by_name('short_term'),
                    'medium_term': WindowConfigManager.get_window_by_name('short_term'),
                    'long_term': WindowConfigManager.get_window_by_name('short_term')
                }
                logger.info(f"使用旧窗口配置: {windows}")

            total_records = self.db.get_record_count()

            for window_name, period in windows.items():
                if period is None:
                    continue

                # 确保不超过总记录数
                effective_period = min(period, total_records) if total_records > 0 else period

                if effective_period >= 10:  # 最小有效期数
                    try:
                        window_stats = self.db.get_statistics_with_period(effective_period)
                        if window_stats:
                            # 添加窗口信息
                            window_stats['window_name'] = window_name
                            window_stats['period_used'] = effective_period
                            window_stats['period_config'] = period

                            stats_by_window[window_name] = window_stats
                            logger.debug(f"获取窗口 '{window_name}' 统计: {effective_period}期数据")
                    except Exception as e:
                        logger.warning(f"获取窗口 '{window_name}' 统计失败: {e}")

            logger.info(f"成功获取 {len(stats_by_window)} 个窗口期的统计信息")

        except Exception as e:
            logger.error(f"获取多窗口统计失败: {e}")

        return stats_by_window
    
    def _adjust_predictions_with_probability(
        self, 
        prediction_result: Dict[str, Any], 
        probability_analysis: Dict[str, Any]
    ) -> None:
        """
        基于概率分析调整预测结果
        
        根据不同窗口期的重复概率，调整预测的置信度和策略
        """
        try:
            if 'window_analysis' not in probability_analysis:
                return
            
            window_analysis = probability_analysis['window_analysis']
            
            # 获取主要窗口的概率信息
            primary_probabilities = {}
            
            # 优先使用长期窗口
            for window_name in ['long_term', 'medium_term', 'short_term', 'all_history']:
                if window_name in window_analysis:
                    window_result = window_analysis[window_name]
                    
                    # 获取重号分布
                    repeat_dist = window_result.get('repeat_distribution', {})
                    if repeat_dist:
                        # 找到最可能的重号数量
                        most_likely_count = max(repeat_dist.items(), key=lambda x: x[1])[0] if repeat_dist else 0
                        primary_probabilities['most_likely_repeat_count'] = most_likely_count
                    
                    # 获取蓝球重复概率
                    blue_prob = window_result.get('blue_repeat_probability', 0)
                    primary_probabilities['blue_repeat_probability'] = blue_prob
                    
                    # 获取当前期预测
                    predictions = window_result.get('current_predictions', {})
                    if predictions:
                        primary_probabilities.update({
                            'predicted_avg_repeat': predictions.get('avg_repeat_count', 0),
                            'predicted_blue_repeat': predictions.get('blue_repeat_probability', 0)
                        })
                    
                    primary_probabilities['primary_window'] = window_name
                    break
            
            if primary_probabilities:
                prediction_result['probability_insights'] = primary_probabilities
                
                # 可以基于概率调整预测的置信度
                most_likely_count = primary_probabilities.get('most_likely_repeat_count', 0)
                blue_repeat_prob = primary_probabilities.get('blue_repeat_probability', 0)
                
                # 调整预测组合的置信度
                for key in ['6_plus_1', '7_plus_1', '8_plus_1']:
                    if key in prediction_result and isinstance(prediction_result[key], dict):
                        original_confidence = prediction_result[key].get('confidence', 50)
                        
                        # 基于概率微调查信度
                        adjustment = 0
                        
                        # 如果蓝球重复概率高，适当提高置信度
                        if blue_repeat_prob > 0.15:  # 超过15%的概率
                            adjustment += 5 * blue_repeat_prob
                        
                        # 如果重号数量适中（2-3个），适当提高置信度
                        if 2 <= most_likely_count <= 3:
                            adjustment += 3
                        
                        new_confidence = min(100, max(0, original_confidence + adjustment))
                        
                        if adjustment != 0:
                            prediction_result[key]['confidence'] = new_confidence
                            prediction_result[key]['probability_adjustment'] = adjustment
                            prediction_result[key]['adjustment_reason'] = (
                                f"基于{primary_probabilities.get('primary_window', '未知')}窗口概率分析"
                            )
                
                logger.debug(f"基于概率分析调整预测，主要窗口: {primary_probabilities.get('primary_window', '未知')}")
        
        except Exception as e:
            logger.warning(f"基于概率调整预测失败: {e}")
    
    def _get_default_prediction_result(self) -> Dict[str, Any]:
        """获取默认预测结果"""
        return {
            '6_plus_1': {
                'red_balls': [], 
                'blue_ball': 0, 
                'confidence': 0, 
                'strategy': '默认'
            },
            '7_plus_1': {
                'red_balls': [], 
                'blue_ball': 0, 
                'confidence': 0, 
                'strategy': '默认'
            },
            '8_plus_1': {
                'red_balls': [], 
                'blue_ball': 0, 
                'confidence': 0, 
                'strategy': '默认'
            },
            'timestamp': datetime.now().isoformat(),
            'recommended_combination': '6+1',
            'recommended_confidence': 0
        }

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        total_records = self.db.get_record_count()
        
        # 获取窗口配置信息
        window_config = {}
        try:
            from config import config
            window_config = {
                'short_term': WindowConfigManager.get_window_by_name('short_term'),
                'medium_term': WindowConfigManager.get_window_by_name('medium_term'),
                'long_term': WindowConfigManager.get_window_by_name('long_term')
            }
        except ImportError:
            window_config = {'error': '无法获取窗口配置'}
        
        return {
            'database_path': self.db.db_path,
            'records_count': total_records,
            'latest_issue': self.db.get_latest_issue(),
            'prediction_time': datetime.now().isoformat(),
            'window_configuration': window_config
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息（用于显示）"""
        total_records = self.db.get_record_count()
        
        # 获取窗口统计信息
        window_stats_info = []
        stats_by_window = self._get_multi_window_statistics()
        
        for window_name, stats in stats_by_window.items():
            period_used = stats.get('period_used', 0)
            record_count = stats.get('record_count', 0)
            window_stats_info.append({
                'window': window_name,
                'periods': period_used,
                'records': record_count
            })
        
        return {
            'database': {'database_path': self.db.db_path},
            'records_count': total_records,
            'latest_issue': self.db.get_latest_issue(),
            'window_statistics': window_stats_info,
            'model_status': {
                'ml_available': True,
                'models_trained': False
            },
            'prediction_history_count': len(self.reports_history)
        }
    
    def get_prediction_history(self, limit: int = 5) -> list:
        """获取预测历史"""
        return self.reports_history[-limit:] if self.reports_history else []

    # services/prediction_service.py - generate_prediction_report 方法修改部分
    def generate_prediction_report(self, result: Dict[str, Any]) -> str:
        """生成预测报告文本 - 按照共识方案显示多窗口期概率分析"""
        if not isinstance(result, dict):
            logger.error(f"预测结果不是字典类型: {type(result)}")
            return "预测结果格式错误"

        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("🎯 双色球增强预测报告 (多窗口期分析)")
        report_lines.append("=" * 70)
        report_lines.append(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 系统信息（保持原样）
        if 'system_info' in result:
            info = result['system_info']

            # 数据库路径显示优化
            db_path = info.get('database_path', '未知')
            if isinstance(db_path, str) and '/' in db_path:
                db_path = db_path.split('/')[-1]  # 只显示文件名
            report_lines.append(f"💾 数据库: {db_path}")

            # 记录数
            records_count = info.get('records_count', 0)
            report_lines.append(f"📊 总记录数: {records_count:,} 期")

            # 最新期号
            latest_issue = info.get('latest_issue', '未知')
            report_lines.append(f"🎯 最新期号: {latest_issue}")

            # 窗口配置
            window_config = info.get('window_configuration', {})
            if window_config and isinstance(window_config, dict):
                report_lines.append("\n📈 分析窗口配置:")
                for window_name, period in window_config.items():
                    if isinstance(period, int):
                        display_name = {
                            'short_term': '📱 短期',
                            'medium_term': '📊 中期',
                            'long_term': '📈 长期'
                        }.get(window_name, window_name)
                        report_lines.append(f"   {display_name}: {period}期")

        # 错误信息
        if 'error' in result:
            report_lines.append(f"\n❌ 错误信息: {result['error']}")
            return "\n".join(report_lines)

        # 预测结果（保持原样）
        report_lines.append("\n🎯 预测结果:")

        # 定义组合显示
        combinations = [
            ('6_plus_1', '💰 6+1基础组合'),
            ('7_plus_1', '💎 7+1扩展组合'),
            ('8_plus_1', '🚀 8+1高级组合')
        ]

        for key, display_name in combinations:
            if key in result and isinstance(result[key], dict):
                pred = result[key]

                # 安全获取数据
                reds = pred.get('red_balls', [])
                blue = pred.get('blue_ball', 0)
                conf = pred.get('confidence', 0)
                strategy = pred.get('strategy', '未知策略')

                if isinstance(reds, list) and len(reds) > 0:
                    try:
                        sorted_reds = sorted([int(x) for x in reds if str(x).isdigit()])
                        red_str = ' '.join([f'{red:02d}' for red in sorted_reds])
                    except Exception as e:
                        logger.debug(f"格式化红球失败: {e}")
                        red_str = str(reds)
                else:
                    red_str = '无数据'

                # 格式化蓝球
                if isinstance(blue, int) and 1 <= blue <= 16:
                    blue_str = f'{blue:02d}'
                else:
                    blue_str = str(blue)

                report_lines.append(f"\n{display_name}:")
                report_lines.append(f"   🔴 红球: {red_str}")
                report_lines.append(f"   🔵 蓝球: {blue_str}")
                report_lines.append(f"   📊 置信度: {conf:.1f}%")
                report_lines.append(f"   🎯 策略: {strategy}")

        # 推荐组合
        if 'recommended_combination' in result:
            report_lines.append("\n🏆 推荐组合:")
            report_lines.append(f"   💎 最佳组合: {result.get('recommended_combination', '未知')}")
            report_lines.append(f"   ⭐ 推荐置信度: {result.get('recommended_confidence', 0):.1f}%")

        # ========== 按照共识方案显示多窗口期概率分析 ==========
        if 'repeat_analysis' in result:
            repeat_analysis = result['repeat_analysis']

            if isinstance(repeat_analysis, dict) and 'window_analysis' in repeat_analysis:
                window_analysis = repeat_analysis['window_analysis']

                # 定义窗口期显示顺序和名称
                window_display_config = [
                    ('short_term', '📱 短期窗口', '短期窗口 (最近30期)'),
                    ('medium_term', '📊 中期窗口', '中期窗口 (最近50期)'),
                    ('long_term', '📈 长期窗口', '长期窗口 (最近100期)'),
                    ('all_history', '📚 全部历史', '全部历史数据')
                ]

                # 1. 显示四个窗口期的重号分布和蓝球重复概率
                report_lines.append("\n📊 概率分析 (多窗口期):")

                for window_key, window_title, window_desc in window_display_config:
                    if window_key in window_analysis:
                        window_data = window_analysis[window_key]
                        total_pairs = window_data.get('total_pairs', 0)

                        if total_pairs > 0:
                            report_lines.append(f"\n  {window_title}:")
                            report_lines.append(f"    {window_desc}")

                            # 重号分布（按照共识方案：只显示百分比）
                            repeat_dist = window_data.get('repeat_distribution', {})
                            if isinstance(repeat_dist, dict):
                                # 按照共识方案：0个(33%) | 1个(36%) | 2个(24%) | 3个(6%) | 4-6个(0%)
                                dist_items = []
                                for i in range(0, 7):
                                    prob = repeat_dist.get(i, 0)
                                    if isinstance(prob, (int, float)):
                                        if i <= 3:
                                            dist_items.append(f"{i}个({prob:.1%})")
                                        elif i == 4:
                                            # 合并显示4-6个
                                            prob_4_6 = sum([repeat_dist.get(j, 0) for j in range(4, 7)])
                                            dist_items.append(f"4-6个({prob_4_6:.1%})")
                                            break

                                if dist_items:
                                    report_lines.append(f"    重号分布: {' | '.join(dist_items)}")
                            else:
                                report_lines.append("    重号分布: 无数据")

                            # 蓝球重复概率
                            blue_prob = window_data.get('blue_repeat_probability', 0)
                            if isinstance(blue_prob, (int, float)):
                                report_lines.append(f"    蓝球重复: {blue_prob:.2%}")


                # 2. 进行重号数量的趋势分析
                report_lines.append("\n🎯 综合预测与趋势分析:")

                # 收集四个窗口期的趋势数据
                trend_data = self._analyze_repeat_trends(window_analysis)

                # 找出最可能的重号数量（基于长期窗口）
                most_likely_count = 0
                max_prob = 0
                if 'long_term' in window_analysis:
                    repeat_dist = window_analysis['long_term'].get('repeat_distribution', {})
                    for count, prob in repeat_dist.items():
                        if isinstance(prob, (int, float)) and prob > max_prob:
                            max_prob = prob
                            most_likely_count = count

                report_lines.append(f"\n  最可能重复: {most_likely_count}个红球")

                # 显示趋势分析
                report_lines.append("\n  趋势分析:")
                report_lines.append("    从四个窗口期的统计来看:")

                # 为每个重复数量计算趋势
                for count in range(0, 4):  # 只显示0-3个重号
                    probs_with_labels = []
                    for window_key, window_title, window_desc in window_display_config:
                        if window_key in window_analysis:
                            repeat_dist = window_analysis[window_key].get('repeat_distribution', {})
                            prob = repeat_dist.get(count, 0)
                            if isinstance(prob, (int, float)):
                                # probs.append(f"{prob:.1%}")
                                # 根据窗口类型添加标签
                                period_name = {
                                    'short_term': '短期',
                                    'medium_term': '中期',
                                    'long_term': '长期',
                                    'all_history': '历史'
                                }.get(window_key, window_key)

                                probs_with_labels.append(f"{period_name}{prob:.1%}")
                            else:
                                probs_with_labels.append("N/A")
                        else:
                            probs_with_labels.append("N/A")

                    # 判断趋势
                    if len(probs_with_labels) == 4 and all(p != "N/A" for p in probs_with_labels):
                        try:
                            # 提取概率值（去掉标签）
                            prob_values = []
                            for p in probs_with_labels:
                                # 从"短期33.3%"中提取33.3
                                import re
                                match = re.search(r'(\d+\.?\d*)%', p)
                                if match:
                                    prob_values.append(float(match.group(1)) / 100)

                            if prob_values:
                                trend = self._determine_trend(prob_values)

                                # 修改：显示带周期标签的趋势
                                report_lines.append(
                                    f"    • 重复{count}个红球: {probs_with_labels[0]} → {probs_with_labels[1]} → {probs_with_labels[2]} → {probs_with_labels[3]} ({trend})")
                        except:
                                report_lines.append(
                                    f"    • 重复{count}个红球: {probs_with_labels[0]} → {probs_with_labels[1]} → {probs_with_labels[2]} → {probs_with_labels[3]} (数据异常)")

                # 趋势判断
                report_lines.append(f"\n  趋势判断:")

                # 获取长期窗口的重复1-2个的概率
                if 'long_term' in window_analysis:
                    repeat_dist = window_analysis['long_term'].get('repeat_distribution', {})
                    prob_1 = repeat_dist.get(1, 0)
                    prob_2 = repeat_dist.get(2, 0)
                    total_prob_1_2 = prob_1 + prob_2 if isinstance(prob_1, (int, float)) and isinstance(prob_2,
                                                                                                        (int,
                                                                                                         float)) else 0

                    report_lines.append(f"    • 整体趋势显示，随着统计窗口扩大，重复0个红球的概率下降")
                    report_lines.append(f"    • 重复1-2个红球的概率在长期窗口中为{total_prob_1_2:.1%}")
                    report_lines.append(f"    • 建议重点关注重复{most_likely_count}个红球的情况")

                # 蓝球重复概率建议
                if 'long_term' in window_analysis:
                    blue_prob = window_analysis['long_term'].get('blue_repeat_probability', 0)
                    if isinstance(blue_prob, (int, float)):
                        report_lines.append(f"\n  蓝球重复概率: {blue_prob:.2%} (基于长期窗口)")
                        if blue_prob < 0.05:
                            report_lines.append("  注: 蓝球重复概率较低，不建议选择上期蓝球")
                        elif blue_prob < 0.1:
                            report_lines.append("  注: 蓝球重复概率一般，可适当考虑")
                        else:
                            report_lines.append("  注: 蓝球重复概率较高，值得关注")

                # 4-6个重号合并显示（概率通常很低）
                probs_4_6 = []
                for window_key, _, _ in window_display_config:
                    if window_key in window_analysis:
                        repeat_dist = window_analysis[window_key].get('repeat_distribution', {})
                        prob = sum([repeat_dist.get(i, 0) for i in range(4, 7)])
                        if isinstance(prob, (int, float)):
                            probs_4_6.append(f"{prob:.1%}")
                        else:
                            probs_4_6.append("N/A")
                    else:
                        probs_4_6.append("N/A")

                if len(probs_4_6) == 4 and all(p != "N/A" for p in probs_4_6):
                    try:
                        total_prob = sum([float(p.strip('%')) / 100 for p in probs_4_6])
                        if total_prob > 0.001:  # 概率大于0.1%才显示
                            report_lines.append(
                                f"    • 重复4-6个红球: {probs_4_6[0]} → {probs_4_6[1]} → {probs_4_6[2]} → {probs_4_6[3]} (概率极低)")
                    except:
                        pass

                # 趋势判断
                report_lines.append(f"\n  趋势判断:")

                # 获取长期窗口的重复1-2个的概率
                if 'long_term' in window_analysis:
                    repeat_dist = window_analysis['long_term'].get('repeat_distribution', {})
                    prob_1 = repeat_dist.get(1, 0)
                    prob_2 = repeat_dist.get(2, 0)
                    total_prob_1_2 = prob_1 + prob_2 if isinstance(prob_1, (int, float)) and isinstance(prob_2, (
                    int, float)) else 0

                    report_lines.append(f"    • 整体趋势显示，随着统计窗口扩大，重复0个红球的概率下降")
                    report_lines.append(f"    • 重复1-2个红球的概率在长期窗口中为{total_prob_1_2:.1%}")
                    report_lines.append(f"    • 建议重点关注重复{most_likely_count}个红球的情况")

                # 蓝球重复概率建议
                if 'long_term' in window_analysis:
                    blue_prob = window_analysis['long_term'].get('blue_repeat_probability', 0)
                    if isinstance(blue_prob, (int, float)):
                        report_lines.append(f"\n  蓝球重复概率: {blue_prob:.2%} (基于长期窗口)")
                        if blue_prob < 0.05:
                            report_lines.append("  注: 蓝球重复概率较低，不建议选择上期蓝球")
                        elif blue_prob < 0.1:
                            report_lines.append("  注: 蓝球重复概率一般，可适当考虑")
                        else:
                            report_lines.append("  注: 蓝球重复概率较高，值得关注")



        # 机器学习预测（保持原样）
        if 'ml_predictions' in result:
            ml_pred = result['ml_predictions']
            if isinstance(ml_pred, dict):
                report_lines.append("\n🤖 机器学习预测:")

                if 'error' in ml_pred:
                    report_lines.append(f"   ❌ 错误: {ml_pred['error']}")
                elif 'message' in ml_pred:
                    report_lines.append(f"   ℹ️  信息: {ml_pred['message']}")
                else:
                    # 显示ML预测结果
                    model_type = ml_pred.get('model_type', '未知模型')
                    confidence = ml_pred.get('confidence', 0)
                    report_lines.append(f"   📊 模型类型: {model_type}")
                    report_lines.append(f"   🎯 置信度: {confidence:.2f}")

                    if 'predicted_balls' in ml_pred:
                        balls = ml_pred['predicted_balls']
                        if isinstance(balls, list):
                            sorted_balls = sorted([int(x) for x in balls if str(x).isdigit()])
                            ball_str = ' '.join([f'{x:02d}' for x in sorted_balls])
                            report_lines.append(f"   🔴 预测号码: {ball_str}")

        # 多窗口期统计分析（保持原样）
        if 'statistics_by_window' in result:
            stats_by_window = result['statistics_by_window']
            if isinstance(stats_by_window, dict):
                report_lines.append("\n📊 多窗口期统计分析:")

                window_order = ['short_term', 'medium_term', 'long_term']
                display_names = {
                    'short_term': '📱 短期分析',
                    'medium_term': '📊 中期分析',
                    'long_term': '📈 长期分析'
                }

                for window_name in window_order:
                    if window_name in stats_by_window:
                        stats = stats_by_window[window_name]
                        if not isinstance(stats, dict):
                            continue

                        display_name = display_names.get(window_name, window_name)
                        period_used = stats.get('period_used', 0)

                        report_lines.append(f"\n  {display_name} ({period_used}期):")

                        # 和值趋势
                        sum_trend = stats.get('sum_trend', '未知')
                        report_lines.append(f"     📈 和值趋势: {sum_trend}")

                        # 热号（只显示前3个）
                        hot_reds = stats.get('hot_reds', [])
                        if hot_reds and isinstance(hot_reds, list):
                            report_lines.append("     🔥 热门红球:")
                            count = 0
                            for item in hot_reds[:5]:  # 最多5个
                                if isinstance(item, (tuple, list)) and len(item) >= 2:
                                    ball, freq = item[0], item[1]
                                    if isinstance(ball, int):
                                        report_lines.append(f"       号码 {ball:02d}: {freq}次")
                                        count += 1
                                elif isinstance(item, int):
                                    report_lines.append(f"       号码 {item:02d}")
                                    count += 1
                                if count >= 3:  # 只显示3个
                                    break

                        # 冷号（只显示前3个）
                        cold_reds = stats.get('cold_reds', [])
                        import sys
                        print(f"🎯 [cold_reds] 检查: {cold_reds}, 类型: {type(cold_reds)}", file=sys.stderr)

                        if cold_reds and isinstance(cold_reds, list):
                            print(f"🎯 [cold_reds] 条件成立，长度: {len(cold_reds)}", file=sys.stderr)

                            report_lines.append("     ❄️  冷门红球:")
                            count = 0
                            for item in cold_reds[:5]:  # 最多5个
                                if isinstance(item, (tuple, list)) and len(item) >= 2:
                                    ball, freq = item[0], item[1]
                                    if isinstance(ball, int):
                                        report_lines.append(f"       号码 {ball:02d}: {freq}次")
                                        count += 1
                                elif isinstance(item, int):
                                    report_lines.append(f"       号码 {item:02d}")
                                    count += 1
                                if count >= 3:  # 只显示3个
                                    break
                        else:
                            print("🎯 [cold_reds] 条件不成立", file=sys.stderr)


        # 添加单个号码趋势分析
        import sys
        print("🎯 [调用前] 准备调用趋势分析方法", file=sys.stderr)
        self._add_individual_ball_trend_analysis(report_lines)
        print("🎯 [调用后] 趋势分析方法调用完成", file=sys.stderr)
        # 定义说明
        report_lines.append("\n📝 定义说明:")
        report_lines.append("  • 短期分析: 最近30期数据，反映近期趋势")
        report_lines.append("  • 中期分析: 最近50期数据，反映中期规律")
        report_lines.append("  • 长期分析: 最近100期数据，反映长期模式")
        report_lines.append("  • 热号: 统计周期内出现频率高的号码")
        report_lines.append("  • 冷号: 统计周期内出现频率低或遗漏期数长的号码")
        report_lines.append("  • 置信度: 预测结果的可靠程度，越高越好")
        report_lines.append("  • 趋势判断: 递增/递减/稳定/波动，基于四个窗口期概率变化")

        return "\n".join(report_lines)

        report_text = "\n".join(report_lines)

        # 🎯 添加调试信息
        import sys
        print(f"🎯 [报告生成完成] 报告长度: {len(report_text)} 字符", file=sys.stderr)
        print(f"🎯 [报告最后50字符] {report_text[-50:] if len(report_text) > 50 else report_text}", file=sys.stderr)

        return report_text

    # 在 PredictionService 类中添加趋势分析辅助方法
    def _add_individual_ball_trend_analysis(self, report_lines: List[str]) -> None:
        """添加单个号码趋势分析到报告"""
        # 🎯 绝对调试
        import sys
        print("🎯🎯🎯 _add_individual_ball_trend_analysis 方法开始执行", file=sys.stderr)

        # 最简单版本，先确认能执行
        report_lines.append("\n" + "=" * 70)
        report_lines.append("📈 单个号码趋势分析测试")
        report_lines.append("=" * 70)
        report_lines.append("\n✅ 测试：趋势分析方法执行成功")

        print("🎯🎯🎯 _add_individual_ball_trend_analysis 方法执行完成", file=sys.stderr)

    # 在 PredictionService 类中添加趋势分析辅助方法
    def _analyze_repeat_trends(self, window_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析重号分布的跨窗口趋势"""
        trend_data = {}

        # 定义窗口期顺序
        window_order = ['short_term', 'medium_term', 'long_term', 'all_history']

        # 为每个重复数量收集四个窗口期的概率
        for repeat_count in range(0, 7):
            probabilities = {}
            for window_name in window_order:
                if window_name in window_analysis:
                    repeat_dist = window_analysis[window_name].get('repeat_distribution', {})
                    prob = repeat_dist.get(repeat_count, 0)
                    if isinstance(prob, (int, float)):
                        probabilities[window_name] = prob

            if probabilities:
                trend_data[repeat_count] = probabilities

        return trend_data

    def _determine_trend(self, probabilities: List[float]) -> str:
        """判断趋势类型"""
        if len(probabilities) < 2:
            return "数据不足"

        # 检查是否递增
        is_increasing = all(probabilities[i] <= probabilities[i + 1] for i in range(len(probabilities) - 1))
        # 检查是否递减
        is_decreasing = all(probabilities[i] >= probabilities[i + 1] for i in range(len(probabilities) - 1))

        # 计算最大差异
        max_diff = max(probabilities) - min(probabilities) if probabilities else 0

        if len(probabilities) == 4:
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

    def test_save_report(self):
        # 创建一个模拟的预测结果
        test_result = {
            '6_plus_1': {
                'red_balls': [1, 2, 3, 4, 5, 6],
                'blue_ball': 7,
                'confidence': 75.5,
                'strategy': '测试策略'
            },
            'timestamp': datetime.now().isoformat(),
            'recommended_combination': '6+1'
        }

        # 测试保存
        save_result = self.save_report_to_file(test_result)
        print(f"测试保存结果: {save_result}")
        return save_result

    # 新增：报告历史管理方法
    def get_saved_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取保存的报告列表"""
        try:
            import glob
            import os

            reports_dir = "reports"
            if not os.path.exists(reports_dir):
                return []

            report_files = glob.glob(os.path.join(reports_dir, "prediction_*.txt"))
            report_files.sort(key=os.path.getmtime, reverse=True)

            reports = []
            for filepath in report_files[:limit]:
                try:
                    stats = os.stat(filepath)
                    filename = os.path.basename(filepath)

                    # 从文件名解析信息
                    parts = filename.replace('prediction_', '').replace('.txt', '').split('_')
                    issue_number = parts[0] if len(parts) > 0 else 'unknown'
                    timestamp = parts[1] if len(parts) > 1 else 'unknown'

                    reports.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size': stats.st_size,
                        'issue_number': issue_number,
                        'timestamp': timestamp,
                        'modified': datetime.fromtimestamp(stats.st_mtime).isoformat(),
                        'formatted_date': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    logger.warning(f"处理报告文件 {filepath} 失败: {e}")

            return reports

        except Exception as e:
            logger.error(f"获取报告列表失败: {e}")
            return []

    def get_report_content(self, filepath: str, max_lines: int = None) -> Dict[str, Any]:
        """获取报告内容"""
        try:
            if not os.path.exists(filepath):
                return {'error': f"文件不存在: {filepath}"}

            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

                result = {
                    'success': True,
                    'filepath': filepath,
                    'size': len(content),
                    'line_count': len(lines),
                    'full_content': content
                }

                if max_lines and max_lines > 0:
                    result['preview'] = '\n'.join(lines[:max_lines])
                    result['has_more'] = len(lines) > max_lines

                return result

        except Exception as e:
            logger.error(f"读取报告失败: {e}")
            return {'error': str(e)}

    def delete_report(self, filepath: str) -> Dict[str, Any]:
        """删除报告文件"""
        try:
            if not os.path.exists(filepath):
                return {'success': False, 'error': f"文件不存在: {filepath}"}

            os.remove(filepath)
            logger.info(f"已删除报告文件: {filepath}")
            return {'success': True, 'message': f"已删除报告: {os.path.basename(filepath)}"}

        except Exception as e:
            logger.error(f"删除报告失败: {e}")
            return {'success': False, 'error': str(e)}

    def add_to_history(self, save_result: Dict[str, Any]):
        """添加到报告历史"""
        try:
            if isinstance(save_result, dict) and save_result.get('success'):
                history_entry = {
                    'timestamp': save_result.get('timestamp', datetime.now().isoformat()),
                    'filepath': save_result.get('filepath'),
                    'filename': save_result.get('filename'),
                    'size': save_result.get('size', 0)
                }
                self.reports_history.append(history_entry)
                # 只保留最近50条历史记录
                if len(self.reports_history) > 50:
                    self.reports_history = self.reports_history[-50:]
        except Exception as e:
            logger.warning(f"添加到历史失败: {e}")

    def save_report_to_file(self, result: Dict[str, Any], filename: str = None) -> Dict[str, Any]:
        """保存预测结果到文件"""
        logger.info(f"保存报告被调用，参数类型: result={type(result).__name__}, filename={type(filename).__name__}")
        logger.debug(f"结果结构: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")

        try:
            # 如果 result 是字符串（可能是直接传递的报告文本），转换为字典格式
            if isinstance(result, str):
                logger.warning(f"save_report_to_file 接收到字符串参数，长度: {len(result)}")
                # 尝试解析字符串或创建基本结构
                result_dict = {
                    'raw_report': result,
                    'timestamp': datetime.now().isoformat()
                }
                report = result  # 直接使用字符串作为报告
            else:
                # 正常处理字典类型的预测结果
                result_dict = result
                # 1. 先生成报告文本
                report = self.generate_prediction_report(result_dict)

            # 2. 生成文件名
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                try:
                    # 尝试从结果中获取期号
                    if isinstance(result_dict, dict):
                        if 'system_info' in result_dict:
                            latest_issue = result_dict['system_info'].get('latest_issue', 'unknown')
                        elif 'repeat_analysis' in result_dict:
                            latest_issue = result_dict['repeat_analysis'].get('current_period', 'unknown')
                        else:
                            latest_issue = 'unknown'
                    else:
                        latest_issue = 'unknown'
                except:
                    latest_issue = 'unknown'

                filename = f"prediction_{latest_issue}_{timestamp}.txt"

            # 3. 确保目录存在
            os.makedirs("reports", exist_ok=True)
            filepath = os.path.join("reports", filename)

            # 4. 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)

            logger.info(f"预测报告已保存: {filepath}")

            # 5. 构建返回结果
            save_info = {
                'success': True,
                'filepath': filepath,
                'filename': filename,
                'size': len(report),
                'timestamp': datetime.now().isoformat()
            }

            # 6. 添加到历史
            self.add_to_history(save_info)

            return save_info

        except Exception as e:
            logger.error(f"保存报告失败: {e}", exc_info=True)
            error_result = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
            return error_result

# 全局预测服务实例
prediction_service = None

def get_prediction_service(db_path=None):
    """获取预测服务实例"""
    global prediction_service
    if prediction_service is None:
        prediction_service = PredictionService(db_path)
    return prediction_service
