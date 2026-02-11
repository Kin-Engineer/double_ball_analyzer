# main.py
#!/usr/bin/env python3
"""
双色球增强预测系统 - 主入口（重构版）
"""
import sys
import os
import argparse
import logging
from datetime import datetime
from utils.window_config import WindowConfigManager

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from ui.interactive import InteractiveManager
from workflows.full_analysis import run_full_analysis_workflow
from workflows.prediction_workflow import run_prediction_workflow
from workflows.data_pipeline import run_data_pipeline
from services.prediction_service import get_prediction_service
from services.analysis_service import get_analysis_service  # 添加这行
from utils.color_utils import print_colored_banner, print_success, print_error, print_info
from utils.logger import setup_logger


def setup_environment():
    """设置环境"""
    # 确保目录存在
    os.makedirs("logs", exist_ok=True)
    os.makedirs("visualizations", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    # 设置日志
    setup_logger('double_ball_analyzer', 
                log_file=f"logs/double_ball_{datetime.now().strftime('%Y%m%d')}.log",
                level=logging.INFO)

def main():
    """主函数"""
    from config import config
    parser = argparse.ArgumentParser(description='双色球增强预测系统')
    parser.add_argument('--mode', choices=['interactive', 'full', 'predict', 'analyze', 'data', 'sync'], 
                       default='interactive', help='运行模式')
    parser.add_argument('--db', type=str, default=config.paths.DATABASE_PATH, help='数据库路径')
    parser.add_argument('--force-update', action='store_true', help='强制更新数据')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    # 设置环境
    setup_environment()
    
    # 打印横幅 - 修复：添加横幅文本参数
    print_colored_banner("双色球增强预测系统 v3.0")
    
    try:
        if args.mode == 'interactive':
            # 交互模式
            print_info("启动交互模式...")
            manager = InteractiveManager(args.db)
            manager.run()
            
        elif args.mode == 'full':
            # 完整分析模式
            print_info("运行完整分析流程...")
            result = run_full_analysis_workflow(args.db)
            if 'error' in result:
                print_error(f"分析失败: {result['error']}")
            else:
                print_success("完整分析完成")
                
        elif args.mode == 'predict':
            # 预测模式
            print_info("运行预测流程...")
            result = run_prediction_workflow(args.db)
            if 'error' in result:
                print_error(f"预测失败: {result['error']}")
            else:
                print_success("预测完成")
                # 显示预测结果
                try:
                    from ui.display import display_full_prediction_report
                    display_full_prediction_report(result)
                except ImportError:
                    # 如果新函数不存在，回退到旧函数
                    from ui.display import display_prediction_result
                    display_prediction_result({'predictions': result.get('predictions', {})})
                
        elif args.mode == 'analyze':
            # 分析模式 - 修改为调用分析服务
            print_info("运行数据分析...")
            
            # 获取分析服务
            analysis_service = get_analysis_service(args.db)
            
            # 从配置获取分析窗口
            try:
                # 使用统一的WindowConfigManager
                from utils.window_config import WindowConfigManager
                window = WindowConfigManager.get_window_by_name('short_term')
            except (ImportError, AttributeError):
                # 如果无法导入WindowConfigManager，尝试从config获取
                try:
                    from config import config
                    window = config.analysis.TREND_ANALYSIS_WINDOW
                except:
                    window = WindowConfigManager.get_window_by_name('short_term')  # 使用默认值
            
            # 获取分析结果
            analysis = analysis_service.get_comprehensive_analysis(window)
            
            if 'error' in analysis:
                print_error(f"分析失败: {analysis['error']}")
            else:
                # 显示详细分析报告
                report = analysis_service.get_detailed_analysis_report(window)
                print(f"\n{report}")
                
                # 显示补充统计信息
                print(f"\n=== 补充统计信息 ===")
                
                # 热冷号分析
                if 'hot_cold' in analysis:
                    hot_cold = analysis['hot_cold']
                    hot_reds = hot_cold.get('hot_reds', [])
                    warm_reds = hot_cold.get('warm_reds', [])
                    cold_reds = hot_cold.get('cold_reds', [])
                    
                    if hot_reds:
                        print_info(f"热门号码 ({len(hot_reds)}个): {sorted(hot_reds)}")
                    if warm_reds:
                        print_info(f"温门号码 ({len(warm_reds)}个): {sorted(warm_reds)}")
                    if cold_reds:
                        print_info(f"冷门号码 ({len(cold_reds)}个): {sorted(cold_reds)}")
                
                # 趋势分析
                if 'trends' in analysis:
                    trends = analysis['trends']
                    print_info(f"和值趋势: {trends.get('sum_trend', '未知')}")
                    
        elif args.mode == 'data':
            # 数据处理模式
            print_info("运行数据处理流程...")
            result = run_data_pipeline(args.db, args.force_update)
            if 'error' in result:
                print_error(f"数据处理失败: {result['error']}")
            else:
                print_success("数据处理完成")
                
        elif args.mode == 'sync':
            # 数据同步模式
            print_info("运行数据同步...")
            from data.database import DoubleBallDatabase
            from data.crawler import DoubleBallCrawler

            # 使用 args.db（已在 main.py 中设置为 config.paths.DATABASE_PATH）
            db = DoubleBallDatabase(args.db)
            crawler = DoubleBallCrawler(db)
            result = crawler.sync_all_data_incremental(args.force_update)
            print_success(f"数据同步完成: {result.get('new_records', 0)} 条新记录")
        
        print_success("程序执行完成")

    except KeyboardInterrupt:
        print_info("\n用户中断程序")
    except Exception as e:
        print_error(f"程序执行出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
