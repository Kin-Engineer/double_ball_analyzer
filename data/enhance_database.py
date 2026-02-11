# data/database.py 添加以下方法

class DoubleBallDatabase:
    # ... 现有代码 ...
    
    def get_statistics_with_period(self, period: int = 30) -> Dict[str, Any]:
        """获取带周期参数的统计信息"""
        all_records = self.get_all_records()
        if not all_records:
            return {}
        
        total_records = len(all_records)
        recent_records = all_records[-period:] if total_records > period else all_records
        
        # 热门号码统计
        red_counts = Counter()
        blue_counts = Counter()
        
        for record in recent_records:
            reds = [record.red1, record.red2, record.red3, 
                   record.red4, record.red5, record.red6]
            for ball in reds:
                red_counts[ball] += 1
            blue_counts[record.blue] += 1
        
        # 热号、温号、冷号定义
        total_games = len(recent_records)
        avg_frequency = total_games / 33  # 每个红球平均出现次数
        
        hot_threshold = avg_frequency * 1.5  # 高于平均1.5倍
        cold_threshold = avg_frequency * 0.5  # 低于平均0.5倍
        
        hot_reds = [ball for ball, count in red_counts.most_common() 
                   if count >= hot_threshold]
        cold_reds = [ball for ball, count in red_counts.most_common() 
                    if count <= cold_threshold]
        warm_reds = [ball for ball in range(1, 34) 
                    if ball not in hot_reds and ball not in cold_reds]
        
        # 和值统计
        sums = [record.red1 + record.red2 + record.red3 + 
                record.red4 + record.red5 + record.red6 for record in recent_records]
        sum_trend = '上升' if len(sums) > 1 and sums[-1] > sums[-2] else '下降' if len(sums) > 1 and sums[-1] < sums[-2] else '稳定'
        
        return {
            'period': period,
            'total_games': total_games,
            'hot_reds': [(ball, red_counts[ball]) for ball in hot_reds[:10]],
            'warm_reds': [(ball, red_counts[ball]) for ball in warm_reds[:10]],
            'cold_reds': [(ball, red_counts[ball]) for ball in cold_reds[:10]],
            'sum_trend': sum_trend,
            'avg_sum': sum(sums) / len(sums) if sums else 0,
            'red_frequencies': {ball: count for ball, count in red_counts.items()},
            'blue_frequencies': {ball: count for ball, count in blue_counts.items()}
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