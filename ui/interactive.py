# ui/interactive.py
"""
交互管理
"""
import sys
from typing import Dict, Any
from utils.window_config import WindowConfigManager

from ui.display import display_menu, display_system_info, display_prediction_result
from services.prediction_service import get_prediction_service
from services.analysis_service import get_analysis_service
from utils.color_utils import *

class InteractiveManager:
    """交互管理器"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # 使用 config.py 中的路径
            from config import config
            db_path = config.paths.DATABASE_PATH
        # # 使用数据库管理器获取数据库实例
        # from utils.db_manager import DatabaseManager
        # db_manager = DatabaseManager()
        # db = db_manager.get_db(db_path)
        # 直接获取服务，不需要在这里创建数据库连接
        self.prediction_service = get_prediction_service(db_path)
        self.analysis_service = get_analysis_service(db_path)

        self.menu_options = [
            {"id": "predict", "name": "预测分析", "description": "进行号码预测"},
            {"id": "analyze", "name": "数据分析", "description": "统计分析历史数据"},
            {"id": "system", "name": "系统信息", "description": "查看系统状态"},
            {"id": "visualize", "name": "可视化", "description": "生成可视化图表"},
            {"id": "sync", "name": "数据同步", "description": "同步最新开奖数据"},
            {"id": "exit", "name": "退出", "description": "退出程序"}
        ]

    def run(self):
        """运行交互界面"""
        from ui.display import print_colored_banner
        print_colored_banner()

        while True:
            try:
                choice = display_menu(self.menu_options)

                if choice == '1':
                    self.handle_prediction()
                elif choice == '2':
                    self.handle_analysis()
                elif choice == '3':
                    self.handle_system_info()
                elif choice == '4':
                    self.handle_visualization()
                elif choice == '5':
                    self.handle_sync()
                elif choice.lower() == 'exit' or choice == '6':
                    print_success("感谢使用，再见！")
                    break
                else:
                    print_warning("无效选择，请重新输入")

            except KeyboardInterrupt:
                print_warning("\n用户中断")
                break
            except Exception as e:
                print_error(f"操作失败: {e}")

    # 文件：ui/interactive.py
    # 修改 handle_prediction 方法

    def handle_prediction(self):
        """处理预测"""
        print_info("开始预测分析...")
        result = self.prediction_service.run_enhanced_prediction()

        # 检查是否有错误
        if 'error' in result:
            print_error(f"❌ 预测失败: {result['error']}")
            return

        display_prediction_result(result)

        # 询问是否保存报告
        save = input(f"\n{C}是否保存详细报告? (y/n): {RS}").lower()
        if save == 'y':
            try:
                print_info("正在保存报告...")

                # 调用保存方法
                save_result = self.prediction_service.save_report_to_file(result)

                # 处理返回结果
                if isinstance(save_result, dict):
                    if save_result.get('success'):
                        filepath = save_result.get('filepath', '未知路径')
                        size = save_result.get('size', 0)
                        print_success(f"✅ 预测报告保存成功！")
                        print_info(f"   文件路径: {filepath}")
                        print_info(f"   文件大小: {size} 字节")

                        # 新增：询问是否查看报告内容
                        view_report = input(f"\n{C}是否查看报告内容? (y/n): {RS}").lower()
                        if view_report == 'y':
                            try:
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    print("\n" + "=" * 60)
                                    print("📄 报告内容预览:")
                                    print("=" * 60)
                                    # 预览前30行内容
                                    lines = content.split('\n')
                                    for i, line in enumerate(lines[:30]):
                                        print(line)
                                    if len(lines) > 30:
                                        print(f"... (共{len(lines)}行，完整内容请查看文件)")
                                        show_all = input(f"\n{C}是否显示完整内容? (y/n): {RS}").lower()
                                        if show_all == 'y':
                                            print("\n" + "=" * 60)
                                            print("📄 完整报告内容:")
                                            print("=" * 60)
                                            print(content)
                                            print("=" * 60)
                            except Exception as e:
                                print_error(f"❌ 读取报告失败: {e}")

                        # 可选：询问是否打开文件
                        if size > 0:
                            open_file = input(f"\n{C}是否打开报告文件? (y/n): {RS}").lower()
                            if open_file == 'y':
                                try:
                                    import os
                                    os.startfile(filepath)
                                    print_success("✅ 已打开报告文件")
                                except:
                                    print_info(f"📄 您可以在以下位置查看报告: {filepath}")
                    else:
                        print_error(f"❌ 保存失败: {save_result.get('error', '未知错误')}")
                elif isinstance(save_result, str):
                    print_success(f"✅ 报告已保存: {save_result}")
                else:
                    print_warning(f"⚠️ 保存返回未知格式: {type(save_result)}")

            except KeyboardInterrupt:
                print_warning("\n用户取消保存")
            except Exception as e:
                print_error(f"❌ 保存报告时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            print_info("已跳过保存报告")

    def handle_analysis(self):
        """处理分析"""
        print_info("开始数据分析...")

        try:
            # 使用WindowConfigManager获取短期窗口
            from utils.window_config import WindowConfigManager
            window = WindowConfigManager.get_window_by_name('short_term')
            print_info(f"分析窗口: {window}期")
        except (ImportError, AttributeError):
            # 如果WindowConfigManager失败，尝试从config获取
            try:
                from config import config
                window = config.analysis.TREND_ANALYSIS_WINDOW
                print_info(f"分析窗口: {window}期")
            except:
                # 最后使用WindowConfigManager的默认值
                window = WindowConfigManager.get_window_by_name('short_term')
                print_warning(f"使用默认窗口: {window}期")

        try:
            # 获取详细分析报告
            report = self.analysis_service.get_detailed_analysis_report(window)
            if report:
                print(f"\n{report}")
            else:
                print_warning("分析报告为空，可能没有数据或分析失败")

            # 同时获取分析数据用于显示补充信息
            analysis = self.analysis_service.get_comprehensive_analysis(window)

            # 检查是否有错误
            if 'error' in analysis:
                print_error(f"分析数据获取失败: {analysis['error']}")
                return

            # 显示额外统计信息（如果报告中没有包含）
            print(f"\n{G}=== 补充统计信息 ==={RS}")

            # 红球分布统计
            if 'statistics' in analysis and analysis['statistics']:
                stats = analysis['statistics']
                if 'red_distribution' in stats and stats['red_distribution']:
                    red_dist = stats['red_distribution']
                    # 显示出现次数最多的红球
                    sorted_reds = sorted(red_dist.items(), key=lambda x: x[1], reverse=True)[:10]
                    print(f"{B}📊 高频红球 (前10):{RS}")
                    for ball, count in sorted_reds:
                        print(f"  红球 {ball:02d}: {count}次 ({count/window*100:.1f}%)")

                # 蓝球分布统计
                if 'blue_distribution' in stats and stats['blue_distribution']:
                    blue_dist = stats['blue_distribution']
                    if blue_dist:
                        sorted_blues = sorted(blue_dist.items(), key=lambda x: x[1], reverse=True)[:5]
                        print(f"{C}📊 高频蓝球 (前5):{RS}")
                        for ball, count in sorted_blues:
                            print(f"  蓝球 {ball:02d}: {count}次 ({count/window*100:.1f}%)")

            # 询问用户是否查看其他分析
            print(f"\n{Y}是否查看其他分析?{RS}")
            print("  1. 重号概率分析")
            print("  2. 组合概率分析")
            print("  3. 单个球趋势分析")
            print("  4. 返回主菜单")

            sub_choice = input(f"\n{C}请选择 (1-4): {RS}").strip()

            if sub_choice == '1':
                self.handle_repeat_probability_analysis()
            elif sub_choice == '2':
                self.handle_combination_probability_analysis()
            elif sub_choice == '3':
                self.handle_individual_ball_trend_analysis()
            else:
                return

        except Exception as e:
            print_error(f"数据分析失败: {e}")
            print_info("尝试检查数据库是否有足够的数据")

    def handle_individual_ball_trend_analysis(self):
        """处理单个球趋势分析"""
        try:
            print_info("获取单个球趋势分析...")

            # 获取整体趋势分析
            trend_analysis = self.analysis_service.get_individual_ball_trend_analysis()

            if 'error' in trend_analysis:
                print_error(f"单个球趋势分析失败: {trend_analysis['error']}")
                return

            print(f"\n{G}=== 单个球出现趋势分析 ==={RS}")

            # 显示热门趋势
            summary = trend_analysis.get('trend_analysis', {}).get('summary', {})

            if summary.get('increasing_reds'):
                print(f"{Y}📈 出现频率递增的红球 ({len(summary['increasing_reds'])}个):{RS}")
                print(f"  {', '.join([f'{ball:02d}' for ball in summary['increasing_reds']])}")

            if summary.get('decreasing_reds'):
                print(f"{Y}📉 出现频率递减的红球 ({len(summary['decreasing_reds'])}个):{RS}")
                print(f"  {', '.join([f'{ball:02d}' for ball in summary['decreasing_reds']])}")

            if summary.get('hot_reds'):
                print(f"{R}🔥 热门红球 ({len(summary['hot_reds'])}个):{RS}")
                print(f"  {', '.join([f'{ball:02d}' for ball in summary['hot_reds']])}")

            if summary.get('cold_reds'):
                print(f"{B}❄️  冷门红球 ({len(summary['cold_reds'])}个):{RS}")
                print(f"  {', '.join([f'{ball:02d}' for ball in summary['cold_reds']])}")

            # 询问是否查看具体球的趋势
            print(f"\n{C}是否查看具体球的详细趋势? (y/n): {RS}")
            view_detail = input().lower()

            if view_detail == 'y':
                print(f"\n{Y}请选择球类型:{RS}")
                print("  1. 红球")
                print("  2. 蓝球")

                ball_type_choice = input(f"{C}请选择 (1-2): {RS}").strip()

                if ball_type_choice == '1':
                    ball_type = "red"
                    max_ball = 33
                elif ball_type_choice == '2':
                    ball_type = "blue"
                    max_ball = 16
                else:
                    return

                print(f"\n{Y}请输入要分析的球号 (1-{max_ball}):{RS}")
                try:
                    ball_number = int(input(f"{C}球号: {RS}").strip())

                    if not (1 <= ball_number <= max_ball):
                        print_error(f"球号必须在1-{max_ball}之间")
                        return

                    # 获取该球的趋势报告
                    report = self.analysis_service.get_ball_trend_report(ball_type, ball_number)
                    print(f"\n{report}")

                except ValueError:
                    print_error("请输入有效的数字")

        except Exception as e:
            print_error(f"单个球趋势分析失败: {e}")

    def handle_repeat_probability_analysis(self):
        """处理重号概率分析"""
        try:
            print_info("获取重号概率分析...")
            result = self.analysis_service.get_repeat_probability_analysis()

            if 'error' in result:
                print_error(f"重号概率分析失败: {result['error']}")
                return

            print(f"\n{G}=== 重号概率分析 ==={RS}")

            if 'repeat_probabilities' in result:
                probs = result['repeat_probabilities']
                print(f"{Y}重号数量概率分布:{RS}")
                for count, prob in sorted(probs.items()):
                    print(f"  {count}个重号: {prob * 100:.1f}%")

            if 'total_pairs' in result:
                print(f"\n{B}统计基础:{RS}")
                print(f"  分析期数对: {result['total_pairs']}")

        except Exception as e:
            print_error(f"重号概率分析失败: {e}")

    def handle_combination_probability_analysis(self):
        """处理组合概率分析"""
        try:
            from config import config
            window = WindowConfigManager.get_window_by_name('short_term')
        except (ImportError, AttributeError):
            window = 30

        try:
            print_info(f"获取组合概率分析 (窗口: {window}期)...")
            result = self.analysis_service.get_combination_probability(window)

            if 'error' in result:
                print_error(f"组合概率分析失败: {result['error']}")
                return

            print(f"\n{G}=== 组合概率分析 ==={RS}")

            if 'pair_probabilities' in result:
                probs = result['pair_probabilities']
                print(f"{Y}高频组合 (前10):{RS}")
                for pair_name, data in list(probs.items())[:10]:
                    count = data.get('count', 0)
                    probability = data.get('probability', 0)
                    print(f"  组合 {pair_name}: {count}次 ({probability * 100:.1f}%)")

            if 'total_games' in result:
                print(f"\n{B}统计基础:{RS}")
                print(f"  分析期数: {result['total_games']}")

        except Exception as e:
            print_error(f"组合概率分析失败: {e}")


    def handle_system_info(self):
        """处理系统信息"""
        info = self.prediction_service.get_system_info()
        display_system_info(info)

    def handle_visualization(self):
        """处理可视化"""
        from analysis.visualization import get_visualizer
        print_info("开始生成可视化图表...")
        visualizer = get_visualizer()
        success = visualizer.create_all_visualizations()
        if success:
            print_success("可视化图表生成完成，保存到 visualizations/ 目录")
        else:
            print_error("可视化图表生成失败")

    def handle_sync(self):
        """处理数据同步"""
        print_warning("数据同步功能需要单独运行 data_sync.py")
        print_info("您可以在命令行运行: python data_sync.py")

        confirm = input(f"\n{C}是否现在运行数据同步? (y/n): {RS}").lower()
        if confirm == 'y':
            import subprocess
            try:
                # 获取当前使用的数据库路径
                import config
                db_path = config.config.paths.DATABASE_PATH

                # 使用正确的数据库路径运行同步
                subprocess.run([sys.executable, "data_sync.py", "--db", db_path], check=True)
                print_success("数据同步完成")
            except Exception as e:
                print_error(f"数据同步失败: {e}")

def main():
    """主函数"""
    manager = InteractiveManager()
    manager = InteractiveManager("data/double_ball.db")
    manager.run()

if __name__ == "__main__":
    main()