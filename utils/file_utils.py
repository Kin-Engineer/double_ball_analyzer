#  utils/file_utils.py
"""
文件操作工具函数
"""
import os
import json
import csv
import pickle
import shutil
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger('file_utils')

def ensure_dir(directory: str) -> str:
    """确保目录存在，如果不存在则创建"""
    os.makedirs(directory, exist_ok=True)
    return directory

def read_json_file(filepath: str) -> Optional[Dict]:
    """读取JSON文件"""
    try:
        if not os.path.exists(filepath):
            logger.warning(f"文件不存在: {filepath}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取JSON文件失败 {filepath}: {e}")
        return None

def write_json_file(filepath: str, data: Any, indent: int = 2) -> bool:
    """写入JSON文件"""
    try:
        ensure_dir(os.path.dirname(filepath))
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        logger.debug(f"JSON文件写入成功: {filepath}")
        return True
    except Exception as e:
        logger.error(f"写入JSON文件失败 {filepath}: {e}")
        return False

def read_csv_file(filepath: str) -> Optional[List[Dict]]:
    """读取CSV文件"""
    try:
        if not os.path.exists(filepath):
            logger.warning(f"文件不存在: {filepath}")
            return None
        
        data = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    except Exception as e:
        logger.error(f"读取CSV文件失败 {filepath}: {e}")
        return None

def write_csv_file(filepath: str, data: List[Dict], fieldnames: Optional[List[str]] = None) -> bool:
    """写入CSV文件"""
    try:
        if not data:
            logger.warning("没有数据可写入CSV")
            return False
        
        ensure_dir(os.path.dirname(filepath))
        
        if fieldnames is None:
            fieldnames = list(data[0].keys())
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.debug(f"CSV文件写入成功: {filepath}")
        return True
    except Exception as e:
        logger.error(f"写入CSV文件失败 {filepath}: {e}")
        return False

def save_pickle(filepath: str, data: Any) -> bool:
    """保存数据为pickle文件"""
    try:
        ensure_dir(os.path.dirname(filepath))
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        logger.debug(f"Pickle文件保存成功: {filepath}")
        return True
    except Exception as e:
        logger.error(f"保存Pickle文件失败 {filepath}: {e}")
        return False

def load_pickle(filepath: str) -> Optional[Any]:
    """加载pickle文件"""
    try:
        if not os.path.exists(filepath):
            logger.warning(f"Pickle文件不存在: {filepath}")
            return None
        
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        logger.error(f"加载Pickle文件失败 {filepath}: {e}")
        return None

def get_file_size(filepath: str) -> Optional[int]:
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"获取文件大小失败 {filepath}: {e}")
        return None

def get_file_extension(filepath: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(filepath)[1].lower()

def is_file_empty(filepath: str) -> bool:
    """检查文件是否为空"""
    try:
        return os.path.getsize(filepath) == 0
    except Exception:
        return True

def list_files(directory: str, pattern: str = "*") -> List[str]:
    """列出目录中的文件"""
    try:
        if not os.path.exists(directory):
            return []
        
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if pattern == "*" or filename.endswith(pattern):
                    files.append(os.path.join(root, filename))
        return files
    except Exception as e:
        logger.error(f"列出文件失败 {directory}: {e}")
        return []

def backup_file(filepath: str, backup_dir: str = "backups") -> Optional[str]:
    """备份文件"""
    try:
        if not os.path.exists(filepath):
            logger.warning(f"要备份的文件不存在: {filepath}")
            return None
        
        ensure_dir(backup_dir)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        backup_name = f"{timestamp}_{filename}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        shutil.copy2(filepath, backup_path)
        logger.info(f"文件备份成功: {filepath} -> {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"文件备份失败 {filepath}: {e}")
        return None

def delete_old_files(directory: str, max_files: int = 10) -> int:
    """删除旧文件，只保留最新的max_files个"""
    try:
        if not os.path.exists(directory):
            return 0
        
        files = list_files(directory)
        if len(files) <= max_files:
            return 0
        
        # 按修改时间排序
        files_with_time = [(f, os.path.getmtime(f)) for f in files]
        files_sorted = sorted(files_with_time, key=lambda x: x[1])
        
        deleted_count = 0
        for filepath, _ in files_sorted[:len(files) - max_files]:
            try:
                os.remove(filepath)
                deleted_count += 1
                logger.debug(f"删除旧文件: {filepath}")
            except Exception as e:
                logger.warning(f"删除文件失败 {filepath}: {e}")
        
        return deleted_count
    except Exception as e:
        logger.error(f"删除旧文件失败 {directory}: {e}")
        return 0