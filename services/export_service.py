# services/export_service.py
"""
导出服务 - 将分析结果导出为多种格式
"""
import logging
import os
import json
import csv
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from utils.db_manager import DatabaseManager
from utils.color_utils import print_success, print_warning, print_error

logger = logging.getLogger('export_service')

class ExportService:
    """导出服务"""
    
    def __init__(self, db_path: str = None):
        self.db_manager = DatabaseManager()
        
        if db_path is None:
            from config import config
            db_path = config.paths.DATABASE_PATH
        
        self.db = self.db_manager.get_db(db_path)
        
        # 导出目录
        from config import config
        self.exports_dir = config.paths.EXPORTS_DIR
        os.makedirs(self.exports_dir, exist_ok=True)
        
        logger.info("导出服务初始化完成")
    
    def export_to_csv(self, data: List[Dict[str, Any]], filename: str = None) -> Dict[str, Any]:
        """
        导出数据到CSV
        
        Args:
            data: 要导出的数据列表
            filename: 输出文件名（可选）
            
        Returns:
            导出结果信息
        """
        try:
            if not data:
                return {'error': '没有数据可导出'}
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}.csv"
            
            filepath = os.path.join(self.exports_dir, filename)
            
            # 确定CSV列名
            if isinstance(data[0], dict):
                fieldnames = list(data[0].keys())
            else:
                # 如果是其他格式，转换为字典列表
                data = self._normalize_data(data)
                if not data:
                    return {'error': '数据格式不支持'}
                fieldnames = list(data[0].keys())
            
            # 写入CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            result = {
                'success': True,
                'filepath': filepath,
                'filename': filename,
                'size': os.path.getsize(filepath),
                'records': len(data),
                'format': 'csv',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"导出到CSV成功: {filepath} ({len(data)} 条记录)")
            return result
            
        except Exception as e:
            logger.error(f"导出到CSV失败: {e}")
            return {'error': str(e)}
    
    def export_to_json(self, data: Any, filename: str = None) -> Dict[str, Any]:
        """
        导出数据到JSON
        
        Args:
            data: 要导出的数据
            filename: 输出文件名（可选）
            
        Returns:
            导出结果信息
        """
        try:
            if data is None:
                return {'error': '没有数据可导出'}
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}.json"
            
            filepath = os.path.join(self.exports_dir, filename)
            
            # 写入JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            result = {
                'success': True,
                'filepath': filepath,
                'filename': filename,
                'size': os.path.getsize(filepath),
                'format': 'json',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"导出到JSON成功: {filepath}")
            return result
            
        except Exception as e:
            logger.error(f"导出到JSON失败: {e}")
            return {'error': str(e)}
    
    def export_to_excel(self, data: List[Dict[str, Any]], filename: str = None) -> Dict[str, Any]:
        """
        导出数据到Excel
        
        Args:
            data: 要导出的数据列表
            filename: 输出文件名（可选）
            
        Returns:
            导出结果信息
        """
        try:
            if not data:
                return {'error': '没有数据可导出'}
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"export_{timestamp}.xlsx"
            
            filepath = os.path.join(self.exports_dir, filename)
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 写入Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            
            result = {
                'success': True,
                'filepath': filepath,
                'filename': filename,
                'size': os.path.getsize(filepath),
                'records': len(data),
                'format': 'excel',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"导出到Excel成功: {filepath} ({len(data)} 条记录)")
            return result
            
        except ImportError:
            return {'error': 'pandas或openpyxl未安装'}
        except Exception as e:
            logger.error(f"导出到Excel失败: {e}")
            return {'error': str(e)}
    
    def export_historical_data(self, limit: int = None, filename: str = None) -> Dict[str, Any]:
        """
        导出历史数据
        
        Args:
            limit: 限制记录数（可选）
            filename: 输出文件名（可选）
            
        Returns:
            导出结果信息
        """
        try:
            # 获取历史数据
            records = self.db.get_all_records(limit=limit)
            
            if not records:
                return {'error': '没有历史数据'}
            
            # 转换为字典列表
            data = []
            for record in records:
                data.append({
                    'issue': record.issue,
                    'date': record.date,
                    'red1': record.red1,
                    'red2': record.red2,
                    'red3': record.red3,
                    'red4': record.red4,
                    'red5': record.red5,
                    'red6': record.red6,
                    'blue': record.blue,
                    'red_sum': record.red1 + record.red2 + record.red3 + 
                              record.red4 + record.red5 + record.red6,
                    'odd_count': sum(1 for x in [
                        record.red1, record.red2, record.red3,
                        record.red4, record.red5, record.red6
                    ] if x % 2 == 1)
                })
            
            # 导出为CSV
            return self.export_to_csv(data, filename)
            
        except Exception as e:
            logger.error(f"导出历史数据失败: {e}")
            return {'error': str(e)}
    
    def export_statistics(self, period: int = 100, filename: str = None) -> Dict[str, Any]:
        """
        导出统计数据
        
        Args:
            period: 统计周期
            filename: 输出文件名（可选）
            
        Returns:
            导出结果信息
        """
        try:
            # 获取统计数据
            stats = self.db.get_statistics_with_period(period)
            
            if not stats:
                return {'error': '无法获取统计数据'}
            
            # 准备数据
            export_data = {
                'statistics': stats,
                'export_info': {
                    'period': period,
                    'timestamp': datetime.now().isoformat(),
                    'total_records': stats.get('total_records', 0)
                }
            }
            
            # 导出为JSON
            return self.export_to_json(export_data, filename)
            
        except Exception as e:
            logger.error(f"导出统计数据失败: {e}")
            return {'error': str(e)}
    
    def export_prediction_result(self, prediction_result: Dict[str, Any], filename: str = None) -> Dict[str, Any]:
        """
        导出预测结果
        
        Args:
            prediction_result: 预测结果
            filename: 输出文件名（可选）
            
        Returns:
            导出结果信息
        """
        try:
            if not prediction_result or not isinstance(prediction_result, dict):
                return {'error': '无效的预测结果'}
            
            # 提取关键信息
            export_data = {
                'predictions': {},
                'metadata': {}
            }

            # 提取预测组合
            for key in ['6_plus_1', '7_plus_1', '8_plus_1']:
                if key in prediction_result and isinstance(prediction_result[key], dict):
                    pred = prediction_result[key]
                    export_data['predictions'][key] = {
                        'red_balls': pred.get('red_balls', []),
                        'blue_ball': pred.get('blue_ball', 0),
                        'confidence': pred.get('confidence', 0),
                        'strategy': pred.get('strategy', ''),
                        'num_reds': pred.get('num_reds', int(key[0]))
                    }

            # 提取元数据
            if 'system_info' in prediction_result:
                info = prediction_result['system_info']
                export_data['metadata'] = {
                    'prediction_time': info.get('prediction_time', datetime.now().isoformat()),
                    'latest_issue': info.get('latest_issue', 'unknown'),
                    'records_count': info.get('records_count', 0)
                }

            if 'repeat_analysis' in prediction_result:
                export_data['probability_analysis'] = prediction_result['repeat_analysis']

            if 'recommended_combination' in prediction_result:
                export_data['recommendation'] = {
                    'best_combination': prediction_result['recommended_combination'],
                    'confidence': prediction_result.get('recommended_confidence', 0)
                }

            # 导出为JSON
            return self.export_to_json(export_data, filename)

        except Exception as e:
            logger.error(f"导出预测结果失败: {e}")
            return {'error': str(e)}

        def export_analysis_report(self, analysis_result: Dict[str, Any], filename: str = None) -> Dict[str, Any]:
            """
            导出分析报告

            Args:
                analysis_result: 分析结果
                filename: 输出文件名（可选）

            Returns:
                导出结果信息
            """
            try:
                if not analysis_result or not isinstance(analysis_result, dict):
                    return {'error': '无效的分析结果'}

                # 准备导出数据
                export_data = {
                    'analysis': analysis_result,
                    'export_info': {
                        'export_type': 'analysis_report',
                        'timestamp': datetime.now().isoformat(),
                        'format_version': '1.0'
                    }
                }

                # 导出为JSON
                return self.export_to_json(export_data, filename)

            except Exception as e:
                logger.error(f"导出分析报告失败: {e}")
                return {'error': str(e)}

        def _normalize_data(self, data: Any) -> List[Dict[str, Any]]:
            """规范化数据为字典列表"""
            if isinstance(data, list):
                if not data:
                    return []

                # 检查第一个元素类型
                first_item = data[0]
                if isinstance(first_item, dict):
                    return data
                elif hasattr(first_item, '__dict__'):
                    # 如果是对象，转换为字典
                    return [item.__dict__ for item in data]
                elif isinstance(first_item, (list, tuple)):
                    # 如果是列表/元组，转换为字典
                    result = []
                    for item in data:
                        if isinstance(item, (list, tuple)) and len(item) > 1:
                            result.append({
                                'column_1': item[0] if len(item) > 0 else None,
                                'column_2': item[1] if len(item) > 1 else None,
                                'column_3': item[2] if len(item) > 2 else None,
                                'column_4': item[3] if len(item) > 3 else None,
                                'column_5': item[4] if len(item) > 4 else None
                            })
                    return result

            # 其他类型转换为字典列表
            return [{'value': data}] if data is not None else []

        def get_export_history(self, limit: int = 20) -> List[Dict[str, Any]]:
            """获取导出历史"""
            try:
                import glob
                from datetime import datetime

                if not os.path.exists(self.exports_dir):
                    return []

                export_files = []

                # 查找所有导出文件
                patterns = [
                    os.path.join(self.exports_dir, 'export_*.csv'),
                    os.path.join(self.exports_dir, 'export_*.json'),
                    os.path.join(self.exports_dir, 'export_*.xlsx')
                ]

                for pattern in patterns:
                    export_files.extend(glob.glob(pattern))

                # 按修改时间排序
                export_files.sort(key=os.path.getmtime, reverse=True)

                history = []
                for filepath in export_files[:limit]:
                    try:
                        stats = os.stat(filepath)
                        filename = os.path.basename(filepath)

                        # 提取信息
                        ext = os.path.splitext(filename)[1]
                        base_name = os.path.splitext(filename)[0]

                        # 从文件名中提取时间戳
                        timestamp_str = base_name.replace('export_', '')
                        timestamp = datetime.fromtimestamp(stats.st_mtime)

                        history.append({
                            'filename': filename,
                            'filepath': filepath,
                            'size': stats.st_size,
                            'modified': timestamp.isoformat(),
                            'formatted_date': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'format': ext[1:].upper() if ext.startswith('.') else ext
                        })
                    except Exception as e:
                        logger.warning(f"处理导出文件 {filepath} 失败: {e}")

                return history

            except Exception as e:
                logger.error(f"获取导出历史失败: {e}")
                return []

        def cleanup_old_exports(self, max_files: int = 50) -> Dict[str, Any]:
            """清理旧的导出文件"""
            try:
                if not os.path.exists(self.exports_dir):
                    return {'success': True, 'deleted': 0, 'message': '导出目录不存在'}

                export_files = glob.glob(os.path.join(self.exports_dir, 'export_*'))

                if len(export_files) <= max_files:
                    return {'success': True, 'deleted': 0, 'message': '文件数量未超过限制'}

                # 按修改时间排序
                files_with_time = [(f, os.path.getmtime(f)) for f in export_files]
                files_sorted = sorted(files_with_time, key=lambda x: x[1])

                deleted_count = 0
                deleted_files = []

                # 删除最旧的文件
                for filepath, _ in files_sorted[:len(files_sorted) - max_files]:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                        deleted_files.append(os.path.basename(filepath))
                        logger.info(f"删除旧导出文件: {filepath}")
                    except Exception as e:
                        logger.warning(f"删除文件失败 {filepath}: {e}")

                result = {
                    'success': True,
                    'deleted': deleted_count,
                    'files': deleted_files[:10],  # 只显示前10个
                    'total_before': len(files_sorted),
                    'total_after': len(files_sorted) - deleted_count
                }

                if deleted_files:
                    logger.info(f"清理完成，删除了 {deleted_count} 个旧导出文件")

                return result

            except Exception as e:
                logger.error(f"清理旧导出文件失败: {e}")
                return {'success': False, 'error': str(e)}

# 全局导出服务实例
export_service = None

def get_export_service(db_path=None):
    """获取导出服务实例"""
    global export_service
    if export_service is None:
        export_service = ExportService(db_path)
    return export_service

