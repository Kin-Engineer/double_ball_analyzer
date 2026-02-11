# workflows/data_pipeline.py
"""
数据处理流程
"""
import logging
from typing import Dict, Any

from data.crawler import DoubleBallCrawler
from data.database import DoubleBallDatabase
from data.processor import processor
from data.advanced_processor import advanced_processor
from utils.color_utils import print_info, print_success, print_error

logger = logging.getLogger('data_pipeline')

def run_data_pipeline(db_path: str = "double_ball.db", force_update: bool = False) -> Dict[str, Any]:
    """运行数据处理流程"""
    print_info("开始数据处理流程...")
    
    try:
        db = DoubleBallDatabase(db_path)
        crawler = DoubleBallCrawler(db)
        
        # 1. 数据同步
        logger.info("步骤1: 数据同步")
        sync_result = crawler.sync_all_data_incremental(force_update)
        print_info(f"数据同步完成: {sync_result.get('new_records', 0)} 条新记录")
        
        # 2. 获取数据
        logger.info("步骤2: 获取数据")
        records = db.get_all_records()
        print_info(f"获取到 {len(records)} 条记录")
        
        # 3. 基础处理
        logger.info("步骤3: 基础数据处理")
        processed_records = processor.process_records(records)
        print_info(f"基础处理完成: {len(processed_records)} 条记录")
        
        # 4. 高级处理
        logger.info("步骤4: 高级特征处理")
        advanced_records = advanced_processor.process_all_features(processed_records)
        print_info(f"高级处理完成: {len(advanced_records)} 条记录")
        
        # 5. 保存处理后的数据（这里可以保存到新表或更新原表）
        # 实际应用中可能需要保存处理后的特征
        
        result = {
            'sync_result': sync_result,
            'total_records': len(records),
            'processed_records': len(processed_records),
            'advanced_processed': len(advanced_records)
        }
        
        print_success("数据处理流程完成")
        return result
        
    except Exception as e:
        logger.error(f"数据处理流程失败: {e}")
        return {'error': str(e)}