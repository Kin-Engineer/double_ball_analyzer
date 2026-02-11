# workflows/prediction_workflow.py
"""
预测工作流程
"""
import logging
from typing import Dict, Any

from data.predictor import EnhancedPredictor
from data.database import DoubleBallDatabase
from utils.color_utils import print_info, print_success, print_warning

logger = logging.getLogger('prediction_workflow')

def run_prediction_workflow(db_path: str = "double_ball.db") -> Dict[str, Any]:
    """运行预测工作流程"""
    print_info("开始预测工作流程...")
    
    try:
        db = DoubleBallDatabase(db_path)
        predictor = EnhancedPredictor(db)
        
        # 检查数据量
        record_count = db.get_record_count()
        if record_count < 30:
            print_warning(f"数据量较少 ({record_count} 条)，预测准确性可能受影响")
        
        # 运行预测
        predictions = predictor.predict_all_combinations()
        
        # 分析结果
        result = {
            'predictions': predictions,
            'data_stats': {
                'record_count': record_count,
                'latest_issue': db.get_latest_issue()
            }
        }
        
        print_success("预测工作流程完成")
        return result
        
    except Exception as e:
        logger.error(f"预测工作流程失败: {e}")
        return {'error': str(e)}