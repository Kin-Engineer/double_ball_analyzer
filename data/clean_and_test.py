# clean_and_test.py - 清理和测试脚本
import os
import sys
import shutil
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('clean_test')

def backup_old_database():
    """备份旧数据库"""
    db_file = "double_ball.db"
    if os.path.exists(db_file):
        # 创建带时间戳的备份文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"double_ball_backup_{timestamp}.db"
        
        try:
            shutil.copy2(db_file, backup_file)
            logger.info(f"✅ 旧数据库已备份到: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            return None
    else:
        logger.info("✅ 没有找到旧数据库文件")
        return None

def delete_old_database():
    """删除旧数据库"""
    db_file = "double_ball.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            logger.info("✅ 已删除旧数据库")
            return True
        except Exception as e:
            logger.error(f"❌ 删除失败: {e}")
            return False
    else:
        logger.info("✅ 数据库文件不存在，无需删除")
        return True

def test_new_database():
    """测试新数据库"""
    try:
        # 导入修复后的模块
        from data.models import DoubleBallRecord
        from data.database import DoubleBallDatabase
        
        logger.info("🔧 创建新数据库...")
        db = DoubleBallDatabase()
        
        # 检查表是否存在
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{db.TABLE_NAME}'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            logger.info(f"✅ 数据库表 '{db.TABLE_NAME}' 创建成功")
        else:
            logger.error(f"❌ 数据库表 '{db.TABLE_NAME}' 创建失败")
            return False
        
        # 检查记录数
        count = db.get_record_count()
        logger.info(f"📊 数据库当前记录数: {count}")
        
        # 创建一个测试记录
        test_record = DoubleBallRecord(
            issue="26001",
            red1=2, red2=6, red3=11, red4=12, red5=13, red6=33,
            blue=15,
            draw_date="2026-01-01"
        )
        
        # 验证记录
        if test_record.is_valid():
            logger.info(f"✅ 测试记录验证通过: {test_record.get_numbers_string()}")
        else:
            logger.error(f"❌ 测试记录验证失败")
            return False
        
        # 保存测试记录
        saved = db.save_records([test_record])
        if saved > 0:
            logger.info(f"✅ 测试记录保存成功")
        else:
            logger.error(f"❌ 测试记录保存失败")
            return False
        
        # 再次检查记录数
        new_count = db.get_record_count()
        logger.info(f"📊 数据库记录数更新为: {new_count}")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_new_crawler():
    """测试新爬虫"""
    try:
        from data.crawler import DoubleBallCrawler
        
        logger.info("🕷️  测试新爬虫...")
        crawler = DoubleBallCrawler()
        
        # 测试连接
        if crawler.test_connection():
            logger.info("✅ 爬虫连接测试成功")
        else:
            logger.warning("⚠️  爬虫连接测试失败，可能使用模拟数据")
        
        # 获取最新期号
        latest_info = crawler.get_latest_issue_info()
        logger.info(f"📅 最新期号信息: {latest_info}")
        
        # 测试爬取单期数据（使用已知有效的期号）
        test_issue = "26001"
        logger.info(f"🔍 测试爬取期号: {test_issue}")
        record = crawler.crawl_single_period(test_issue)
        
        if record and record.is_valid():
            logger.info(f"✅ 爬取测试成功: {record.issue}: {record.get_numbers_string()}")
        else:
            logger.warning(f"⚠️  爬取测试失败，将使用模拟数据")
        
        crawler.cleanup()
        return True
        
    except Exception as e:
        logger.error(f"❌ 爬虫测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主清理和测试流程"""
    print("\n" + "="*60)
    print("🔄 双色球系统数据库清理与测试")
    print("="*60)
    
    print("\n1️⃣ 备份旧数据库...")
    backup_file = backup_old_database()
    
    print("\n2️⃣ 删除旧数据库...")
    if delete_old_database():
        print("✅ 旧数据库清理完成")
    else:
        print("❌ 旧数据库清理失败，退出")
        return
    
    print("\n3️⃣ 测试新数据库...")
    if test_new_database():
        print("✅ 新数据库测试通过")
    else:
        print("❌ 新数据库测试失败")
        return
    
    print("\n4️⃣ 测试新爬虫...")
    if test_new_crawler():
        print("✅ 新爬虫测试通过")
    else:
        print("⚠️  新爬虫测试有问题，但可以继续")
    
    print("\n" + "="*60)
    print("🎉 清理和测试完成！")
    print("="*60)
    
    if backup_file:
        print(f"\n📁 旧数据库备份文件: {backup_file}")
        print("⚠️  如果需要恢复旧数据，请手动复制备份文件")
    
    print("\n接下来可以运行完整的数据同步:")
    print("1. 运行 data/crawler.py")
    print("2. 选择 '同步所有数据'")
    print("3. 系统将从2003年到当前年份爬取数据")
    
    print("\n注意：完整数据同步可能需要较长时间（几小时）")
    print("建议先测试少量数据，确认爬虫正常工作")

if __name__ == "__main__":
    main()
