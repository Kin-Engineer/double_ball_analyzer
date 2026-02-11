# services/model_training.py - 完整修复版本
"""
模型训练服务 - 修复版本
修复XGBoost标签编码、LightGBM版本兼容性、统计模型算法
"""
import logging
import pickle
import os
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from collections import Counter

from data.database import DoubleBallDatabase
from utils.db_manager import DatabaseManager

logger = logging.getLogger('model_training')

@dataclass
class TrainingConfig:
    """训练配置"""
    train_ratio: float = 0.8
    validation_ratio: float = 0.1
    test_ratio: float = 0.1
    random_state: int = 42
    n_estimators: int = 100
    max_depth: int = 6
    learning_rate: float = 0.1

class ModelTrainingService:
    """模型训练服务 - 修复版本"""
    
    def __init__(self, db_path: str = None):
        self.db_manager = DatabaseManager()
        
        if db_path is None:
            from config import config
            db_path = config.paths.DATABASE_PATH
        
        self.db = self.db_manager.get_db(db_path)
        self.config = TrainingConfig()
        
        # 模型存储路径
        self.models_dir = "models"
        os.makedirs(self.models_dir, exist_ok=True)
        
        logger.info("模型训练服务初始化完成")
    
    def prepare_training_data(self, window_size: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据
        
        Args:
            window_size: 使用的历史期数
            
        Returns:
            X: 特征矩阵
            y: 标签
        """
        try:
            # 获取数据
            records = self.db.get_recent_records(window_size)
            if len(records) < 10:
                logger.warning(f"数据不足，只有 {len(records)} 条记录")
                return None, None
            
            # 转换为特征矩阵
            features = []
            labels_red = []
            labels_blue = []
            
            for i in range(len(records) - 1):
                current = records[i]
                next_record = records[i + 1]
                
                # 特征：当前期的红球和蓝球
                red_features = [
                    current.red1, current.red2, current.red3,
                    current.red4, current.red5, current.red6
                ]
                blue_feature = [current.blue]
                
                # 添加统计特征
                red_sum = sum(red_features)
                red_avg = red_sum / 6
                red_std = np.std(red_features)
                odd_count = sum(1 for x in red_features if x % 2 == 1)
                
                # 组合特征
                feature_vector = red_features + blue_feature + [
                    red_sum, red_avg, red_std, odd_count,
                    i % 7,  # 星期几的简单表示
                    len(records) - i  # 时间衰减
                ]
                
                features.append(feature_vector)
                
                # 标签：下期的红球和蓝球
                labels_red.append([
                    next_record.red1, next_record.red2, next_record.red3,
                    next_record.red4, next_record.red5, next_record.red6
                ])
                labels_blue.append([next_record.blue])
            
            X = np.array(features, dtype=np.float32)
            y_red = np.array(labels_red, dtype=np.int32)
            y_blue = np.array(labels_blue, dtype=np.int32)
            
            logger.info(f"数据准备完成: X.shape={X.shape}, y_red.shape={y_red.shape}")
            return X, (y_red, y_blue)
            
        except Exception as e:
            logger.error(f"准备训练数据失败: {e}", exc_info=True)
            return None, None
    
    def train_xgboost_model(self, X: np.ndarray, y_red: np.ndarray, y_blue: np.ndarray) -> Dict[str, Any]:
        """训练XGBoost模型 - 使用DMatrix API避免标签检查问题"""
        try:
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
            
            logger.info(f"开始训练XGBoost模型，数据形状: X={X.shape}, y_red={y_red.shape}, y_blue={y_blue.shape}")
            
            # 编码标签
            y_red_encoded = y_red - 1  # 1-33 -> 0-32
            y_blue_encoded = y_blue.ravel() - 1  # 1-16 -> 0-15
            
            # 使用分层抽样确保蓝球分布均匀
            X_train, X_test, y_red_train_encoded, y_red_test_encoded, y_blue_train_encoded, y_blue_test_encoded = train_test_split(
                X, y_red_encoded, y_blue_encoded, 
                test_size=0.2, 
                random_state=self.config.random_state,
                stratify=y_blue_encoded  # 🔧 关键：按蓝球分层抽样
            )
            
            logger.info(f"训练集: {X_train.shape[0]}条, 测试集: {X_test.shape[0]}条")
            logger.info(f"训练集蓝球标签: {sorted(np.unique(y_blue_train_encoded))}")
            logger.info(f"测试集蓝球标签: {sorted(np.unique(y_blue_test_encoded))}")
            
            # 解码用于评估
            y_red_test = y_red_test_encoded + 1
            y_blue_test = y_blue_test_encoded + 1
            
            # 训练红球模型
            red_models = []
            red_accuracies = []
            
            for i in range(6):
                y_train_single_encoded = y_red_train_encoded[:, i]
                y_test_single_encoded = y_red_test_encoded[:, i]
                y_test_single = y_red_test[:, i]
                
                # 🔧 使用DMatrix直接训练，避免sklearn wrapper的类别检查
                dtrain = xgb.DMatrix(X_train, label=y_train_single_encoded)
                dtest = xgb.DMatrix(X_test, label=y_test_single_encoded)
                
                params = {
                    'objective': 'multi:softmax',
                    'num_class': 33,
                    'max_depth': self.config.max_depth,
                    'eta': self.config.learning_rate,
                    'seed': self.config.random_state,
                    'verbosity': 0,
                    'eval_metric': 'merror'
                }
                
                # 训练模型
                model = xgb.train(
                    params=params,
                    dtrain=dtrain,
                    num_boost_round=self.config.n_estimators,
                    evals=[(dtrain, 'train'), (dtest, 'eval')],
                    early_stopping_rounds=10,
                    verbose_eval=False
                )
                
                # 预测
                y_pred_encoded = model.predict(dtest).astype(int)
                y_pred = y_pred_encoded + 1
                
                accuracy = accuracy_score(y_test_single, y_pred)
                
                red_models.append(model)
                red_accuracies.append(accuracy)
                
                logger.info(f"红球位置 {i+1} 模型准确率: {accuracy:.4f}")
            
            # 训练蓝球模型
            dtrain_blue = xgb.DMatrix(X_train, label=y_blue_train_encoded)
            dtest_blue = xgb.DMatrix(X_test, label=y_blue_test_encoded)
            
            params_blue = {
                'objective': 'multi:softmax',
                'num_class': 16,
                'max_depth': self.config.max_depth,
                'eta': self.config.learning_rate,
                'seed': self.config.random_state,
                'verbosity': 0,
                'eval_metric': 'merror'
            }
            
            blue_model = xgb.train(
                params=params_blue,
                dtrain=dtrain_blue,
                num_boost_round=self.config.n_estimators,
                evals=[(dtrain_blue, 'train'), (dtest_blue, 'eval')],
                early_stopping_rounds=10,
                verbose_eval=False
            )
            
            y_blue_pred_encoded = blue_model.predict(dtest_blue).astype(int)
            y_blue_pred = y_blue_pred_encoded + 1
            
            blue_accuracy = accuracy_score(y_blue_test, y_blue_pred)
            logger.info(f"蓝球模型准确率: {blue_accuracy:.4f}")
            
            # 保存模型
            model_info = {
                'red_models': red_models,
                'blue_model': blue_model,
                'red_accuracies': red_accuracies,
                'blue_accuracy': blue_accuracy,
                'train_size': X_train.shape[0],
                'test_size': X_test.shape[0],
                'feature_count': X.shape[1],
                'train_time': datetime.now().isoformat(),
                'model_type': 'xgboost_dmatrix'
            }
            
            model_path = os.path.join(self.models_dir, "xgboost_model.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model_info, f)
            
            logger.info(f"XGBoost模型已保存到: {model_path}")
            return model_info
            
        except ImportError:
            logger.error("XGBoost未安装，请运行: pip install xgboost")
            return {'error': 'XGBoost未安装'}
        except Exception as e:
            logger.error(f"训练XGBoost模型失败: {e}", exc_info=True)
            return {'error': str(e)}

    def train_lightgbm_model(self, X: np.ndarray, y_red: np.ndarray, y_blue: np.ndarray) -> Dict[str, Any]:
        """训练LightGBM模型 - 使用原生API避免sklearn兼容性问题"""
        try:
            import lightgbm as lgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score
            import warnings
            warnings.filterwarnings('ignore')

            logger.info(f"开始训练LightGBM模型，数据形状: X={X.shape}, y_red={y_red.shape}, y_blue={y_blue.shape}")

            # 编码标签
            y_red_encoded = y_red - 1
            y_blue_encoded = y_blue.ravel() - 1

            # 使用分层抽样确保蓝球分布均匀
            X_train, X_test, y_red_train_encoded, y_red_test_encoded, y_blue_train_encoded, y_blue_test_encoded = train_test_split(
                X, y_red_encoded, y_blue_encoded,
                test_size=0.2,
                random_state=self.config.random_state,
                stratify=y_blue_encoded
            )

            # 解码用于评估
            y_red_test = y_red_test_encoded + 1
            y_blue_test = y_blue_test_encoded + 1

            # 🔧 使用LightGBM原生Dataset API
            red_models = []
            red_accuracies = []

            # 创建数据集
            train_data = lgb.Dataset(X_train)
            test_data = lgb.Dataset(X_test, reference=train_data)

            for i in range(6):
                y_train_single_encoded = y_red_train_encoded[:, i]
                y_test_single = y_red_test[:, i]

                # 设置标签
                train_data.set_label(y_train_single_encoded)

                # 参数配置
                params = {
                    'objective': 'multiclass',
                    'num_class': 33,
                    'num_leaves': 31,
                    'learning_rate': self.config.learning_rate,
                    'feature_fraction': 0.8,
                    'bagging_fraction': 0.8,
                    'bagging_freq': 5,
                    'verbose': -1,
                    'seed': self.config.random_state
                }

                # 训练模型
                model = lgb.train(
                    params,
                    train_data,
                    num_boost_round=self.config.n_estimators,
                    valid_sets=[test_data],
                    callbacks=[lgb.log_evaluation(0)]  # 不显示日志
                )

                # 预测
                y_pred_encoded = model.predict(X_test, num_iteration=model.best_iteration)
                y_pred = np.argmax(y_pred_encoded, axis=1) + 1

                accuracy = accuracy_score(y_test_single, y_pred)

                red_models.append(model)
                red_accuracies.append(accuracy)

                logger.info(f"LightGBM红球位置 {i + 1} 模型准确率: {accuracy:.4f}")

            # 训练蓝球模型
            train_data_blue = lgb.Dataset(X_train, label=y_blue_train_encoded)
            test_data_blue = lgb.Dataset(X_test, label=y_blue_test_encoded, reference=train_data_blue)

            params_blue = {
                'objective': 'multiclass',
                'num_class': 16,
                'num_leaves': 31,
                'learning_rate': self.config.learning_rate,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'seed': self.config.random_state
            }

            blue_model = lgb.train(
                params_blue,
                train_data_blue,
                num_boost_round=self.config.n_estimators,
                valid_sets=[test_data_blue],
                callbacks=[lgb.log_evaluation(0)]
            )

            y_blue_pred_encoded = blue_model.predict(X_test, num_iteration=blue_model.best_iteration)
            y_blue_pred = np.argmax(y_blue_pred_encoded, axis=1) + 1

            blue_accuracy = accuracy_score(y_blue_test, y_blue_pred)
            logger.info(f"LightGBM蓝球模型准确率: {blue_accuracy:.4f}")

            # 保存模型
            model_info = {
                'red_models': red_models,
                'blue_model': blue_model,
                'red_accuracies': red_accuracies,
                'blue_accuracy': blue_accuracy,
                'model_type': 'lightgbm_native',
                'train_time': datetime.now().isoformat(),
                'label_encoding': '1-based_to_0-based'
            }

            model_path = os.path.join(self.models_dir, "lightgbm_model.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model_info, f)

            logger.info(f"LightGBM模型已保存到: {model_path}")
            return model_info

        except ImportError:
            logger.error("LightGBM未安装，请运行: pip install lightgbm")
            return {'error': 'LightGBM未安装'}
        except Exception as e:
            logger.error(f"训练LightGBM模型失败: {e}", exc_info=True)
            return {'error': str(e)}
    
    def train_statistical_model(self) -> Dict[str, Any]:
        """训练统计模型（基于频率分析）- 修复热冷号算法"""
        try:
            # 获取历史数据
            records = self.db.get_all_records()
            if len(records) < 50:
                logger.warning("数据不足，无法训练统计模型")
                return {'error': '数据不足'}
            
            # 统计红球频率 - 🔧 使用已导入的Counter
            red_counts = Counter()
            blue_counts = Counter()
            
            for record in records:
                reds = [record.red1, record.red2, record.red3,
                       record.red4, record.red5, record.red6]
                
                for ball in reds:
                    red_counts[ball] = red_counts.get(ball, 0) + 1
                
                blue_counts[record.blue] = blue_counts.get(record.blue, 0) + 1
            
            total_games = len(records)
            
            # 计算理论平均出现次数
            theoretical_red_freq = total_games * 6 / 33
            
            # 🔧 修复：使用实际统计排名
            sorted_reds = red_counts.most_common()
            
            # 取前33%作为热号（大约11个号码）
            hot_count = max(1, int(len(sorted_reds) * 0.33))
            hot_reds = [ball for ball, _ in sorted_reds[:hot_count]]
            
            # 取后33%作为冷号
            cold_count = max(1, int(len(sorted_reds) * 0.33))
            cold_reds = [ball for ball, _ in sorted_reds[-cold_count:]]
            
            # 温号是中间的部分
            warm_reds = []
            if len(sorted_reds) > (hot_count + cold_count):
                warm_reds = [ball for ball, _ in sorted_reds[hot_count:-cold_count]]
            
            # 计算概率
            red_probabilities = {
                ball: count / (total_games * 6)
                for ball, count in red_counts.items()
            }
            
            blue_probabilities = {
                ball: count / total_games
                for ball, count in blue_counts.items()
            }
            
            # 获取最热门的10个红球和最冷门的10个红球
            hot_reds_top10 = [ball for ball, _ in sorted_reds[:10]]
            cold_reds_top10 = [ball for ball, _ in sorted_reds[-10:]]
            
            model_info = {
                'red_probabilities': red_probabilities,
                'blue_probabilities': blue_probabilities,
                'hot_reds': hot_reds,
                'warm_reds': warm_reds,
                'cold_reds': cold_reds,
                'hot_reds_top10': hot_reds_top10,
                'cold_reds_top10': cold_reds_top10,
                'total_games': total_games,
                'model_type': 'statistical',
                'train_time': datetime.now().isoformat(),
                'classification_method': 'ranking_top_bottom_33_percent',
                'red_counts_dict': dict(red_counts),
                'blue_counts_dict': dict(blue_counts)
            }
            
            # 保存模型
            model_path = os.path.join(self.models_dir, "statistical_model.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model_info, f)
            
            logger.info(f"统计模型已保存到: {model_path}")
            logger.info(f"热号: {len(hot_reds)}个, 温号: {len(warm_reds)}个, 冷号: {len(cold_reds)}个")
            logger.info(f"热门红球TOP10: {hot_reds_top10}")
            logger.info(f"冷门红球TOP10: {cold_reds_top10}")
            return model_info
            
        except Exception as e:
            logger.error(f"训练统计模型失败: {e}", exc_info=True)
            return {'error': str(e)}
    
    def train_all_models(self, window_size: int = 200) -> Dict[str, Any]:
        """训练所有模型"""
        try:
            # 准备数据
            X, (y_red, y_blue) = self.prepare_training_data(window_size)
            if X is None:
                return {'error': '无法准备训练数据'}
            
            results = {}
            
            # 训练XGBoost模型
            logger.info("开始训练XGBoost模型...")
            xgb_result = self.train_xgboost_model(X, y_red, y_blue)
            results['xgboost'] = xgb_result
            
            # 训练LightGBM模型
            logger.info("开始训练LightGBM模型...")
            lgb_result = self.train_lightgbm_model(X, y_red, y_blue)
            results['lightgbm'] = lgb_result
            
            # 训练统计模型
            logger.info("开始训练统计模型...")
            stats_result = self.train_statistical_model()
            results['statistical'] = stats_result
            
            # 生成训练报告
            report = self.generate_training_report(results)
            
            logger.info("所有模型训练完成")
            return {
                'success': True,
                'results': results,
                'report': report,
                'total_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"训练所有模型失败: {e}", exc_info=True)
            return {'error': str(e)}
    
    def generate_training_report(self, results: Dict[str, Any]) -> str:
        """生成训练报告"""
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("模型训练报告")
        report_lines.append("=" * 60)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for model_name, result in results.items():
            report_lines.append(f"\n📊 {model_name.upper()} 模型:")
            
            if 'error' in result:
                report_lines.append(f"  状态: 失败 - {result['error']}")
                continue
            
            report_lines.append(f"  状态: 成功")
            
            if model_name in ['xgboost', 'lightgbm']:
                red_accuracies = result.get('red_accuracies', [])
                blue_accuracy = result.get('blue_accuracy', 0)
                
                if red_accuracies:
                    avg_red_accuracy = sum(red_accuracies) / len(red_accuracies)
                    report_lines.append(f"  红球平均准确率: {avg_red_accuracy:.4f}")
                    report_lines.append(f"  蓝球准确率: {blue_accuracy:.4f}")
                    
                    for i, acc in enumerate(red_accuracies):
                        report_lines.append(f"    位置{i+1}: {acc:.4f}")
            
            elif model_name == 'statistical':
                hot_reds = result.get('hot_reds', [])
                warm_reds = result.get('warm_reds', [])
                cold_reds = result.get('cold_reds', [])
                total_games = result.get('total_games', 0)
                
                report_lines.append(f"  基于数据: {total_games} 期")
                report_lines.append(f"  热号数量: {len(hot_reds)} 个")
                report_lines.append(f"  温号数量: {len(warm_reds)} 个")
                report_lines.append(f"  冷号数量: {len(cold_reds)} 个")
                
                hot_top10 = result.get('hot_reds_top10', [])
                cold_top10 = result.get('cold_reds_top10', [])
                if hot_top10:
                    report_lines.append(f"  热门红球TOP10: {sorted(hot_top10)}")
                if cold_top10:
                    report_lines.append(f"  冷门红球TOP10: {sorted(cold_top10)}")
        
        report_lines.append(f"\n💡 说明:")
        report_lines.append("  • 准确率基于测试集计算")
        report_lines.append("  • 统计模型基于频率分析")
        report_lines.append("  • 机器学习模型基于历史数据训练")
        report_lines.append("  • 热/温/冷号按出现频率排名前/中/后33%划分")
        
        return "\n".join(report_lines)
    
    def load_model(self, model_type: str = "xgboost") -> Dict[str, Any]:
        """加载训练好的模型"""
        try:
            model_files = {
                'xgboost': 'xgboost_model.pkl',
                'lightgbm': 'lightgbm_model.pkl',
                'statistical': 'statistical_model.pkl'
            }
            
            if model_type not in model_files:
                logger.error(f"未知的模型类型: {model_type}")
                return {'error': f'未知的模型类型: {model_type}'}
            
            model_path = os.path.join(self.models_dir, model_files[model_type])
            
            if not os.path.exists(model_path):
                logger.error(f"模型文件不存在: {model_path}")
                return {'error': f'模型文件不存在: {model_path}'}
            
            with open(model_path, 'rb') as f:
                model_info = pickle.load(f)
            
            logger.info(f"加载模型成功: {model_type}")
            return {'success': True, 'model_info': model_info}
            
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return {'error': str(e)}
    
    def get_model_status(self) -> Dict[str, Any]:
        """获取模型状态"""
        model_status = {}
        
        for model_name in ['xgboost', 'lightgbm', 'statistical']:
            model_path = os.path.join(self.models_dir, f"{model_name}_model.pkl")
            
            if os.path.exists(model_path):
                try:
                    with open(model_path, 'rb') as f:
                        model_info = pickle.load(f)
                    
                    model_status[model_name] = {
                        'exists': True,
                        'size': os.path.getsize(model_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(model_path)),
                        'info': model_info.get('model_type', model_name),
                        'train_time': model_info.get('train_time', '未知')
                    }
                except Exception as e:
                    model_status[model_name] = {'exists': True, 'error': f'无法读取: {str(e)}'}
            else:
                model_status[model_name] = {'exists': False}
        
        return model_status

# 全局模型训练服务实例
model_training_service = None

def get_model_training_service(db_path=None):
    """获取模型训练服务实例"""
    global model_training_service
    if model_training_service is None:
        model_training_service = ModelTrainingService(db_path)
    return model_training_service