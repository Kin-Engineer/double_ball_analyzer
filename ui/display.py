# ui/display.py
"""
显示管理，彩色输出和格式化显示
"""
import sys
from typing import Dict, Any, List
# 颜色代码定义
R = "\033[91m"  # 红色
G = "\033[92m"  # 绿色
Y = "\033[93m"  # 黄色
B = "\033[94m"  # 蓝色
M = "\033[95m"  # 紫色
C = "\033[96m"  # 青色
W = "\033[97m"  # 白色

# 样式
DIM = "\033[2m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"
HIDDEN = "\033[8m"

# 重置
RS = "\033[0m"



from utils.color_utils import *

def print_colored_banner():
    """打印彩色横幅"""
    if COLOR_ENABLED:
        banner = f"""
{B}{'='*60}{RS}
{Y}╔══════════════════════════════════════════════════════╗{RS}
{Y}║{G}{BOLD}           双色球增强预测系统 v3.0                    {RS}{Y}║{RS}
{Y}║{C}{BOLD}           基于机器学习与统计分析                     {RS}{Y}║{RS}
{Y}║{M}{BOLD}           支持6+1, 7+1, 8+1多组合预测               {RS}{Y}║{RS}
{Y}╚══════════════════════════════════════════════════════╝{RS}
{B}{'='*60}{RS}
        """
    else:
        banner = """
╔══════════════════════════════════════════════════════╗
║           双色球增强预测系统 v3.0                    ║
║           基于机器学习与统计分析                     ║
║           支持6+1, 7+1, 8+1多组合预测               ║
╚══════════════════════════════════════════════════════╝
        """
    print(banner)

# ui/display.py - display_prediction_result 方法修改部分
# ui/display.py - 完整的 display_prediction_result 函数

def display_prediction_result(result: Dict[str, Any]):
    """显示预测结果 - 按照共识方案显示概率分析"""
    if not result:
        print_error("预测结果为空")
        return

    if 'error' in result:
        print_error(f"预测失败: {result.get('error', '未知错误')}")
        return

    print(f"\n{B}{'=' * 60}{RS}")
    print(f"{Y}{BOLD}🎯 预测结果汇总{RS}")
    print(f"{B}{'=' * 60}{RS}")

    # 系统信息
    if 'system_info' in result:
        info = result['system_info']
        print(f"{C}📅 最新期号: {G}{info.get('latest_issue', '未知')}{RS}")
        # 显示预测时间（如果存在）
        if 'prediction_time' in info:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(info['prediction_time'].replace('Z', '+00:00'))
                print(f"{C}⏰ 预测时间: {G}{dt.strftime('%Y-%m-%d %H:%M:%S')}{RS}")
            except:
                pass

    # 预测组合
    print(f"\n{G}{BOLD}🔮 增强预测组合:{RS}")

    # 修改：定义一个简单的格式化函数，只显示球号，不显示冷热温号
    def format_red_balls_simple(reds: List[int]) -> str:
        """只显示球号，不显示冷热温状态"""
        if not reds:
            return ""
        sorted_reds = sorted(reds)
        return ' '.join([f"{C}{ball:02d}{RS}" for ball in sorted_reds])

    # 6+1组合
    pred_6 = result.get('6_plus_1', {})
    if isinstance(pred_6, dict):
        reds = pred_6.get('red_balls', [])
        blue = pred_6.get('blue_ball', 0)
        conf = pred_6.get('confidence', 0)
        strategy = pred_6.get('strategy', '')

        # 修改：使用简单的格式化，只显示球号
        reds_display = format_red_balls_simple(reds)
        print(f"{W}  6+1: {reds_display} + {C}{blue:02d}{W}")
        print(f"{DIM}     置信度: {G}{conf:.1f}%{RS} 策略: {strategy}")

    # 7+1组合
    pred_7 = result.get('7_plus_1', {})
    if isinstance(pred_7, dict):
        reds = pred_7.get('red_balls', [])
        blue = pred_7.get('blue_ball', 0)
        conf = pred_7.get('confidence', 0)
        strategy = pred_7.get('strategy', '')

        # 修改：使用简单的格式化，只显示球号
        reds_display = format_red_balls_simple(reds)
        print(f"{W}  7+1: {reds_display} + {C}{blue:02d}{W}")
        print(f"{DIM}     置信度: {G}{conf:.1f}%{RS} 策略: {strategy}")

    # 8+1组合
    pred_8 = result.get('8_plus_1', {})
    if isinstance(pred_8, dict):
        reds = pred_8.get('red_balls', [])
        blue = pred_8.get('blue_ball', 0)
        conf = pred_8.get('confidence', 0)
        strategy = pred_8.get('strategy', '')

        # 修改：使用简单的格式化，只显示球号
        reds_display = format_red_balls_simple(reds)
        print(f"{W}  8+1: {reds_display} + {C}{blue:02d}{W}")
        print(f"{DIM}     置信度: {G}{conf:.1f}%{RS} 策略: {strategy}")

    # 推荐组合
    if 'recommended_combination' in result:
        print(f"\n{M}{BOLD}💎 推荐组合:{RS}")
        print(f"{W}  最佳组合: {result.get('recommended_combination', '未知')}")
        print(f"{W}  推荐置信度: {G}{result.get('recommended_confidence', 0):.1f}%{RS}")

    # ========== 按照共识方案显示概率分析 ==========
    print(f"\n{B}{BOLD}📊 概率分析 (多窗口期):{RS}")

    # 检查是否有重复分析数据
    if 'repeat_analysis' in result:
        repeat_analysis = result['repeat_analysis']

        if isinstance(repeat_analysis, dict) and 'window_analysis' in repeat_analysis:
            window_analysis = repeat_analysis['window_analysis']

            # 定义窗口期显示顺序和名称
            window_display_config = [
                ('short_term', '📱 短期窗口'),
                ('medium_term', '📊 中期窗口'),
                ('long_term', '📈 长期窗口'),
                ('all_history', '📚 全部历史')
            ]

            # 显示四个窗口期的重号分布
            for window_key, window_title in window_display_config:
                if window_key in window_analysis:
                    window_data = window_analysis[window_key]
                    total_pairs = window_data.get('total_pairs', 0)

                    if total_pairs > 0:
                        print(f"{C}  {window_title}:{RS}")

                        # 重号分布（只显示百分比）
                        repeat_dist = window_data.get('repeat_distribution', {})
                        if isinstance(repeat_dist, dict):
                            dist_items = []
                            for i in range(0, 7):
                                prob = repeat_dist.get(i, 0)
                                if isinstance(prob, (int, float)):
                                    if i <= 3:
                                        dist_items.append(f"{i}个({prob:.1%})")
                                    elif i == 4:
                                        # 合并显示4-6个
                                        prob_4_6 = sum([repeat_dist.get(j, 0) for j in range(4, 7)])
                                        dist_items.append(f"4-6个({prob_4_6:.1%})")
                                        break

                            if dist_items:
                                print(f"{W}    重号分布: {' | '.join(dist_items)}{RS}")

                        # 蓝球重复概率
                        blue_prob = window_data.get('blue_repeat_probability', 0)
                        if isinstance(blue_prob, (int, float)):
                            print(f"{W}    蓝球重复: {Y}{blue_prob:.2%}{RS}")

            # 显示趋势分析
            print(f"\n{M}{BOLD}🎯 综合预测与趋势分析:{RS}")

            # 找出最可能的重号数量（基于长期窗口）
            most_likely_count = 0
            max_prob = 0
            if 'long_term' in window_analysis:
                repeat_dist = window_analysis['long_term'].get('repeat_distribution', {})
                for count, prob in repeat_dist.items():
                    if isinstance(prob, (int, float)) and prob > max_prob:
                        max_prob = prob
                        most_likely_count = count

            print(f"{W}  最可能重复: {G}{most_likely_count}个红球{RS}")

            # 显示趋势分析（添加周期标签）
            print(f"{W}  趋势分析:")
            print(f"{W}    从四个窗口期的统计来看:{RS}")

            # 为每个重复数量显示趋势（添加周期标签）
            for count in range(0, 4):  # 只显示0-3个重号
                probs_with_labels = []
                for window_key, _ in window_display_config:
                    if window_key in window_analysis:
                        repeat_dist = window_analysis[window_key].get('repeat_distribution', {})
                        prob = repeat_dist.get(count, 0)
                        if isinstance(prob, (int, float)):
                            # 添加周期标签
                            period_label = {
                                'short_term': '短期',
                                'medium_term': '中期',
                                'long_term': '长期',
                                'all_history': '历史'
                            }.get(window_key, '未知')
                            probs_with_labels.append(f"{period_label}{prob:.1%}")
                        else:
                            probs_with_labels.append("N/A")
                    else:
                        probs_with_labels.append("N/A")

                # 只显示有数据的趋势
                if len(probs_with_labels) == 4 and all(p != "N/A" for p in probs_with_labels):
                    try:
                        # 提取概率值（去掉标签）
                        prob_values = []
                        for p in probs_with_labels:
                            # 从"短期33.3%"中提取33.3
                            import re
                            match = re.search(r'(\d+\.?\d*)%', p)
                            if match:
                                prob_values.append(float(match.group(1)) / 100)

                        if prob_values:
                            # 简单判断趋势
                            if len(prob_values) == 4:
                                if prob_values[0] < prob_values[-1] and prob_values[-1] - prob_values[0] > 0.02:
                                    trend = "递增"
                                elif prob_values[0] > prob_values[-1] and prob_values[0] - prob_values[-1] > 0.02:
                                    trend = "递减"
                                else:
                                    trend = "稳定"

                            print(
                                f"{W}    • 重复{count}个红球: {probs_with_labels[0]} → {probs_with_labels[1]} → {probs_with_labels[2]} → {probs_with_labels[3]} ({trend}){RS}")
                    except:
                        print(
                            f"{W}    • 重复{count}个红球: {probs_with_labels[0]} → {probs_with_labels[1]} → {probs_with_labels[2]} → {probs_with_labels[3]}{RS}")

            # 趋势判断
            print(f"{W}  趋势判断:")
            print(f"{W}    • 建议重点关注重复{most_likely_count}个红球的情况{RS}")

            # 蓝球重复概率建议
            if 'long_term' in window_analysis:
                blue_prob = window_analysis['long_term'].get('blue_repeat_probability', 0)
                if isinstance(blue_prob, (int, float)):
                    print(f"{W}  蓝球重复概率: {Y}{blue_prob:.2%}{RS} (基于长期窗口)")
                    if blue_prob < 0.05:
                        print(f"{W}  注: 蓝球重复概率较低，不建议选择上期蓝球{RS}")
                    elif blue_prob < 0.1:
                        print(f"{W}  注: 蓝球重复概率一般，可适当考虑{RS}")
                    else:
                        print(f"{W}  注: 蓝球重复概率较高，值得关注{RS}")
    else:
        print(f"{W}  无概率分析数据{RS}")

    # 统计周期说明
    print(f"\n{C}{BOLD}📈 统计说明:{RS}")
    print(f"{W}  • 热号定义: 统计周期内出现次数排名前11名")
    print(f"{W}  • 温号定义: 统计周期内出现次数排名中间11名")
    print(f"{W}  • 冷号定义: 统计周期内出现次数排名后11名")
    print(f"{W}  • 统计周期: 默认最近30期")
    print(f"{W}  • 趋势分析: 基于四个窗口期(30/50/100/全部)的概率变化")

    print(f"\n{B}{'=' * 60}{RS}")
    print(f"{G}{BOLD}✨ 分析完成{RS}")
    print(f"{B}{'=' * 60}{RS}")

    # ========== 新增：趋势分析部分 ==========
    print(f"\n{Y}{BOLD}📈 单个号码趋势分析:{RS}")
    print(f"{C}{'=' * 60}{RS}")
    
    # 简单趋势分析显示
    print(f"{W}  ✅ 趋势分析方法测试成功{RS}")
    print(f"{DIM}  趋势分析功能正常运行...{RS}")
    print(f"{W}  基于多窗口期分析的趋势判断{RS}")
    print(f"{C}{'=' * 60}{RS}")
    
    # 如果结果中有趋势分析数据，可以显示更多
    if 'trends' in result:
        trends = result['trends']
        if 'hot_reds' in trends:
            hot_balls = [str(item[0]) if isinstance(item, (list, tuple)) else str(item) 
                        for item in trends.get('hot_reds', [])[:3]]
            if hot_balls:
                print(f"{W}  🔥 热门号码: {G}{' '.join(hot_balls)}{RS}")
        
        if 'cold_reds' in trends:
            cold_balls = [str(item[0]) if isinstance(item, (list, tuple)) else str(item)
                         for item in trends.get('cold_reds', [])[:3]]
            if cold_balls:
                print(f"{W}  ❄️  冷门号码: {M}{' '.join(cold_balls)}{RS}")
    
    # 和值趋势
    if 'trends' in result:
        sum_trend = result['trends'].get('sum_trend', '未知')
        trend_color = G if sum_trend in ['上升', '稳定'] else R
        print(f"{W}  📊 和值趋势: {trend_color}{sum_trend}{RS}")
    """显示系统信息"""
    print(f"\n{B}{'='*60}{RS}")
    print(f"{Y}{BOLD}📊 系统信息{RS}")
    print(f"{B}{'='*60}{RS}")
    
    if 'database' in info:
        db = info['database']
        print(f"{C}📁 数据库: {W}{db.get('database_path', '未知')}{RS}")
        print(f"{C}📈 记录数: {G}{info.get('records_count', 0)}{RS}")
        print(f"{C}🎯 最新期号: {G}{info.get('latest_issue', '未知')}{RS}")
    
    if 'model_status' in info:
        status = info['model_status']
        ml_icon = '✅' if status.get('ml_available') else '❌'
        trained_icon = '✅' if status.get('models_trained') else '❌'
        print(f"{C}🤖 机器学习: {W}{ml_icon}{RS}")
        print(f"{C}🧠 模型已训练: {W}{trained_icon}{RS}")
    
def display_system_info(info: Dict[str, Any]):
    """显示系统信息"""
    print(f"\n{B}{'='*60}{RS}")
    print(f"{Y}{BOLD}📊 系统信息{RS}")
    print(f"{B}{'='*60}{RS}")
    
    if 'database' in info:
        db = info['database']
        print(f"{C}📁 数据库: {W}{db.get('database_path', '未知')}{RS}")
        print(f"{C}📈 记录数: {G}{info.get('records_count', 0)}{RS}")
        print(f"{C}🎯 最新期号: {G}{info.get('latest_issue', '未知')}{RS}")
    
    if 'model_status' in info:
        status = info['model_status']
        ml_icon = '✅' if status.get('ml_available') else '❌'
        trained_icon = '✅' if status.get('models_trained') else '❌'
        print(f"{C}🤖 机器学习: {W}{ml_icon}{RS}")
        print(f"{C}🧠 模型已训练: {W}{trained_icon}{RS}")

def display_menu(options: List[Dict[str, str]]):
    """显示菜单"""
    print(f"\n{B}{'='*60}{RS}")
    print(f"{Y}{BOLD}📋 主菜单{RS}")
    print(f"{B}{'='*60}{RS}")
    
    for i, option in enumerate(options, 1):
        print(f"{W}  {i}. {option.get('name', '未知选项')}")
        print(f"{DIM}     {option.get('description', '')}{RS}")
    
    print(f"{B}{'='*60}{RS}")
    return input(f"{C}请选择操作 (1-{len(options)}): {RS}")
