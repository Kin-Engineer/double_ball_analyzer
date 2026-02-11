# analysis/visualization.py
"""
数据可视化模块，从double_ball_master.py提取
"""
import logging
import os
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import rcParams
import numpy as np
from collections import Counter
from typing import List, Optional

from data.models import DoubleBallRecord
from data.database import DoubleBallDatabase

logger = logging.getLogger('visualization')

# 设置中文字体
plt.style.use('seaborn-v0_8-darkgrid')
rcParams['figure.figsize'] = (12, 8)
rcParams['font.sans-serif'] = ['SimHei', 'Arial']
rcParams['axes.unicode_minus'] = False

class Visualization:
    """可视化类"""
    
    def __init__(self, database: DoubleBallDatabase):
        self.db = database
    
    def plot_red_ball_frequency(self, save_path: Optional[str] = None) -> plt.Figure:
        """绘制红球频率分布图"""
        records = self.db.get_all_records()
        if not records:
            logger.warning("没有数据用于可视化")
            return None
        
        # 统计所有红球出现次数
        red_counts = Counter()
        for record in records:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            for ball in reds:
                red_counts[ball] += 1
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(15, 6))
        
        # 柱状图
        balls = list(range(1, 34))
        counts = [red_counts.get(ball, 0) for ball in balls]
        
        colors = ['red' if count > np.mean(counts) else 'lightcoral' for count in counts]
        ax.bar(balls, counts, color=colors, alpha=0.7)
        ax.set_xlabel('红球号码')
        ax.set_ylabel('出现次数')
        ax.set_title('红球历史出现频率')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加平均线
        avg_count = np.mean(counts)
        ax.axhline(y=avg_count, color='blue', linestyle='--', alpha=0.5, label=f'平均: {avg_count:.1f}')
        ax.legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_blue_ball_frequency(self, save_path: Optional[str] = None) -> plt.Figure:
        """绘制蓝球频率分布图"""
        records = self.db.get_all_records()
        if not records:
            logger.warning("没有数据用于可视化")
            return None
        
        blue_counts = Counter(record.blue for record in records)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 柱状图
        balls = list(range(1, 17))
        counts = [blue_counts.get(ball, 0) for ball in balls]
        
        colors = ['blue' if count > np.mean(counts) else 'lightblue' for count in counts]
        bars = ax.bar(balls, counts, color=colors, alpha=0.7)
        ax.set_xlabel('蓝球号码')
        ax.set_ylabel('出现次数')
        ax.set_title('蓝球历史出现频率')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 在柱子上方添加数值
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{count}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def plot_time_series(self, save_path: Optional[str] = None) -> plt.Figure:
        """绘制时间序列分析图"""
        records = self.db.get_all_records(limit=200)  # 限制200期避免图太密
        if not records:
            logger.warning("没有数据用于可视化")
            return None
        
        # 计算红球和值
        red_sums = []
        odd_counts = []
        issues = []
        
        for record in records:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            red_sums.append(sum(reds))
            odd_counts.append(sum(1 for ball in reds if ball % 2 == 1))
            issues.append(int(record.issue))
        
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))
        
        # 1. 红球和值时间序列
        axes[0].plot(issues, red_sums, 'b-', alpha=0.7, linewidth=1)
        axes[0].set_xlabel('期号')
        axes[0].set_ylabel('红球和值')
        axes[0].set_title('红球和值时间序列')
        axes[0].grid(True, alpha=0.3)
        
        # 添加移动平均线
        if len(red_sums) >= 20:
            ma_20 = np.convolve(red_sums, np.ones(20)/20, mode='valid')
            axes[0].plot(issues[19:], ma_20, 'r-', linewidth=2, label='20期移动平均')
            axes[0].legend()
        
        # 2. 奇偶比时间序列
        axes[1].plot(issues, odd_counts, 'g-', alpha=0.7, linewidth=1)
        axes[1].set_xlabel('期号')
        axes[1].set_ylabel('奇数个数')
        axes[1].set_title('奇偶比时间序列')
        axes[1].grid(True, alpha=0.3)
        axes[1].set_ylim(0, 6)
        
        # 添加水平线
        for i in range(7):
            axes[1].axhline(y=i, color='gray', linestyle=':', alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        return fig
    
    def create_all_visualizations(self, output_dir: str = "visualizations"):
        """创建所有可视化图表"""
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 1. 红球频率分布图
            fig1 = self.plot_red_ball_frequency()
            if fig1:
                fig1.savefig(f"{output_dir}/red_frequency.png", dpi=150, bbox_inches='tight')
                plt.close(fig1)
                logger.info(f"红球频率分布图已保存到 {output_dir}/red_frequency.png")
            
            # 2. 蓝球频率分布图
            fig2 = self.plot_blue_ball_frequency()
            if fig2:
                fig2.savefig(f"{output_dir}/blue_frequency.png", dpi=150, bbox_inches='tight')
                plt.close(fig2)
                logger.info(f"蓝球频率分布图已保存到 {output_dir}/blue_frequency.png")
            
            # 3. 时间序列分析图
            fig3 = self.plot_time_series()
            if fig3:
                fig3.savefig(f"{output_dir}/time_series.png", dpi=150, bbox_inches='tight')
                plt.close(fig3)
                logger.info(f"时间序列分析图已保存到 {output_dir}/time_series.png")
            
            return True
            
        except Exception as e:
            logger.error(f"创建可视化图表时出错: {e}")
            return False

# 全局可视化实例
visualizer = None

def get_visualizer(db_path=None):
    """获取可视化实例"""
    global visualizer
    if visualizer is None:
        db = DoubleBallDatabase(db_path)
        visualizer = Visualization(db)
    return visualizer