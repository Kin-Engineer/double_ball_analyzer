# config.py
"""
双色球分析系统 - 配置文件 (实际配置版)
基于实际项目结构调整
"""

# =============================================================================
# 实际项目结构图 (基于实际运行情况)
# =============================================================================
"""
double_ball_analyzer/
├── config.py                    # 配置管理 (本文件)
├── main.py                      # 主程序入口
├── requirements.txt             # 依赖包列表
├── README.md                    # 项目说明
├── run.py                       # 快速启动脚本
├── data_sync.py                 # 独立数据同步脚本
│
├── core/                        # 核心系统模块
│   ├── __init__.py
│   ├── analyzer.py              # 主分析器
│   ├── enhanced_analyzer.py     # 增强分析器
│   └── unified_analyzer.py      # 统一分析接口
│
├── data/                        # 数据模块 (实际数据库位置)
│   ├── __init__.py
│   ├── database.py              # 数据库操作
│   ├── crawler.py               # 数据爬取
│   ├── models.py                # 数据模型
│   ├── processor.py             # 基础数据处理
│   ├── advanced_processor.py    # 高级特征处理
│   └── predictor.py             # 预测算法
│
├── analysis/                    # 分析模块
│   ├── __init__.py
│   ├── statistics.py            # 统计分析
│   ├── visualization.py         # 数据可视化
│   ├── trend_analysis.py        # 趋势分析
│   ├── probability_analyzer.py  # 概率分析器
│   └── hot_cold_analyzer.py     # 热冷号分析器
│
├── services/                    # 服务模块
│   ├── __init__.py
│   ├── prediction_service.py    # 预测服务
│   ├── analysis_service.py      # 分析服务
│   ├── model_training.py        # 模型训练服务
│   └── export_service.py        # 导出服务
│
├── ui/                          # 用户界面模块
│   ├── __init__.py
│   ├── display.py               # 显示管理
│   ├── interactive.py           # 交互管理 (主界面)
│   └── menu.py                  # 菜单系统
│
├── utils/                       # 工具模块
│   ├── __init__.py
│   ├── logger.py                # 日志工具
│   ├── color_utils.py           # 颜色工具
│   ├── data_utils.py            # 数据处理工具
│   ├── file_utils.py            # 文件操作工具
│   ├── db_manager.py            # 数据库管理器
│   └── validation_utils.py      # 验证工具
│
├── workflows/                   # 工作流程模块
│   ├── __init__.py
│   ├── full_analysis.py         # 完整分析流程
│   ├── prediction_workflow.py   # 预测流程
│   └── data_pipeline.py         # 数据处理流程
│
├── data/                        # 数据文件目录 (实际位置)
│   └── double_ball.db          # 主数据库文件 (实际位置)
│
├── reports/                     # 报告文件目录 (实际位置)
│   ├── prediction_*.txt        # 预测报告
│   └── analysis_*.txt          # 分析报告
│
├── visualizations/              # 可视化图表目录
│   ├── red_frequency.png
│   ├── blue_frequency.png
│   └── time_series.png
│
├── logs/                       # 日志文件目录
│   ├── double_ball.log
│   ├── crawler.log
│   └── prediction.log
│
├── exports/                    # 导出文件目录 (新增)
│   ├── csv_exports/
│   ├── json_exports/
│   └── excel_exports/
│
├── models/                     # 模型文件目录 (运行时创建)
│   ├── xgboost_model.pkl
│   ├── lightgbm_model.pkl
│   └── statistical_model.pkl
│
└── tests/                      # 测试目录 (可选)
    └── __init__.py

实际使用的目录结构 (重点)：
1. data/double_ball.db      - 数据库文件 (实际位置，保持不变)
2. reports/                 - 报告文件 (实际位置，保持不变)
3. visualizations/          - 可视化图表
4. logs/                   - 日志文件
5. exports/                - 导出文件 (新增)
6. models/                 - 模型文件

模块依赖关系:
main.py → config.py → core/ → services/ → analysis/ → data/ → ui/ → workflows/ → utils/
数据处理流程: 爬取数据 → 存储到数据库 → 基础数据处理 → 高级特征处理 → 统计分析 → 可视化展示 → 预测分析 → 报告生成
"""

import os
import logging
import yaml
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass
class PathConfig:
    """路径配置 (基于实际项目结构)"""

    # 基础路径
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))

    # 核心模块路径
    CORE_DIR: str = os.path.join(BASE_DIR, 'core')
    DATA_DIR: str = os.path.join(BASE_DIR, 'data')
    ANALYSIS_DIR: str = os.path.join(BASE_DIR, 'analysis')
    SERVICES_DIR: str = os.path.join(BASE_DIR, 'services')
    UI_DIR: str = os.path.join(BASE_DIR, 'ui')
    UTILS_DIR: str = os.path.join(BASE_DIR, 'utils')
    WORKFLOWS_DIR: str = os.path.join(BASE_DIR, 'workflows')

    # 数据文件路径 (基于实际位置)
    DATABASE_PATH: str = os.path.join(DATA_DIR, 'double_ball.db')  # 实际数据库位置
    BACKUP_DIR: str = os.path.join(DATA_DIR, 'backups')           # 数据库备份目录
    CACHE_DIR: str = os.path.join(DATA_DIR, 'cache')              # 缓存目录
    
    # 报告文件路径 (基于实际位置 - 根目录下的reports)
    REPORTS_DIR: str = os.path.join(BASE_DIR, 'reports')          # 实际报告位置
    
    # 导出文件路径 (新增)
    EXPORTS_DIR: str = os.path.join(BASE_DIR, 'exports')
    
    # 可视化文件路径
    VISUALIZATIONS_DIR: str = os.path.join(BASE_DIR, 'visualizations')
    
    # 模型文件路径
    MODELS_DIR: str = os.path.join(BASE_DIR, 'models')
    
    # 日志文件路径
    LOGS_DIR: str = os.path.join(BASE_DIR, 'logs')
    MAIN_LOG: str = os.path.join(LOGS_DIR, 'double_ball.log')
    CRAWLER_LOG: str = os.path.join(LOGS_DIR, 'crawler.log')
    PREDICTION_LOG: str = os.path.join(LOGS_DIR, 'prediction.log')
    
    # 测试路径 (可选)
    TESTS_DIR: str = os.path.join(BASE_DIR, 'tests')

    def __post_init__(self):
        """初始化实际使用的目录结构"""
        directories = [
            # 代码目录
            self.CORE_DIR, self.DATA_DIR, self.ANALYSIS_DIR,
            self.SERVICES_DIR, self.UI_DIR, self.UTILS_DIR,
            self.WORKFLOWS_DIR,

            # 数据目录
            self.BACKUP_DIR, self.CACHE_DIR,
            
            # 报告和导出目录 (实际使用)
            self.REPORTS_DIR,         # 报告目录 (实际使用)
            self.EXPORTS_DIR,         # 导出目录 (新增)
            
            # 可视化目录
            self.VISUALIZATIONS_DIR,
            
            # 模型目录
            self.MODELS_DIR,
            
            # 日志目录
            self.LOGS_DIR,
            
            # 测试目录 (可选)
            self.TESTS_DIR
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logging.debug(f"确保目录存在: {directory}")

@dataclass
class DatabaseConfig:
    """数据库配置"""
    
    # 数据库设置
    DATABASE_PATH: str = "data/double_ball.db"  # 基于实际位置
    TABLE_NAME: str = "doubleball_records"
    
    # 连接设置
    TIMEOUT: int = 30
    CHECK_SAME_THREAD: bool = False
    AUTOMATIC_BACKUP: bool = True
    
    # 备份设置
    BACKUP_ENABLED: bool = True
    BACKUP_INTERVAL_DAYS: int = 7
    MAX_BACKUP_FILES: int = 10
    BACKUP_ON_START: bool = True
    
    # 性能设置
    CACHE_SIZE: int = 10000
    JOURNAL_MODE: str = "WAL"
    SYNC_MODE: str = "NORMAL"
    
    # 数据完整性
    FOREIGN_KEYS: bool = True
    AUTO_VACUUM: bool = True
    
    # 查询优化
    DEFAULT_LIMIT: int = 1000
    BATCH_SIZE: int = 100


@dataclass
class CrawlerConfig:
    """爬虫配置"""

    # 数据源配置
    DATA_SOURCES: Dict[str, str] = field(default_factory=lambda: {
        'primary': 'https://datachart.500.com/ssq/history/history.shtml',
        'backup_1': 'https://www.500.com/static/info/kaijiang/ssq/',
        'backup_2': 'https://kaijiang.zhcw.com'
    })

    # 每年期数配置
    YEAR_ISSUES: Dict[int, int] = field(default_factory=lambda: {
        2003: 89, 2004: 122, 2005: 153, 2006: 154, 2007: 153,
        2008: 154, 2009: 154, 2010: 153, 2011: 153, 2012: 154,
        2013: 154, 2014: 152, 2015: 154, 2016: 153, 2017: 154,
        2018: 153, 2019: 151, 2020: 134, 2021: 150, 2022: 150,
        2023: 151, 2024: 151, 2025: 151, 2026: 151
    })

    # 请求配置
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    RETRY_BACKOFF: float = 2.0

    # 延迟配置
    REQUEST_DELAY: Tuple[float, float] = (1.0, 3.0)  # 最小和最大延迟秒数

    # 并发配置
    MAX_CONCURRENT_REQUESTS: int = 5
    CONCURRENT_DELAY: float = 0.5

    # 数据更新配置
    UPDATE_INTERVAL_HOURS: int = 6
    FORCE_UPDATE_DAYS: int = 1
    INCREMENTAL_UPDATE: bool = True

    # 代理配置
    USE_PROXY: bool = False
    PROXY_POOL: List[str] = field(default_factory=list)

    # 数据验证
    VALIDATE_DATA: bool = True
    MIN_RECORDS_PER_YEAR: Dict[int, int] = field(default_factory=lambda: {
        2003: 80, 2004: 110, 2005: 140, 2006: 140, 2007: 140,
        2008: 140, 2009: 140, 2010: 140, 2011: 140, 2012: 140,
        2013: 140, 2014: 140, 2015: 140, 2016: 140, 2017: 140,
        2018: 140, 2019: 140, 2020: 120, 2021: 140, 2022: 140,
        2023: 140, 2024: 140, 2025: 140, 2026: 140
    })

@dataclass
class ProcessorConfig:
    """处理器配置"""
    
    # 处理器启用配置
    PROCESSOR_ENABLED: bool = True
    ADVANCED_PROCESSOR_ENABLED: bool = True
    
    # 特征处理配置
    HEAT_COLD_WINDOW: int = 15
    RECENT_ANALYSIS_WINDOW: int = 10
    TREND_ANALYSIS_WINDOW: int = 5
    OMISSION_HISTORY_WINDOW: int = 50
    
    # 数据验证配置
    MIN_RED_BALL: int = 1
    MAX_RED_BALL: int = 33
    MIN_BLUE_BALL: int = 1
    MAX_BLUE_BALL: int = 16
    
    # 特征生成配置
    GENERATE_AC_VALUE: bool = True
    GENERATE_SUM_FEATURES: bool = True
    GENERATE_ZONE_FEATURES: bool = True
    GENERATE_INTERVAL_FEATURES: bool = True
    
    # 缓存配置
    FEATURE_CACHE_SIZE: int = 1000
    CACHE_TTL_SECONDS: int = 3600
    
    # 特征阈值
    HOT_THRESHOLD_MULTIPLIER: float = 1.5
    COLD_THRESHOLD_MULTIPLIER: float = 0.5

@dataclass
class AnalysisConfig:
    """分析配置"""
    
    # 统计分析配置
    STATISTICS_ENABLED: bool = True
    BASIC_STATS_WINDOW: int = 100  # 长期
    FREQUENCY_ANALYSIS_WINDOW: int = 50  # 中期
    TREND_ANALYSIS_WINDOW: int = 30  # 短期

    # ========== 新增：统一窗口配置（兼容性别名） ==========
    # # 统一命名，便于代码理解和使用
    # SHORT_TERM_WINDOW: int = 30  # 默认值，如果用户未设置
    # MEDIUM_TERM_WINDOW: int = 50  # 默认值
    # LONG_TERM_WINDOW: int = 100  # 默认值
    # ALL_HISTORY_WINDOW: Any = None  # 全部历史
    #
    # # 热冷号分析窗口
    # HOT_COLD_WINDOW: int = None  # 默认使用短期窗口
    #
    # # 趋势分析窗口配置
    # # TREND_WINDOW_SIZES: List[int] = field(default_factory=lambda: [30, 50, 100])
    # _TREND_WINDOW_SIZES: List[Optional[int]] = field(default_factory=lambda: [30, 50, 100, None])

    # def __post_init__(self):
    #     """
    #     初始化后处理：
    #     1. 确保新旧配置一致
    #     2. 动态设置趋势窗口
    #     """
    #     # 第一步：同步新旧配置（确保兼容性）
    #     # 如果用户通过旧配置设置了值，更新新配置
    #     if self.TREND_ANALYSIS_WINDOW != 30:  # 不是默认值
    #         self.SHORT_TERM_WINDOW = self.TREND_ANALYSIS_WINDOW
    #
    #     if self.FREQUENCY_ANALYSIS_WINDOW != 50:  # 不是默认值
    #         self.MEDIUM_TERM_WINDOW = self.FREQUENCY_ANALYSIS_WINDOW
    #
    #     if self.BASIC_STATS_WINDOW != 100:  # 不是默认值
    #         self.LONG_TERM_WINDOW = self.BASIC_STATS_WINDOW
    #
    #     # 第二步：确保热冷号窗口有值
    #     if self.HOT_COLD_WINDOW == 30:  # 还是默认值
    #         self.HOT_COLD_WINDOW = self.SHORT_TERM_WINDOW
    #
    #     # 第三步：动态设置趋势窗口
    #     if self._TREND_WINDOW_SIZES == [30, 50, 100, None]:  # 默认值
    #         self._TREND_WINDOW_SIZES = [
    #             self.SHORT_TERM_WINDOW,
    #             self.MEDIUM_TERM_WINDOW,
    #             self.LONG_TERM_WINDOW,
    #             None
    #         ]
    #
    #     logger.debug(
    #         f"窗口配置同步完成: 短期={self.SHORT_TERM_WINDOW}, 中期={self.MEDIUM_TERM_WINDOW}, 长期={self.LONG_TERM_WINDOW}")

    # ========== 新增：统一窗口配置 ==========
    # 注意：这里使用field(default_factory)确保每个实例独立
    SHORT_TERM_WINDOW: int = field(default_factory=lambda: 30)  # 短期窗口
    MEDIUM_TERM_WINDOW: int = field(default_factory=lambda: 50)  # 中期窗口
    LONG_TERM_WINDOW: int = field(default_factory=lambda: 100)  # 长期窗口
    ALL_HISTORY_WINDOW: Any = field(default_factory=lambda: None)  # 全部历史

    # 热冷号分析窗口
    HOT_COLD_WINDOW: int = field(default_factory=lambda: 30)  # 默认使用短期窗口

    def __post_init__(self):
        """
        初始化后处理：确保新旧配置一致

        注意：这个__post_init__与PathConfig的__post_init__是独立的
        每个dataclass都有自己的__post_init__方法
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("AnalysisConfig __post_init__ 开始执行")

        # 如果用户通过新配置设置了值，同步到旧配置（保持兼容性）
        if self.SHORT_TERM_WINDOW != 30:  # 不是默认值
            self.TREND_ANALYSIS_WINDOW = self.SHORT_TERM_WINDOW
            logger.debug(f"同步配置: SHORT_TERM_WINDOW -> TREND_ANALYSIS_WINDOW = {self.SHORT_TERM_WINDOW}")

        if self.MEDIUM_TERM_WINDOW != 50:  # 不是默认值
            self.FREQUENCY_ANALYSIS_WINDOW = self.MEDIUM_TERM_WINDOW
            logger.debug(f"同步配置: MEDIUM_TERM_WINDOW -> FREQUENCY_ANALYSIS_WINDOW = {self.MEDIUM_TERM_WINDOW}")

        if self.LONG_TERM_WINDOW != 100:  # 不是默认值
            self.BASIC_STATS_WINDOW = self.LONG_TERM_WINDOW
            logger.debug(f"同步配置: LONG_TERM_WINDOW -> BASIC_STATS_WINDOW = {self.LONG_TERM_WINDOW}")

        # 确保热冷号窗口有值
        if self.HOT_COLD_WINDOW == 30:  # 还是默认值
            self.HOT_COLD_WINDOW = self.SHORT_TERM_WINDOW
            logger.debug(f"设置 HOT_COLD_WINDOW = SHORT_TERM_WINDOW = {self.HOT_COLD_WINDOW}")

        logger.info(
            f"窗口配置初始化完成: 短期={self.SHORT_TERM_WINDOW}, 中期={self.MEDIUM_TERM_WINDOW}, 长期={self.LONG_TERM_WINDOW}")

    @property
    def TREND_WINDOW_SIZES(self) -> List[Optional[int]]:
        """获取趋势分析窗口"""
        return self._TREND_WINDOW_SIZES

    @TREND_WINDOW_SIZES.setter
    def TREND_WINDOW_SIZES(self, value: List[Optional[int]]):
        """设置趋势分析窗口"""
        self._TREND_WINDOW_SIZES = value

    # 概率分析配置
    PROBABILITY_ANALYSIS_ENABLED: bool = True
    REPEAT_PROBABILITY_WINDOW: int = 100
    COMBINATION_PROBABILITY_WINDOW: int = 100
    
    # 热号冷号分析
    HOT_COLD_THRESHOLD: float = 0.3  # 30%作为阈值
    MIN_HOT_FREQUENCY: int = 2
    MAX_COLD_OMISSION: int = 20
    
    # 趋势分析
    TREND_SMOOTHING_WINDOW: int = 10
    DETECT_TREND_CHANGES: bool = True
    
    # 可视化配置
    VISUALIZATION_ENABLED: bool = True
    SAVE_VISUALIZATIONS: bool = True
    VISUALIZATION_FORMAT: str = "png"  # png, pdf, svg
    DPI: int = 150
    FIGURE_SIZE: Tuple[int, int] = (12, 8)

@dataclass
class PredictionConfig:
    """预测配置"""
    
    # 机器学习配置
    ML_ENABLED: bool = True
    ML_MODEL_TYPE: str = "ensemble"  # random_forest, xgboost, lightgbm, ensemble
    TRAIN_TEST_SPLIT: float = 0.8
    CROSS_VALIDATION_FOLDS: int = 5
    MODEL_UPDATE_INTERVAL: int = 30  # 每30期更新一次模型
    
    # 特征工程
    FEATURE_WINDOW: int = 50
    INCLUDE_STAT_FEATURES: bool = True
    INCLUDE_TEMPORAL_FEATURES: bool = True
    INCLUDE_PATTERN_FEATURES: bool = True
    
    # 预测策略
    PREDICTION_STRATEGIES: List[str] = field(default_factory=lambda: [
        "frequency_based",
        "hot_cold",
        "statistical_trend",
        "pattern_recognition",
        "machine_learning"
    ])
    
    COMBINE_PREDICTIONS: bool = True
    MIN_CONFIDENCE_THRESHOLD: float = 0.6
    
    # 多组合预测配置
    MULTIPLE_COMBINATIONS: Dict[str, bool] = field(default_factory=lambda: {
        '6_plus_1': True,   # 基础组合
        '7_plus_1': True,   # 扩展组合
        '8_plus_1': True,   # 高级组合
        'multiple_sets': True  # 多组预测
    })
    
    # 重号预测配置
    REPEAT_PREDICTION_ENABLED: bool = True
    REPEAT_PREDICTION_METHOD: str = "ml_enhanced"  # simple, statistical, ml_enhanced
    MIN_REPEAT_CONFIDENCE: float = 0.3
    MAX_REPEAT_COUNT: int = 3

@dataclass
class ModelTrainingConfig:
    """模型训练配置"""
    
    # 训练配置
    TRAINING_ENABLED: bool = True
    TRAIN_ON_STARTUP: bool = False
    RETRAIN_INTERVAL: int = 30  # 每30期重新训练
    
    # 数据准备
    TRAIN_WINDOW_SIZE: int = 200
    TRAIN_TEST_RATIO: float = 0.8
    RANDOM_STATE: int = 42
    
    # 模型参数
    XGBOOST_PARAMS: Dict[str, Any] = field(default_factory=lambda: {
        'n_estimators': 100,
        'max_depth': 6,
        'learning_rate': 0.1
    })
    
    LIGHTGBM_PARAMS: Dict[str, Any] = field(default_factory=lambda: {
        'n_estimators': 100,
        'max_depth': 6,
        'learning_rate': 0.1
    })

@dataclass
class ExportConfig:
    """导出配置"""
    
    # 导出启用
    EXPORT_ENABLED: bool = True
    
    # 格式配置
    DEFAULT_EXPORT_FORMAT: str = "csv"  # csv, json, excel
    
    # 文件管理
    AUTO_CLEANUP: bool = True
    MAX_EXPORT_FILES: int = 50

@dataclass
class UIConfig:
    """用户界面配置"""
    
    # 界面模式配置
    INTERFACE_MODE: str = "colorful"  # colorful, simple, enhanced
    INTERACTIVE_MODE: bool = True
    SHOW_PROGRESS_BARS: bool = True
    
    # 显示配置
    COLOR_OUTPUT: bool = True
    EMOJI_ENABLED: bool = True
    DISPLAY_BANNER: bool = True
    
    # 菜单配置
    MAIN_MENU_OPTIONS: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"id": "sync", "name": "📡 数据同步", "description": "同步最新开奖数据", "color": "cyan"},
        {"id": "analyze", "name": "📊 数据分析", "description": "统计分析历史数据", "color": "green"},
        {"id": "predict", "name": "🎯 基础预测", "description": "预测下一期号码（6+1）", "color": "yellow"},
        {"id": "enhanced_predict", "name": "🚀 增强预测", "description": "增强预测（7+1, 8+1组合）", "color": "magenta"},
        {"id": "visualize", "name": "📈 数据可视化", "description": "生成可视化图表", "color": "blue"},
        {"id": "workflow", "name": "⚙️  完整运行", "description": "执行完整分析流程", "color": "white"},
        {"id": "system", "name": "🔧 系统信息", "description": "查看系统状态", "color": "gray"},
        {"id": "exit", "name": "❌ 退出系统", "description": "退出程序", "color": "red"}
    ])
    
    # 输出格式
    DATE_FORMAT: str = "%Y-%m-%d"
    TIME_FORMAT: str = "%H:%M:%S"
    NUMBER_FORMAT: str = "02d"  # 号码显示格式

@dataclass
class SystemConfig:
    """系统配置"""
    
    # 系统设置
    APP_NAME: str = "双色球智能分析系统"
    VERSION: str = "3.0.0"
    DEBUG: bool = False
    TEST_MODE: bool = False
    ENVIRONMENT: str = "production"  # production, development, testing
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_TO_FILE: bool = True
    LOG_TO_CONSOLE: bool = True
    
    # 性能配置
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600
    MAX_WORKERS: int = 4
    
    # 系统模块配置
    MODULES_ENABLED: Dict[str, bool] = field(default_factory=lambda: {
        'crawler': True,
        'database': True,
        'processor': True,
        'advanced_processor': True,
        'predictor': True,
        'statistics': True,
        'visualization': True,
        'display': True,
        'interactive': True,
        'workflow': True,
        'model_training': True,
        'export': True
    })
    
    # 系统安全
    DATA_VALIDATION: bool = True
    BACKUP_ON_ERROR: bool = True

@dataclass
class WorkflowConfig:
    """工作流程配置"""
    
    # 工作流程启用
    ENABLE_WORKFLOWS: bool = True
    
    # 数据处理流程
    DATA_PIPELINE_STEPS: List[str] = field(default_factory=lambda: [
        "data_validation",
        "data_cleaning",
        "feature_extraction",
        "feature_engineering"
    ])
    
    # 分析流程
    ANALYSIS_WORKFLOW_STEPS: List[str] = field(default_factory=lambda: [
        "basic_statistics",
        "frequency_analysis",
        "trend_analysis",
        "hot_cold_analysis",
        "pattern_recognition"
    ])
    
    # 预测流程
    PREDICTION_WORKFLOW_STEPS: List[str] = field(default_factory=lambda: [
        "data_preparation",
        "feature_selection",
        "model_prediction",
        "result_combination",
        "confidence_calculation"
    ])

class ConfigManager:
    """配置管理器 (单例模式)"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialize()
            self._initialized = True

    def _initialize(self):
        """初始化所有配置"""
        # 第一步：先设置基础日志，避免后续配置对象初始化时出错
        self._setup_basic_logging()

        # 第二步：创建配置对象
        self.paths = PathConfig()
        self.database = DatabaseConfig()
        self.crawler = CrawlerConfig()
        self.processor = ProcessorConfig()
        self.analysis = AnalysisConfig()
        self.prediction = PredictionConfig()
        self.model_training = ModelTrainingConfig()
        self.export = ExportConfig()
        self.ui = UIConfig()
        self.system = SystemConfig()
        self.workflow = WorkflowConfig()

        # 第三步：应用完整的日志配置
        self._setup_logging()

        logging.info(f"配置初始化完成，系统版本: {self.system.VERSION}")

    def _setup_basic_logging(self):
        """设置基础日志（不依赖任何配置对象）"""
        # 清空现有处理器
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # 添加简单的控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logging.root.addHandler(console_handler)
        logging.root.setLevel(logging.INFO)

    def _setup_logging(self):
        """设置完整的日志配置（依赖配置对象已创建）"""
        # 如果系统配置中指定了日志级别，则使用该级别
        log_level = getattr(logging, self.system.LOG_LEVEL)

        # 移除所有现有处理器
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # 创建格式化器
        formatter = logging.Formatter(self.system.LOG_FORMAT)

        # 文件处理器
        if self.system.LOG_TO_FILE:
            try:
                file_handler = logging.FileHandler(self.paths.MAIN_LOG, encoding='utf-8')
                file_handler.setLevel(log_level)
                file_handler.setFormatter(formatter)
                logging.root.addHandler(file_handler)
            except Exception as e:
                logging.warning(f"无法创建日志文件处理器: {e}")

        # 控制台处理器
        if self.system.LOG_TO_CONSOLE:
            console_handler = logging.StreamHandler()
            console_level = logging.DEBUG if self.system.DEBUG else log_level
            console_handler.setLevel(console_level)
            console_handler.setFormatter(formatter)
            logging.root.addHandler(console_handler)

        # 设置根日志级别
        logging.root.setLevel(log_level)

    def get_database_path(self) -> str:
        """获取数据库路径"""
        return self.paths.DATABASE_PATH

    def display_config_summary(self):
        """显示配置摘要"""
        print("\n" + "=" * 70)
        print(f"双色球分析系统 - 配置摘要 (版本 {self.system.VERSION})")
        print("=" * 70)

        print(f"\n📂 路径配置 (实际位置):")
        print(f"  项目根目录: {self.paths.BASE_DIR}")
        print(f"  数据库路径: {self.paths.DATABASE_PATH} ✅ (实际位置)")
        print(f"  报告目录: {self.paths.REPORTS_DIR} ✅ (实际位置)")
        print(f"  日志目录: {self.paths.LOGS_DIR}")

        print(f"\n📊 分析配置 (统一窗口命名):")
        print(f"  短期窗口: {self.analysis.SHORT_TERM_WINDOW} 期")
        print(f"  中期窗口: {self.analysis.MEDIUM_TERM_WINDOW} 期")
        print(f"  长期窗口: {self.analysis.LONG_TERM_WINDOW} 期")
        print(f"  热冷号窗口: {self.analysis.HOT_COLD_WINDOW} 期")

        print(f"\n🤖 预测配置:")
        print(f"  机器学习: {'✅ 启用' if self.prediction.ML_ENABLED else '❌ 禁用'}")
        print(f"  支持组合: {', '.join([k for k, v in self.prediction.MULTIPLE_COMBINATIONS.items() if v])}")

        print(f"\n🚀 系统配置:")
        print(f"  运行环境: {self.system.ENVIRONMENT}")
        print(f"  日志级别: {self.system.LOG_LEVEL}")

        print(f"\n📈 模块状态:")
        enabled_modules = [k for k, v in self.system.MODULES_ENABLED.items() if v]
        print(f"  启用模块: {len(enabled_modules)}/{len(self.system.MODULES_ENABLED)}")

        print("\n" + "=" * 70)
        print("💡 提示: 系统已使用统一窗口配置，新旧配置名称自动同步")

# 全局配置实例
config = ConfigManager()

if __name__ == "__main__":
    """直接运行config.py时显示配置信息"""
    config.display_config_summary()
    
    # 验证配置
    if config.paths.DATABASE_PATH and os.path.exists(config.paths.DATABASE_PATH):
        print(f"\n✅ 数据库文件存在: {config.paths.DATABASE_PATH}")
    else:
        print(f"\n⚠️  数据库文件不存在: {config.paths.DATABASE_PATH}")
        print("   首次运行前请先执行数据同步")
    
    print(f"\n🎯 系统名称: {config.system.APP_NAME}")
    print(f"📅 初始化时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")