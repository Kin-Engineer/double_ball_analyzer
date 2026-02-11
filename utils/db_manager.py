# utils/db_manager.py
"""
数据库连接管理器
"""
import logging
from data.database import DoubleBallDatabase

logger = logging.getLogger('db_manager')

class DatabaseManager:
    """数据库连接管理器"""
    
    _instance = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_db(self, db_path: str = None) -> DoubleBallDatabase:
        """获取数据库实例"""
        if db_path is None:
            # 从 config 获取默认路径
            try:
                from config import config
                db_path = config.paths.DATABASE_PATH  # 注意: 数据库路径引用，非窗口配置
            except ImportError:
                db_path = "double_ball.db"

        if self._db is None:
            logger.info(f"初始化数据库连接: {db_path}")
            self._db = DoubleBallDatabase(db_path)
        return self._db
    
    def close_connection(self):
        """关闭数据库连接"""
        if self._db is not None:
            try:
                self._db.close()
                logger.info("数据库连接已关闭")
            except Exception as e:
                logger.warning(f"关闭数据库连接失败: {e}")
            finally:
                self._db = None