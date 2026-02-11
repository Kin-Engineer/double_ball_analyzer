# workflows/full_analysis.py
"""
完整分析流程
"""
import logging
from datetime import datetime

from core.unified_analyzer import UnifiedAnalyzer
from utils.color_utils import print_success, print_warning, print_info
from utils.logger import logger

def run_full_analysis_workflow(db_path: str = "double_ball.db") -> dict:
    """运行完整分析流程"""
    print_info("开始完整分析流程...")
    
    try:
        # 初始化分析器
        analyzer = UnifiedAnalyzer(db_path)
        
        # 1. 数据检查
        logger.info("步骤1: 数据检查")
        db_info = analyzer.analyzer.db.get_database_info()
        print_info(f"数据库记录数: {db_info.get('record_count', 0)}")
        
        if db_info.get('record_count', 0) < 50:
            print_warning("数据量较少，建议先同步数据")
        
        # 2. 统计分析
        logger.info("步骤2: 统计分析")
        analysis = analyzer.run_analysis_only()
        
        # 3. 预测分析
        logger.info("步骤3: 预测分析")
        predictions = analyzer.run_prediction_only()
        
        # 4. 可视化
        logger.info("步骤4: 生成可视化")
        viz_success = analyzer.generate_visual_report("reports")
        
        # 5. 生成报告
        logger.info("步骤5: 生成报告")
        report = {
            'analysis': analysis,
            'predictions': predictions,
            'visualization_success': viz_success,
            'database_info': db_info,
            'generated_at': datetime.now().isoformat()
        }
        
        print_success("完整分析流程完成")
        return report
        
    except Exception as e:
        logger.error(f"完整分析流程失败: {e}")
        return {'error': str(e)}