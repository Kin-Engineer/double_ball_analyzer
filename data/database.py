# data/database.py
import os
import sqlite3
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
from collections import Counter
from utils.window_config import WindowConfigManager


# 使用绝对导入或根据项目结构调整
try:
    # 尝试两种导入方式
    from data.models import DoubleBallRecord
except ImportError:
    from .models import DoubleBallRecord

logger = logging.getLogger(__name__)

class DoubleBallDatabase:
    """双色球数据库操作类"""
    
    # 定义表名常量
    TABLE_NAME = "doubleball_records"

    def __init__(self, db_path: str = None):
        if db_path is None:
            try:
                from config import config
                db_path = config.paths.DATABASE_PATH
            except ImportError:
                db_path = "double_ball.db"
    
    # def __init__(self, db_path: Optional[str] = None):
    #     """初始化数据库连接
    #
    #     Args:
    #         db_path: 数据库文件路径，默认为当前目录下的double_ball.db
    #     """
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        try:
            if self.conn is None:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
            return self.conn
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def _init_database(self) -> None:
        """初始化数据库和表结构"""
        try:
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建双色球记录表 - 放宽约束以兼容模拟数据
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        issue TEXT UNIQUE NOT NULL,
                        red1 INTEGER NOT NULL CHECK (red1 BETWEEN 1 AND 33),
                        red2 INTEGER NOT NULL CHECK (red2 BETWEEN 1 AND 33),
                        red3 INTEGER NOT NULL CHECK (red3 BETWEEN 1 AND 33),
                        red4 INTEGER NOT NULL CHECK (red4 BETWEEN 1 AND 33),
                        red5 INTEGER NOT NULL CHECK (red5 BETWEEN 1 AND 33),
                        red6 INTEGER NOT NULL CHECK (red6 BETWEEN 1 AND 33),
                        blue INTEGER NOT NULL CHECK (blue BETWEEN 1 AND 16),
                        draw_date TEXT NOT NULL,
                        year INTEGER,
                        month INTEGER,  -- 移除CHECK约束以兼容模拟数据
                        day INTEGER,    -- 移除CHECK约束以兼容模拟数据
                        weekday TEXT,
                        weekday_num INTEGER,  -- 移除CHECK约束以兼容模拟数据
                        quarter INTEGER,      -- 移除CHECK约束以兼容模拟数据
                        season TEXT,
                        month_type TEXT,
                        is_weekend INTEGER,   -- 移除CHECK约束以兼容模拟数据
                        red_sum INTEGER,      -- 移除CHECK约束以兼容模拟数据
                        red_avg REAL,         -- 移除CHECK约束以兼容模拟数据
                        red_odd_count INTEGER, -- 移除CHECK约束以兼容模拟数据
                        red_even_count INTEGER, -- 移除CHECK约束以兼容模拟数据
                        red_prime_count INTEGER, -- 移除CHECK约束以兼容模拟数据
                        red_range INTEGER,     -- 移除CHECK约束以兼容模拟数据
                        blue_zone TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(issue)
                    )
                ''')
                
                # 创建索引
                indexes = [
                    ('idx_issue', 'issue'),
                    ('idx_draw_date', 'draw_date'),
                    ('idx_year', 'year'),
                    ('idx_red_blue', 'red1, red2, red3, red4, red5, red6, blue'),
                    ('idx_date_issue', 'draw_date, issue')
                ]
                
                for idx_name, idx_columns in indexes:
                    cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {self.TABLE_NAME}({idx_columns})')
                
                conn.commit()
                logger.info(f"数据库初始化完成: {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
        except Exception as e:
            logger.error(f"未知错误: {e}")
            raise
    
    def save_records(self, records: List[DoubleBallRecord]) -> int:
        """保存记录到数据库
        
        Args:
            records: 双色球记录列表
            
        Returns:
            成功保存的记录数量
        """
        if not records:
            logger.warning("没有需要保存的记录")
            return 0
        
        saved_count = 0
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                for record in records:
                    if not record.is_valid():
                        logger.warning(f"跳过无效记录: {record.issue}")
                        continue
                    
                    # 处理可能为None的字段
                    weekday_num = record.weekday_num if record.weekday_num is not None else 0
                    month = record.month if record.month is not None else 1
                    day = record.day if record.day is not None else 1
                    quarter = record.quarter if record.quarter is not None else 1
                    is_weekend = 1 if record.is_weekend else 0
                    
                    # 确保值在合理范围内
                    if weekday_num < 0 or weekday_num > 6:
                        logger.warning(f"修正weekday_num值: {weekday_num} -> {weekday_num % 7}")
                        weekday_num = weekday_num % 7
                    
                    if month < 1 or month > 12:
                        logger.warning(f"修正month值: {month} -> {1 if month < 1 else 12}")
                        month = 1 if month < 1 else 12
                    
                    if day < 1 or day > 31:
                        logger.warning(f"修正day值: {day} -> {1 if day < 1 else 31}")
                        day = 1 if day < 1 else 31
                    
                    if quarter < 1 or quarter > 4:
                        logger.warning(f"修正quarter值: {quarter} -> {1 if quarter < 1 else 4}")
                        quarter = 1 if quarter < 1 else 4
                    
                    # 准备插入数据
                    data = (
                        record.issue, 
                        record.red1, record.red2, record.red3,
                        record.red4, record.red5, record.red6,
                        record.blue, 
                        record.draw_date,
                        record.year, month, day,
                        record.weekday, weekday_num,
                        quarter, record.season, record.month_type,
                        is_weekend,
                        record.red_sum, record.red_avg,
                        record.red_odd_count, record.red_even_count,
                        record.red_prime_count, record.red_range,
                        record.blue_zone,
                        now, now
                    )
                    
                    cursor.execute(f'''
                        INSERT OR REPLACE INTO {self.TABLE_NAME} 
                        (issue, red1, red2, red3, red4, red5, red6, blue, draw_date,
                         year, month, day, weekday, weekday_num, quarter, season, month_type, is_weekend,
                         red_sum, red_avg, red_odd_count, red_even_count, red_prime_count, red_range, blue_zone,
                         created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data)
                    
                    saved_count += 1
                
                conn.commit()
                logger.info(f"成功保存 {saved_count}/{len(records)} 条记录到数据库")
                
            except sqlite3.IntegrityError as e:
                conn.rollback()
                logger.error(f"数据完整性错误: {e}")
                
                # 尝试更宽松的插入方式
                saved_count = self._save_records_without_constraints(records)
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"数据库错误: {e}")
                raise
            
        return saved_count
    
    def _save_records_without_constraints(self, records: List[DoubleBallRecord]) -> int:
        """使用宽松方式保存记录（移除约束的表）"""
        saved_count = 0
        now = datetime.now().isoformat()
        
        # 临时表名
        temp_table = f"{self.TABLE_NAME}_temp"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 创建临时表（无约束）
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {temp_table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        issue TEXT UNIQUE NOT NULL,
                        red1 INTEGER,
                        red2 INTEGER,
                        red3 INTEGER,
                        red4 INTEGER,
                        red5 INTEGER,
                        red6 INTEGER,
                        blue INTEGER,
                        draw_date TEXT,
                        year INTEGER,
                        month INTEGER,
                        day INTEGER,
                        weekday TEXT,
                        weekday_num INTEGER,
                        quarter INTEGER,
                        season TEXT,
                        month_type TEXT,
                        is_weekend INTEGER,
                        red_sum INTEGER,
                        red_avg REAL,
                        red_odd_count INTEGER,
                        red_even_count INTEGER,
                        red_prime_count INTEGER,
                        red_range INTEGER,
                        blue_zone TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )
                ''')
                
                # 插入数据到临时表
                for record in records:
                    try:
                        data = (
                            record.issue, 
                            record.red1, record.red2, record.red3,
                            record.red4, record.red5, record.red6,
                            record.blue, 
                            record.draw_date,
                            record.year, record.month, record.day,
                            record.weekday, record.weekday_num,
                            record.quarter, record.season, record.month_type,
                            1 if record.is_weekend else 0,
                            record.red_sum, record.red_avg,
                            record.red_odd_count, record.red_even_count,
                            record.red_prime_count, record.red_range,
                            record.blue_zone,
                            now, now
                        )
                        
                        cursor.execute(f'''
                            INSERT OR REPLACE INTO {temp_table} 
                            (issue, red1, red2, red3, red4, red5, red6, blue, draw_date,
                             year, month, day, weekday, weekday_num, quarter, season, month_type, is_weekend,
                             red_sum, red_avg, red_odd_count, red_even_count, red_prime_count, red_range, blue_zone,
                             created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', data)
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.warning(f"无法保存记录 {record.issue} 到临时表: {e}")
                
                conn.commit()
                logger.warning(f"使用临时表保存了 {saved_count} 条记录，部分约束检查已跳过")
                
                # 将数据从临时表复制到主表
                self._migrate_from_temp_table(temp_table)
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"临时表保存失败: {e}")
            
        return saved_count
    
    def _migrate_from_temp_table(self, temp_table: str) -> None:
        """从临时表迁移数据到主表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 复制数据，跳过有约束问题的记录
                cursor.execute(f'''
                    INSERT OR IGNORE INTO {self.TABLE_NAME}
                    SELECT * FROM {temp_table}
                    WHERE 
                        red1 BETWEEN 1 AND 33 AND
                        red2 BETWEEN 1 AND 33 AND
                        red3 BETWEEN 1 AND 33 AND
                        red4 BETWEEN 1 AND 33 AND
                        red5 BETWEEN 1 AND 33 AND
                        red6 BETWEEN 1 AND 33 AND
                        blue BETWEEN 1 AND 16 AND
                        (month IS NULL OR month BETWEEN 1 AND 12) AND
                        (day IS NULL OR day BETWEEN 1 AND 31) AND
                        (weekday_num IS NULL OR weekday_num BETWEEN 0 AND 6) AND
                        (quarter IS NULL OR quarter BETWEEN 1 AND 4) AND
                        (is_weekend IS NULL OR is_weekend IN (0, 1))
                ''')
                
                # 删除临时表
                cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
                
                conn.commit()
                logger.info("已从临时表迁移数据到主表")
                
            except sqlite3.Error as e:
                logger.error(f"数据迁移失败: {e}")
    
    def get_all_records(self, limit: Optional[int] = None, 
                       order_by: str = "CAST(issue AS INTEGER) DESC") -> List[DoubleBallRecord]:
        """获取所有记录
        
        Args:
            limit: 限制返回数量
            order_by: 排序字段
            
        Returns:
            双色球记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                query = f"SELECT * FROM {self.TABLE_NAME} ORDER BY {order_by}"
                params = ()
                
                if limit is not None and limit > 0:
                    query += " LIMIT ?"
                    params = (limit,)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = self._row_to_record(row)
                    if record:
                        records.append(record)
                
                logger.debug(f"获取到 {len(records)} 条记录")
                return records
                
            except sqlite3.Error as e:
                logger.error(f"获取记录失败: {e}")
                return []
    
    def get_recent_records(self, limit: int = 20) -> List[DoubleBallRecord]:
        """获取最近的N条开奖记录
        
        Args:
            limit: 记录数量限制
            
        Returns:
            最近的N条记录
        """
        if limit <= 0:
            logger.warning(f"无效的limit参数: {limit}")
            return []
        
        return self.get_all_records(limit=limit, order_by="CAST(issue AS INTEGER) DESC")
    
    def get_record_by_issue(self, issue: str) -> Optional[DoubleBallRecord]:
        """根据期号获取记录
        
        Args:
            issue: 期号
            
        Returns:
            双色球记录对象或None
        """
        if not issue:
            logger.warning("期号不能为空")
            return None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(f"SELECT * FROM {self.TABLE_NAME} WHERE issue = ?", (issue,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_record(row)
                
                logger.debug(f"未找到期号为 {issue} 的记录")
                return None
                
            except sqlite3.Error as e:
                logger.error(f"查询记录失败: {e}")
                return None
    
    def get_records_by_year(self, year: int) -> List[DoubleBallRecord]:
        """根据年份获取记录
        
        Args:
            year: 年份
            
        Returns:
            指定年份的记录列表
        """
        if year <= 0:
            logger.warning(f"无效的年份: {year}")
            return []
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    f"SELECT * FROM {self.TABLE_NAME} WHERE year = ? ORDER BY CAST(issue AS INTEGER) DESC", 
                    (year,)
                )
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = self._row_to_record(row)
                    if record:
                        records.append(record)
                
                logger.debug(f"获取到 {year} 年的 {len(records)} 条记录")
                return records
                
            except sqlite3.Error as e:
                logger.error(f"获取记录失败: {e}")
                return []
    
    def _row_to_record(self, row: sqlite3.Row) -> Optional[DoubleBallRecord]:
        """将数据库行转换为DoubleBallRecord对象
        
        Args:
            row: 数据库行
            
        Returns:
            DoubleBallRecord对象或None
        """
        try:
            # 从行中获取基本数据
            issue = row['issue']
            red_balls = [
                row['red1'], row['red2'], row['red3'],
                row['red4'], row['red5'], row['red6']
            ]
            blue = row['blue']
            draw_date = row['draw_date']
            
            # 创建记录对象
            record = DoubleBallRecord(
                issue=issue,
                red1=red_balls[0], red2=red_balls[1], red3=red_balls[2],
                red4=red_balls[3], red5=red_balls[4], red6=red_balls[5],
                blue=blue,
                draw_date=draw_date
            )
            
            # 设置时间特征
            record.year = row['year'] if row['year'] is not None else None
            record.month = row['month'] if row['month'] is not None else None
            record.day = row['day'] if row['day'] is not None else None
            record.weekday = row['weekday'] or ''
            record.weekday_num = row['weekday_num'] if row['weekday_num'] is not None else None
            record.quarter = row['quarter'] if row['quarter'] is not None else None
            record.season = row['season'] or ''
            record.month_type = row['month_type'] or ''
            record.is_weekend = bool(row['is_weekend']) if row['is_weekend'] is not None else False
            
            # 设置统计特征
            record.red_sum = row['red_sum'] if row['red_sum'] is not None else 0
            record.red_avg = row['red_avg'] if row['red_avg'] is not None else 0.0
            record.red_odd_count = row['red_odd_count'] if row['red_odd_count'] is not None else 0
            record.red_even_count = row['red_even_count'] if row['red_even_count'] is not None else 0
            record.red_prime_count = row['red_prime_count'] if row['red_prime_count'] is not None else 0
            record.red_range = row['red_range'] if row['red_range'] is not None else 0
            record.blue_zone = row['blue_zone'] or ''
            
            return record
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"转换记录失败: {e}, 行数据: {dict(row)}")
            return None
    
    def get_record_count(self) -> int:
        """获取记录总数
        
        Returns:
            记录总数
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")
                count = cursor.fetchone()[0]
                return count if count is not None else 0
            except sqlite3.Error as e:
                logger.error(f"获取记录数失败: {e}")
                return 0
    
    def get_total_records(self) -> int:
        """获取记录总数（兼容性方法）"""
        return self.get_record_count()
    
    def clear_all_data(self) -> bool:
        """清空所有数据
        
        Returns:
            是否成功清空
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(f"DELETE FROM {self.TABLE_NAME}")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (self.TABLE_NAME,))
                conn.commit()
                
                logger.info("已清空所有数据")
                return True
                
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"清空数据失败: {e}")
                return False
    
    def clear_all_records(self) -> bool:
        """清空所有记录（clear_all_data的别名）"""
        return self.clear_all_data()
    
    def get_latest_issue(self) -> Optional[str]:
        """获取最新期号
        
        Returns:
            最新期号或None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    f"SELECT issue FROM {self.TABLE_NAME} ORDER BY CAST(issue AS INTEGER) DESC LIMIT 1"
                )
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
            except sqlite3.Error as e:
                logger.error(f"获取最新期号失败: {e}")
                return None
    
    def get_earliest_issue(self) -> Optional[str]:
        """获取最早期号
        
        Returns:
            最早期号或None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    f"SELECT issue FROM {self.TABLE_NAME} ORDER BY CAST(issue AS INTEGER) ASC LIMIT 1"
                )
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
            except sqlite3.Error as e:
                logger.error(f"获取最早期号失败: {e}")
                return None
    
    def get_years_with_data(self) -> List[int]:
        """获取有数据的年份列表
        
        Returns:
            年份列表，按降序排列
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    f"SELECT DISTINCT year FROM {self.TABLE_NAME} WHERE year IS NOT NULL ORDER BY year DESC"
                )
                results = cursor.fetchall()
                return [row[0] for row in results if row[0] is not None]
            except sqlite3.Error as e:
                logger.error(f"获取年份列表失败: {e}")
                return []
    
    def get_issue_range(self) -> Dict[str, str]:
        """获取期号范围
        
        Returns:
            包含最小和最大期号的字典
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    f"SELECT MIN(CAST(issue AS INTEGER)), MAX(CAST(issue AS INTEGER)) FROM {self.TABLE_NAME}"
                )
                result = cursor.fetchone()
                
                if result and result[0] is not None and result[1] is not None:
                    return {
                        'min_issue': str(result[0]),
                        'max_issue': str(result[1])
                    }
                return {}
            except sqlite3.Error as e:
                logger.error(f"获取期号范围失败: {e}")
                return {}
    
    def get_date_range(self) -> Dict[str, str]:
        """获取日期范围
        
        Returns:
            包含最小和最大日期的字典
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(f"SELECT MIN(draw_date), MAX(draw_date) FROM {self.TABLE_NAME}")
                result = cursor.fetchone()
                
                if result and result[0] and result[1]:
                    return {
                        'min_date': result[0],
                        'max_date': result[1]
                    }
                return {}
            except sqlite3.Error as e:
                logger.error(f"获取日期范围失败: {e}")
                return {}
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息
        
        Returns:
            数据库信息字典
        """
        try:
            # 获取表结构信息
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({self.TABLE_NAME})")
                table_info = cursor.fetchall()
                
                # 获取记录统计
                record_count = self.get_record_count()
                
                # 获取年份范围
                cursor.execute(f"SELECT MIN(year), MAX(year) FROM {self.TABLE_NAME}")
                year_range = cursor.fetchone()
                
                # 获取其他信息
                issue_range = self.get_issue_range()
                date_range = self.get_date_range()
                
                # 获取数据库大小
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'table_name': self.TABLE_NAME,
                    'table_columns': len(table_info),
                    'record_count': record_count,
                    'min_year': year_range[0] if year_range and year_range[0] else None,
                    'max_year': year_range[1] if year_range and year_range[1] else None,
                    'issue_range': issue_range,
                    'date_range': date_range,
                    'database_path': self.db_path,
                    'database_size': f"{db_size / 1024:.2f} KB",
                    'last_updated': datetime.fromtimestamp(os.path.getmtime(self.db_path)).isoformat() 
                                  if os.path.exists(self.db_path) else None
                }
                
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取基本统计信息
        
        Returns:
            统计信息字典
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 基本统计
                total_records = self.get_record_count()
                
                # 期号范围
                issue_range = self.get_issue_range()
                
                # 号码频率统计
                red_frequency = {}
                for i in range(1, 34):
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM {self.TABLE_NAME} 
                        WHERE ? IN (red1, red2, red3, red4, red5, red6)
                    """, (i,))
                    red_frequency[i] = cursor.fetchone()[0]
                
                blue_frequency = {}
                for i in range(1, 17):
                    cursor.execute(f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE blue = ?", (i,))
                    blue_frequency[i] = cursor.fetchone()[0]
                
                # 热门号码
                hot_reds = sorted(red_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
                hot_blues = sorted(blue_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
                
                # 冷门号码
                cold_reds = sorted(red_frequency.items(), key=lambda x: x[1])[:10]
                cold_blues = sorted(blue_frequency.items(), key=lambda x: x[1])[:5]
                
                return {
                    'total_records': total_records,
                    'latest_issue': issue_range.get('max_issue'),
                    'earliest_issue': issue_range.get('min_issue'),
                    'red_frequency': red_frequency,
                    'blue_frequency': blue_frequency,
                    'hot_reds': hot_reds,
                    'hot_blues': hot_blues,
                    'cold_reds': cold_reds,
                    'cold_blues': cold_blues
                }
                
            except sqlite3.Error as e:
                logger.error(f"获取统计信息失败: {e}")
                return {}
    
    def get_records_sorted_by_issue(self, ascending: bool = True, 
                                   limit: Optional[int] = None) -> List[DoubleBallRecord]:
        """按期号数值排序获取记录
        
        Args:
            ascending: 是否升序排序
            limit: 限制返回数量
            
        Returns:
            排序后的记录列表
        """
        order = "ASC" if ascending else "DESC"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                query = f"SELECT * FROM {self.TABLE_NAME} ORDER BY CAST(issue AS INTEGER) {order}"
                params = ()
                
                if limit is not None and limit > 0:
                    query += " LIMIT ?"
                    params = (limit,)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = self._row_to_record(row)
                    if record:
                        records.append(record)
                
                return records
                
            except sqlite3.Error as e:
                logger.error(f"获取排序记录失败: {e}")
                return []
    
    def get_records_by_issue_range(self, start_issue: str, end_issue: str) -> List[DoubleBallRecord]:
        """获取指定期号范围的记录
        
        Args:
            start_issue: 起始期号
            end_issue: 结束期号
            
        Returns:
            期号范围内的记录列表
        """
        try:
            start_int = int(start_issue)
            end_int = int(end_issue)
            
            if start_int > end_int:
                start_int, end_int = end_int, start_int
                logger.warning(f"起始期号大于结束期号，已自动交换: {start_issue}-{end_issue}")
            
        except ValueError as e:
            logger.error(f"期号转换失败: {e}")
            return []
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(f"""
                    SELECT * FROM {self.TABLE_NAME} 
                    WHERE CAST(issue AS INTEGER) BETWEEN ? AND ?
                    ORDER BY CAST(issue AS INTEGER) ASC
                """, (start_int, end_int))
                
                rows = cursor.fetchall()
                records = []
                for row in rows:
                    record = self._row_to_record(row)
                    if record:
                        records.append(record)
                
                logger.debug(f"获取到 {len(records)} 条 {start_issue}-{end_issue} 期间的记录")
                return records
                
            except sqlite3.Error as e:
                logger.error(f"获取期号范围记录失败: {e}")
                return []
    
    def get_records_by_date_range(self, start_date: str, end_date: str) -> List[DoubleBallRecord]:
        """获取指定日期范围的记录
        
        Args:
            start_date: 起始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            日期范围内的记录列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(f"""
                    SELECT * FROM {self.TABLE_NAME} 
                    WHERE draw_date BETWEEN ? AND ?
                    ORDER BY draw_date ASC
                """, (start_date, end_date))
                
                rows = cursor.fetchall()
                records = []
                for row in rows:
                    record = self._row_to_record(row)
                    if record:
                        records.append(record)
                
                logger.debug(f"获取到 {len(records)} 条 {start_date}-{end_date} 期间的记录")
                return records
                
            except sqlite3.Error as e:
                logger.error(f"获取日期范围记录失败: {e}")
                return []
    
    def get_red_blue_combinations(self) -> Dict[str, List[Tuple]]:
        """获取红蓝球组合统计
        
        Returns:
            包含各种组合统计的字典
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 红球奇偶组合
                cursor.execute(f"""
                    SELECT red_odd_count, red_even_count, COUNT(*) as count
                    FROM {self.TABLE_NAME}
                    GROUP BY red_odd_count, red_even_count
                    ORDER BY count DESC
                """)
                odd_even_combo = cursor.fetchall()
                
                # 蓝球分区统计
                cursor.execute(f"""
                    SELECT blue_zone, COUNT(*) as count
                    FROM {self.TABLE_NAME}
                    WHERE blue_zone IS NOT NULL
                    GROUP BY blue_zone
                    ORDER BY count DESC
                """)
                blue_zone_stats = cursor.fetchall()
                
                return {
                    'odd_even_combinations': [(row[0], row[1], row[2]) for row in odd_even_combo],
                    'blue_zone_distribution': [(row[0], row[1]) for row in blue_zone_stats]
                }
                
            except sqlite3.Error as e:
                logger.error(f"获取组合统计失败: {e}")
                return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """备份数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            是否备份成功
        """
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"数据库备份成功: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False
    
    def optimize_database(self) -> bool:
        """优化数据库性能
        
        Returns:
            是否优化成功
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # 执行VACUUM命令整理数据库
                cursor.execute("VACUUM")
                
                # 重新分析统计信息
                cursor.execute("ANALYZE")
                
                conn.commit()
                logger.info("数据库优化完成")
                return True
                
            except sqlite3.Error as e:
                logger.error(f"数据库优化失败: {e}")
                return False
    
    def recreate_table_with_constraints(self) -> bool:
        """重新创建表并添加约束（在数据清理后使用）"""
        try:
            # 备份数据
            temp_table = f"{self.TABLE_NAME}_backup"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 创建备份表
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {temp_table} AS SELECT * FROM {self.TABLE_NAME}")
                
                # 删除原表
                cursor.execute(f"DROP TABLE IF EXISTS {self.TABLE_NAME}")
                
                # 重新创建带有约束的表
                cursor.execute(f'''
                    CREATE TABLE {self.TABLE_NAME} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        issue TEXT UNIQUE NOT NULL,
                        red1 INTEGER NOT NULL CHECK (red1 BETWEEN 1 AND 33),
                        red2 INTEGER NOT NULL CHECK (red2 BETWEEN 1 AND 33),
                        red3 INTEGER NOT NULL CHECK (red3 BETWEEN 1 AND 33),
                        red4 INTEGER NOT NULL CHECK (red4 BETWEEN 1 AND 33),
                        red5 INTEGER NOT NULL CHECK (red5 BETWEEN 1 AND 33),
                        red6 INTEGER NOT NULL CHECK (red6 BETWEEN 1 AND 33),
                        blue INTEGER NOT NULL CHECK (blue BETWEEN 1 AND 16),
                        draw_date TEXT NOT NULL,
                        year INTEGER,
                        month INTEGER CHECK (month BETWEEN 1 AND 12),
                        day INTEGER CHECK (day BETWEEN 1 AND 31),
                        weekday TEXT,
                        weekday_num INTEGER CHECK (weekday_num BETWEEN 0 AND 6),
                        quarter INTEGER CHECK (quarter BETWEEN 1 AND 4),
                        season TEXT,
                        month_type TEXT,
                        is_weekend INTEGER CHECK (is_weekend IN (0, 1)),
                        red_sum INTEGER CHECK (red_sum BETWEEN 21 AND 183),
                        red_avg REAL CHECK (red_avg BETWEEN 3.5 AND 30.5),
                        red_odd_count INTEGER CHECK (red_odd_count BETWEEN 0 AND 6),
                        red_even_count INTEGER CHECK (red_even_count BETWEEN 0 AND 6),
                        red_prime_count INTEGER CHECK (red_prime_count BETWEEN 0 AND 6),
                        red_range INTEGER CHECK (red_range BETWEEN 5 AND 32),
                        blue_zone TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(issue)
                    )
                ''')
                
                # 插入清理后的数据
                cursor.execute(f"""
                    INSERT OR IGNORE INTO {self.TABLE_NAME}
                    SELECT * FROM {temp_table}
                    WHERE 
                        red1 BETWEEN 1 AND 33 AND
                        red2 BETWEEN 1 AND 33 AND
                        red3 BETWEEN 1 AND 33 AND
                        red4 BETWEEN 1 AND 33 AND
                        red5 BETWEEN 1 AND 33 AND
                        red6 BETWEEN 1 AND 33 AND
                        blue BETWEEN 1 AND 16 AND
                        (month IS NULL OR month BETWEEN 1 AND 12) AND
                        (day IS NULL OR day BETWEEN 1 AND 31) AND
                        (weekday_num IS NULL OR weekday_num BETWEEN 0 AND 6) AND
                        (quarter IS NULL OR quarter BETWEEN 1 AND 4) AND
                        (is_weekend IS NULL OR is_weekend IN (0, 1))
                """)
                
                # 删除备份表
                cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
                
                # 重新创建索引
                indexes = [
                    ('idx_issue', 'issue'),
                    ('idx_draw_date', 'draw_date'),
                    ('idx_year', 'year'),
                    ('idx_red_blue', 'red1, red2, red3, red4, red5, red6, blue'),
                    ('idx_date_issue', 'draw_date, issue')
                ]
                
                for idx_name, idx_columns in indexes:
                    cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {self.TABLE_NAME}({idx_columns})')
                
                conn.commit()
                logger.info("已重新创建表并添加约束")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"重新创建表失败: {e}")
            return False

    # 新增扩展数据库统计功能
    def get_statistics_with_period(self, period: int = 30) -> Dict[str, Any]:
        """获取带周期参数的统计信息（紧急修复版）"""
        # 如果未指定period，从配置读取
        if period is None:
            try:
                # 使用WindowConfigManager获取短期窗口配置
                from utils.window_config import WindowConfigManager
                period = WindowConfigManager.get_window_by_name('short_term')
            except (ImportError, AttributeError):
                # 如果无法导入WindowConfigManager，尝试从config获取
                try:
                    from config import config
                    period = config.analysis.TREND_ANALYSIS_WINDOW
                except:
                    # 最后使用WindowConfigManager的默认值
                    period = WindowConfigManager.get_window_by_name('short_term')

        # 获取最近period期记录
        recent_records = self.get_recent_records(period)
        if not recent_records:
            return {}

        total_games = len(recent_records)

        # 统计红球和蓝球出现次数
        red_counts = Counter()
        blue_counts = Counter()
        sums = []

        for record in recent_records:
            reds = [record.red1, record.red2, record.red3,
                    record.red4, record.red5, record.red6]

            for ball in reds:
                red_counts[ball] += 1

            blue_counts[record.blue] += 1
            sums.append(sum(reds))

        # 确保所有红球（1-33）都在计数器中
        for ball in range(1, 34):
            if ball not in red_counts:
                red_counts[ball] = 0

        # 调试信息：打印出现次数
        print(f"\n=== 数据库统计调试信息 ===")
        print(f"分析窗口: {period}期")
        print(f"实际数据: {total_games}期")
        print(f"红球出现次数统计:")

        # 按出现次数排序
        sorted_reds = sorted(red_counts.items(), key=lambda x: (-x[1], x[0]))
        for ball, count in sorted_reds:
            print(f"  红球{ball:02d}: {count}次")

        # 修复：使用更合理的分类标准
        # 如果总期数太少，调整分类策略
        if total_games < 20:
            # 小数据量时的简单分类
            avg_count = total_games * 6 / 33  # 理论平均出现次数
            hot_reds = []
            cold_reds = []
            warm_reds = []

            for ball in range(1, 34):
                count = red_counts[ball]
                if count >= avg_count * 1.2:
                    hot_reds.append(ball)
                elif count <= avg_count * 0.5:
                    cold_reds.append(ball)
                else:
                    warm_reds.append(ball)
        else:
            # 大数据量时的排名分类
            sorted_reds = sorted(red_counts.items(), key=lambda x: (-x[1], x[0]))
            hot_reds = [ball for ball, _ in sorted_reds[:11]]
            warm_reds = [ball for ball, _ in sorted_reds[11:22]]
            cold_reds = [ball for ball, _ in sorted_reds[22:33]]

        print(f"\n分类结果:")
        print(f"  热号 ({len(hot_reds)}个): {sorted(hot_reds)}")
        print(f"  温号 ({len(warm_reds)}个): {sorted(warm_reds)}")
        print(f"  冷号 ({len(cold_reds)}个): {sorted(cold_reds)}")
        print("=" * 40)

        # 计算和值趋势
        avg_sum = sum(sums) / len(sums) if sums else 0
        sum_trend = "稳定"
        if len(sums) >= 2:
            if sums[-1] > sums[-2]:
                sum_trend = "上升"
            elif sums[-1] < sums[-2]:
                sum_trend = "下降"

        return {
            'period': period,
            'total_games': total_games,
            'hot_reds': hot_reds,
            'warm_reds': warm_reds,
            'cold_reds': cold_reds,
            'sum_trend': sum_trend,
            'avg_sum': avg_sum,
            'red_frequencies': dict(red_counts),
            'blue_frequencies': dict(blue_counts),
            'recent_sums': sums[-10:] if len(sums) >= 10 else sums
        }

    def get_repeat_probability_analysis(self) -> Dict[str, Any]:
        """获取重号概率分析"""
        all_records = self.get_all_records()
        if len(all_records) < 2:
            return {}

        # 统计重号数量分布
        repeat_counts = Counter()
        position_repeats = [Counter() for _ in range(6)]  # 6个红球位置
        blue_repeats = Counter()

        for i in range(len(all_records) - 1):
            current = all_records[i]
            next_record = all_records[i + 1]

            current_reds = {current.red1, current.red2, current.red3,
                            current.red4, current.red5, current.red6}
            next_reds = {next_record.red1, next_record.red2, next_record.red3,
                         next_record.red4, next_record.red5, next_record.red6}

            # 重号数量
            repeat_count = len(current_reds & next_reds)
            repeat_counts[repeat_count] += 1

            # 位置重号
            current_positions = [current.red1, current.red2, current.red3,
                                 current.red4, current.red5, current.red6]
            next_positions = [next_record.red1, next_record.red2, next_record.red3,
                              next_record.red4, next_record.red5, next_record.red6]

            for pos in range(6):
                if current_positions[pos] == next_positions[pos]:
                    position_repeats[pos][current_positions[pos]] += 1

            # 蓝球重号
            if current.blue == next_record.blue:
                blue_repeats[current.blue] += 1

        total_pairs = len(all_records) - 1

        # 计算概率
        repeat_probabilities = {
            count: occurrences / total_pairs
            for count, occurrences in repeat_counts.items()
        }

        position_probabilities = []
        for pos_counter in position_repeats:
            pos_total = sum(pos_counter.values())
            probabilities = {
                ball: count / pos_total if pos_total > 0 else 0
                for ball, count in pos_counter.items()
            }
            position_probabilities.append(probabilities)

        blue_probabilities = {
            ball: count / total_pairs for ball, count in blue_repeats.items()
        }

        return {
            'total_pairs': total_pairs,
            'repeat_distribution': dict(repeat_counts),
            'repeat_probabilities': repeat_probabilities,
            'position_probabilities': position_probabilities,
            'blue_repeat_probabilities': blue_probabilities
        }

    def get_combination_probability(self, period: int = 100) -> Dict[str, Any]:
        """获取号码组合概率"""
        recent_records = self.get_recent_records(period)
        if not recent_records:
            return {}

        # 统计任意两个号码同时出现的次数
        pair_counts = Counter()

        for record in recent_records:
            reds = sorted([record.red1, record.red2, record.red3,
                           record.red4, record.red5, record.red6])

            # 生成所有两两组合
            for i in range(len(reds)):
                for j in range(i + 1, len(reds)):
                    pair = (reds[i], reds[j])
                    pair_counts[pair] += 1

        total_games = len(recent_records)

        # 计算概率
        pair_probabilities = {}
        for pair, count in pair_counts.most_common(50):  # 只取前50个
            probability = count / total_games
            pair_probabilities[f"{pair[0]:02d}-{pair[1]:02d}"] = {
                'count': count,
                'probability': probability,
                'expected': probability * total_games
            }

        return {
            'period': period,
            'total_games': total_games,
            'pair_probabilities': pair_probabilities,
            'most_common_pairs': list(pair_counts.most_common(20))
        }

    # ================ 新增方法 ================

    def get_latest_record(self) -> Optional[DoubleBallRecord]:
        """获取最新一期完整记录

        Returns:
            最新一期记录，如果没有记录则返回None
        """
        try:
            records = self.get_recent_records(limit=1)
            return records[0] if records else None
        except Exception as e:
            logger.error(f"获取最新记录失败: {e}")
            return None

    def get_hot_numbers(self, window: int = 30, top_n: int = 10) -> List[int]:
        """获取热号（出现频率高的号码）

        Args:
            window: 统计的期数窗口
            top_n: 返回的热号数量

        Returns:
            热门号码列表
        """
        try:
            recent_records = self.get_recent_records(window)
            if not recent_records:
                return []

            red_counts = Counter()
            for record in recent_records:
                reds = [record.red1, record.red2, record.red3,
                        record.red4, record.red5, record.red6]
                for ball in reds:
                    red_counts[ball] += 1

            # 按出现次数降序排序，取前top_n个
            hot_numbers = [ball for ball, _ in red_counts.most_common(top_n)]
            return hot_numbers

        except Exception as e:
            logger.error(f"获取热号失败: {e}")
            return []

    def get_cold_numbers(self, window: int = 30, top_n: int = 10) -> List[int]:
        """获取冷号（出现频率低的号码）

        Args:
            window: 统计的期数窗口
            top_n: 返回的冷号数量

        Returns:
            冷门号码列表
        """
        try:
            recent_records = self.get_recent_records(window)
            if not recent_records:
                return []

            red_counts = Counter()
            for record in recent_records:
                reds = [record.red1, record.red2, record.red3,
                        record.red4, record.red5, record.red6]
                for ball in reds:
                    red_counts[ball] += 1

            # 确保所有号码都在计数器中
            for ball in range(1, 34):
                if ball not in red_counts:
                    red_counts[ball] = 0

            # 按出现次数升序排序，取前top_n个
            cold_numbers = [ball for ball, _ in red_counts.most_common()[-top_n:]]
            return cold_numbers

        except Exception as e:
            logger.error(f"获取冷号失败: {e}")
            return []

    def close(self):
        """关闭数据库连接"""
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                self.conn = None
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.warning(f"关闭数据库连接时出错: {e}")

    def __del__(self):
        """析构函数，确保数据库连接被关闭"""
        self.close()

    # ================ 新增方法结束 ================