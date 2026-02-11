"""
data_sync.py
数据同步模块 - 从网站获取最新数据
"""
import logging
import sys
import os
import time
from datetime import datetime
import argparse

# 添加项目根目录到路径
sys.path.append('.')

# 导入 config 以获取默认数据库路径
try:
    from config import config
    DEFAULT_DB_PATH = config.paths.DATABASE_PATH
except ImportError:
    DEFAULT_DB_PATH = "double_ball.db"  # 兼容性回退

from data.crawler import DoubleBallCrawler
from data.database import DoubleBallDatabase
from utils.logger import setup_logger

# 设置全局日志记录器
logger = setup_logger("data_sync")

def sync_data(db_path: str = None) -> bool:
    """同步数据"""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
        
    try:
        logger.info(f"开始数据同步，使用数据库: {db_path}")

        # 初始化数据库，指定路径
        db = DoubleBallDatabase(db_path)

        # 获取当前数据量
        current_count = db.get_record_count()
        logger.info(f"当前数据量: {current_count} 条记录")

        # 初始化爬虫
        crawler = DoubleBallCrawler(db)  # 传入数据库实例

        # 获取最新数据 - 使用增量同步方法
        logger.info("正在获取最新数据...")
        result = crawler.sync_all_data_incremental(force_update=False)

        new_records = result.get('new_records', 0)
        total_records = result.get('total_records', 0)

        if new_records == 0:
            logger.info("未获取到新数据，数据已是最新")
            return True  # 没有新数据也是成功状态

        logger.info(f"获取到 {new_records} 条新记录")

        # 检查数据完整性
        new_count = db.get_record_count()
        total_added = new_count - current_count

        if total_added > 0:
            logger.info(f"数据同步完成，新增 {total_added} 条记录")
            logger.info(f"当前总数据量: {new_count} 条记录")

            # 获取统计信息
            stats = db.get_statistics()
            logger.info(f"数据库统计信息: 总记录数={stats.get('total_records', 0)}, "
                       f"数据范围={stats.get('date_range', '未知')}")
            return True
        else:
            logger.warning("数据库记录数未增加，可能数据已存在")
            return True  # 即使没有新增数据，同步过程也是成功的

    except Exception as e:
        logger.error(f"数据同步失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

def sync_with_retry(db_path: str = None, max_retries: int = 3, retry_interval: int = 10) -> bool:
    """带重试的数据同步"""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
        
    success_count = 0
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"尝试第 {attempt} 次数据同步...")

            if sync_data(db_path):
                success_count += 1
                logger.info(f"第 {attempt} 次同步成功")
                # 如果成功，可以提前结束
                break
            else:
                logger.warning(f"第 {attempt} 次同步失败")

            if attempt < max_retries:
                logger.info(f"等待 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)

        except KeyboardInterrupt:
            logger.info("用户中断同步")
            break
        except Exception as e:
            logger.error(f"同步过程中发生未知错误: {e}")
            if attempt < max_retries:
                logger.info(f"等待 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)

    # 总结
    if success_count > 0:
        logger.info("✅ 数据同步成功完成")
        return True
    else:
        logger.error("❌ 数据同步失败")
        return False

if __name__ == "__main__":
    """命令行入口"""
    parser = argparse.ArgumentParser(description="双色球数据同步工具")
    parser.add_argument("--db", type=str, default=DEFAULT_DB_PATH, 
                       help=f"数据库路径 (默认: {DEFAULT_DB_PATH})")
    parser.add_argument("--retry", type=int, default=3, help="最大重试次数")
    parser.add_argument("--retry-interval", type=int, default=10, help="重试间隔（秒）")
    parser.add_argument("--force", action="store_true", help="强制同步（覆盖检查）")
    
    args = parser.parse_args()
    
    # 设置日志级别为INFO
    logger.setLevel(logging.INFO)
    
    print("=" * 50)
    print("双色球数据同步工具")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"数据库路径: {args.db}")
    print("=" * 50)
    
    try:
        if args.force:
            # 强制同步逻辑
            db = DoubleBallDatabase(args.db)
            crawler = DoubleBallCrawler(db)

            logger.info("强制同步模式...")
            result = crawler.sync_all_data(force_update=True)

            if result.get('total_records', 0) > 0:
                total_records = result['total_records']
                inserted = result.get('inserted', 0)
                logger.info(f"获取到 {total_records} 条记录，成功插入 {inserted} 条记录")
                print(f"✅ 强制同步完成，共 {inserted} 条记录")
            else:
                logger.error("获取数据失败")
                print("❌ 获取数据失败")
                sys.exit(1)

        else:
            # 正常同步
            success = sync_with_retry(
                db_path=args.db,
                max_retries=args.retry,
                retry_interval=args.retry_interval
            )
            
            if success:
                print("✅ 数据同步成功")
            else:
                print("❌ 数据同步失败")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"同步过程出错: {e}")
        print(f"❌ 同步失败: {e}")
        sys.exit(1)
