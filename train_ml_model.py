# train_ml_model.py
"""
训练机器学习模型 - 集成配置系统
"""
import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ml_trainer')

def check_ml_dependencies():
    """检查ML依赖"""
    print("🔍 检查机器学习依赖...")
    
    required_libs = {
        'numpy': '用于数值计算',
        'pandas': '用于数据处理',
        'scikit-learn': '用于机器学习算法',
        'xgboost': '用于XGBoost算法（可选）',
        'lightgbm': '用于LightGBM算法（可选）'
    }
    
    missing = []
    installed = []
    
    for lib, desc in required_libs.items():
        try:
            __import__(lib)
            installed.append((lib, desc))
            print(f"  ✅ {lib:15} - {desc}")
        except ImportError:
            if lib in ['xgboost', 'lightgbm']:
                print(f"  ⚠️  {lib:15} - {desc} (可选)")
            else:
                missing.append(lib)
                print(f"  ❌ {lib:15} - {desc}")
    
    if missing:
        print(f"\n⚠️  缺少必要依赖: {missing}")
        print("安装命令:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print(f"\n✅ 所有依赖已安装 ({len(installed)}/{len(required_libs)})")
    return True

def train_ml_models():
    """训练机器学习模型"""
    print("\n🤖 开始训练机器学习模型...")
    
    try:
        # 1. 导入配置
        from config import config
        print(f"📋 使用配置: {config.system.APP_NAME} v{config.system.VERSION}")
        
        # 获取配置参数
        train_window = config.prediction.FEATURE_WINDOW  # 从prediction配置获取
        train_test_ratio = config.prediction.TRAIN_TEST_SPLIT
        random_state = 42
        
        print(f"📊 训练窗口: {train_window}期")
        print(f"📈 训练测试比例: {train_test_ratio}")
        
        # 2. 导入数据库
        from utils.db_manager import DatabaseManager
        db_manager = DatabaseManager()
        db = db_manager.get_db()
        
        # 获取数据
        total_records = db.get_record_count()
        print(f"📁 数据库记录: {total_records}期")
        
        if total_records < train_window * 2:
            print(f"⚠️  数据量不足，需要至少 {train_window * 2} 期数据")
            return False
        
        # 获取训练数据
        records = db.get_recent_records(train_window * 2)  # 获取双倍数据
        print(f"📊 使用 {len(records)} 期数据进行训练")
        
        # 3. 准备特征工程
        print("\n🔧 准备特征...")
        features, labels = prepare_features(records, train_window)
        
        if len(features) < 50:
            print("⚠️  有效特征数据不足")
            return False
        
        # 4. 训练各种模型
        results = {}
        
        # 随机森林
        if 'sklearn' in sys.modules:
            results['random_forest'] = train_random_forest(features, labels, train_test_ratio, random_state)
        
        # XGBoost
        if 'xgboost' in sys.modules:
            results['xgboost'] = train_xgboost(features, labels, train_test_ratio, random_state)
        
        # LightGBM
        if 'lightgbm' in sys.modules:
            results['lightgbm'] = train_lightgbm(features, labels, train_test_ratio, random_state)
        
        # 5. 保存模型
        print("\n💾 保存模型...")
        save_models(results)
        
        # 6. 更新配置
        update_model_config(results)
        
        return True
        
    except Exception as e:
        logger.error(f"训练失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def prepare_features(records, window_size):
    """准备特征数据"""
    import numpy as np
    
    features = []
    labels_red = []
    labels_blue = []
    
    for i in range(window_size, len(records)):
        # 使用前window_size期数据预测下一期
        window_records = records[i-window_size:i]
        next_record = records[i]
        
        # 特征：统计特征
        feature_vector = []
        
        # 1. 基础统计特征
        all_reds = []
        all_blues = []
        
        for record in window_records:
            all_reds.extend(record['red_balls'])
            all_blues.append(record['blue_ball'])
        
        # 红球频率
        red_counts = {}
        for red in all_reds:
            red_counts[red] = red_counts.get(red, 0) + 1
        
        # 添加红球频率特征
        for red in range(1, 34):
            feature_vector.append(red_counts.get(red, 0) / len(window_records))
        
        # 蓝球频率
        blue_counts = {}
        for blue in all_blues:
            blue_counts[blue] = blue_counts.get(blue, 0) + 1
        
        # 添加蓝球频率特征
        for blue in range(1, 17):
            feature_vector.append(blue_counts.get(blue, 0) / len(window_records))
        
        # 2. 最近一期特征
        latest = window_records[-1]
        latest_reds = latest['red_balls']
        latest_blue = latest['blue_ball']
        
        feature_vector.extend([
            sum(latest_reds),  # 和值
            max(latest_reds) - min(latest_reds),  # 跨度
            len([x for x in latest_reds if x <= 11]),  # 小号数量
            len([x for x in latest_reds if x % 2 == 0]),  # 偶数数量
            latest_blue,
            latest_blue % 2  # 蓝球奇偶
        ])
        
        features.append(feature_vector)
        
        # 标签：下一期的红球（第一个）和蓝球
        labels_red.append(next_record['red_balls'][0])
        labels_blue.append(next_record['blue_ball'])
    
    return np.array(features), {
        'red': np.array(labels_red),
        'blue': np.array(labels_blue)
    }

def train_random_forest(features, labels, test_ratio, random_state):
    """训练随机森林模型"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    
    print("🌲 训练随机森林模型...")
    
    # 红球预测
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels['red'], test_size=test_ratio, random_state=random_state
    )
    
    model_red = RandomForestClassifier(n_estimators=100, random_state=random_state)
    model_red.fit(X_train, y_train)
    
    accuracy_red = model_red.score(X_test, y_test)
    
    # 蓝球预测
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels['blue'], test_size=test_ratio, random_state=random_state
    )
    
    model_blue = RandomForestClassifier(n_estimators=100, random_state=random_state)
    model_blue.fit(X_train, y_train)
    
    accuracy_blue = model_blue.score(X_test, y_test)
    
    print(f"  ✅ 红球准确率: {accuracy_red:.3f}")
    print(f"  ✅ 蓝球准确率: {accuracy_blue:.3f}")
    
    return {
        'model_red': model_red,
        'model_blue': model_blue,
        'accuracy_red': accuracy_red,
        'accuracy_blue': accuracy_blue,
        'feature_count': features.shape[1]
    }

def train_xgboost(features, labels, test_ratio, random_state):
    """训练XGBoost模型"""
    try:
        import xgboost as xgb
        from sklearn.model_selection import train_test_split
        
        print("⚡ 训练XGBoost模型...")
        
        # 红球预测
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels['red'], test_size=test_ratio, random_state=random_state
        )
        
        model_red = xgb.XGBClassifier(n_estimators=100, random_state=random_state)
        model_red.fit(X_train, y_train)
        
        accuracy_red = model_red.score(X_test, y_test)
        
        # 蓝球预测
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels['blue'], test_size=test_ratio, random_state=random_state
        )
        
        model_blue = xgb.XGBClassifier(n_estimators=100, random_state=random_state)
        model_blue.fit(X_train, y_train)
        
        accuracy_blue = model_blue.score(X_test, y_test)
        
        print(f"  ✅ 红球准确率: {accuracy_red:.3f}")
        print(f"  ✅ 蓝球准确率: {accuracy_blue:.3f}")
        
        return {
            'model_red': model_red,
            'model_blue': model_blue,
            'accuracy_red': accuracy_red,
            'accuracy_blue': accuracy_blue
        }
    except Exception as e:
        print(f"  ⚠️  XGBoost训练失败: {e}")
        return None

def train_lightgbm(features, labels, test_ratio, random_state):
    """训练LightGBM模型"""
    try:
        import lightgbm as lgb
        from sklearn.model_selection import train_test_split
        
        print("💡 训练LightGBM模型...")
        
        # 红球预测
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels['red'], test_size=test_ratio, random_state=random_state
        )
        
        model_red = lgb.LGBMClassifier(n_estimators=100, random_state=random_state)
        model_red.fit(X_train, y_train)
        
        accuracy_red = model_red.score(X_test, y_test)
        
        # 蓝球预测
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels['blue'], test_size=test_ratio, random_state=random_state
        )
        
        model_blue = lgb.LGBMClassifier(n_estimators=100, random_state=random_state)
        model_blue.fit(X_train, y_train)
        
        accuracy_blue = model_blue.score(X_test, y_test)
        
        print(f"  ✅ 红球准确率: {accuracy_red:.3f}")
        print(f"  ✅ 蓝球准确率: {accuracy_blue:.3f}")
        
        return {
            'model_red': model_red,
            'model_blue': model_blue,
            'accuracy_red': accuracy_red,
            'accuracy_blue': accuracy_blue
        }
    except Exception as e:
        print(f"  ⚠️  LightGBM训练失败: {e}")
        return None

def save_models(results):
    """保存训练好的模型"""
    import pickle
    import json
    
    os.makedirs('models', exist_ok=True)
    
    model_info = {
        'trained_at': datetime.now().isoformat(),
        'models': {}
    }
    
    for model_name, result in results.items():
        if result is None:
            continue
            
        # 保存模型文件
        model_path = os.path.join('models', f'{model_name}_model.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(result, f)
        
        # 记录模型信息
        model_info['models'][model_name] = {
            'accuracy_red': float(result.get('accuracy_red', 0)),
            'accuracy_blue': float(result.get('accuracy_blue', 0)),
            'feature_count': result.get('feature_count', 0),
            'model_file': f'{model_name}_model.pkl'
        }
        
        print(f"  💾 {model_name:15} 已保存")
    
    # 保存模型元数据
    metadata_path = os.path.join('models', 'model_metadata.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(model_info, f, indent=2, ensure_ascii=False)
    
    print(f"  📄 模型元数据已保存")

def update_model_config(results):
    """更新模型配置"""
    try:
        from config import config
        
        # 找到最佳模型
        best_model = None
        best_accuracy = 0
        
        for model_name, result in results.items():
            if result and 'accuracy_red' in result:
                accuracy = result['accuracy_red']
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_model = model_name
        
        if best_model:
            print(f"\n🏆 最佳模型: {best_model} (准确率: {best_accuracy:.3f})")
            
            # 这里可以更新配置，但config可能是只读的
            # 我们创建一个单独的配置文件
            config_data = {
                'best_model': best_model,
                'best_accuracy': best_accuracy,
                'last_trained': datetime.now().isoformat()
            }
            
            config_path = os.path.join('models', 'ml_config.json')
            import json
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            print(f"  📋 ML配置已更新: {config_path}")
    except Exception as e:
        print(f"  ⚠️  更新配置失败: {e}")

if __name__ == "__main__":
    from datetime import datetime
    
    print("=" * 60)
    print("🤖 双色球机器学习模型训练 (集成配置版)")
    print("=" * 60)
    
    # 检查依赖
    if not check_ml_dependencies():
        print("\n❌ 请先安装缺失的依赖")
        sys.exit(1)
    
    # 训练模型
    success = train_ml_models()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 训练完成！")
        print("\n下一步:")
        print("1. 运行 python test_ml.py 测试ML预测")
        print("2. 在 prediction_service.py 中启用ML预测")
        print("3. 查看 models/ 目录中的模型文件")
    else:
        print("❌ 训练失败")
        print("\n可能的原因:")
        print("1. 数据量不足")
        print("2. 特征工程失败")
        print("3. 模型训练错误")
    
    print("=" * 60)