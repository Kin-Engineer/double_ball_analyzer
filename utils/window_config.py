# utils/window_config.py
"""
统一窗口配置管理器
提供系统统一的窗口配置访问接口
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger('window_config')

class WindowConfigManager:
    """窗口配置管理器（静态类）"""
    
    # 标准窗口配置
    _WINDOW_CONFIG = {
        'short_term': 30,      # 短期窗口
        'medium_term': 50,     # 中期窗口
        'long_term': 100,      # 长期窗口
        'all_history': None    # 全部历史
    }
    
    # 趋势分析窗口
    _TREND_WINDOWS = [30, 50, 100, None]
    
    @classmethod
    def get_all_windows(cls) -> Dict[str, Any]:
        """获取所有窗口配置"""
        return cls._WINDOW_CONFIG.copy()
    
    @classmethod
    def get_standard_windows(cls) -> Dict[str, int]:
        """获取标准窗口配置（短、中、长期）"""
        return {
            'short_term': cls._WINDOW_CONFIG['short_term'],
            'medium_term': cls._WINDOW_CONFIG['medium_term'],
            'long_term': cls._WINDOW_CONFIG['long_term']
        }
    
    @classmethod
    def get_window_by_name(cls, name: str) -> Optional[int]:
        """通过名称获取窗口值"""
        return cls._WINDOW_CONFIG.get(name)
    
    @classmethod
    def get_trend_windows(cls) -> List[Optional[int]]:
        """获取趋势分析窗口列表"""
        return cls._TREND_WINDOWS.copy()
    
    @classmethod
    def set_window_config(cls, config: Dict[str, Any]):
        """设置窗口配置"""
        if 'short_term' in config:
            cls._WINDOW_CONFIG['short_term'] = config['short_term']
        if 'medium_term' in config:
            cls._WINDOW_CONFIG['medium_term'] = config['medium_term']
        if 'long_term' in config:
            cls._WINDOW_CONFIG['long_term'] = config['long_term']
        
        # 更新趋势窗口
        cls._TREND_WINDOWS = [
            cls._WINDOW_CONFIG['short_term'],
            cls._WINDOW_CONFIG['medium_term'],
            cls._WINDOW_CONFIG['long_term'],
            None
        ]
        
        logger.info(f"窗口配置已更新: {cls._WINDOW_CONFIG}")
    
    @classmethod
    def update_from_config(cls, config_object):
        """从配置对象更新窗口配置"""
        try:
            if hasattr(config_object, 'analysis'):
                analysis_config = config_object.analysis
                
                new_config = {
                    'short_term': getattr(analysis_config, 'SHORT_TERM_WINDOW', 30),
                    'medium_term': getattr(analysis_config, 'MEDIUM_TERM_WINDOW', 50),
                    'long_term': getattr(analysis_config, 'LONG_TERM_WINDOW', 100)
                }
                
                cls.set_window_config(new_config)
                logger.info(f"从系统配置同步窗口配置: {new_config}")
                
        except Exception as e:
            logger.warning(f"从配置对象更新窗口配置失败: {e}")

# 初始化：在导入时同步系统配置
try:
    from config import config
    WindowConfigManager.update_from_config(config)
except ImportError:
    logger.warning("无法导入系统配置，使用默认窗口配置")