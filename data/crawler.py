# [file name]: crawler.py
# [file content begin]
"""
双色球数据采集系统 - 增强版
添加多种数据获取选项，保持原有500.com数据源
"""

import requests
import time
import random
import re
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup

# 导入原有系统的模块
try:
    from data.models import DoubleBallRecord
    from data.database import DoubleBallDatabase
    from config import config
    logger = logging.getLogger('crawler')
except ImportError as e:
    logging.error(f"导入模块失败: {e}")
    raise

class DoubleBallCrawler:
    """双色球数据爬虫 - 增强版"""
    
    def __init__(self, database: Optional[DoubleBallDatabase] = None):
        if database is None:
            # 使用 config 中的数据库路径创建数据库实例
            try:
                from config import config
                db_path = config.paths.DATABASE_PATH
            except ImportError:
                db_path = "double_ball.db"
            database = DoubleBallDatabase(db_path)

        self.db = database
        self.base_url = "https://www.500.com/kaijiang/ssq"

        # 配置 - 这里可能有问题，config.crawler 可能未定义
        try:
            from config import config
            self.year_issues = config.crawler.YEAR_ISSUES
            self.request_timeout = config.crawler.REQUEST_TIMEOUT
            self.max_retries = config.crawler.MAX_RETRIES
            self.request_delay = config.crawler.REQUEST_DELAY
        except (ImportError, AttributeError):
            # 提供默认值
            self.year_issues = {2024: 151, 2025: 151}
            self.request_timeout = 30
            self.max_retries = 3
            self.request_delay = (1.0, 3.0)
        
        # 多个User-Agent轮换
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.160 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]
        
        # 请求统计
        self.request_count = 0
        self.last_request_time = time.time()
    
    def smart_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """智能请求函数，添加延迟和重试机制"""
        for retry in range(max_retries):
            try:
                # 控制请求频率
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                
                # 动态延迟
                delay = random.uniform(self.request_delay[0], self.request_delay[1])
                if time_since_last < delay:
                    time.sleep(delay - time_since_last)
                
                # 随机选择User-Agent
                user_agent = random.choice(self.user_agents)
                headers = {
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                }
                
                response = requests.get(url, headers=headers, timeout=self.request_timeout)
                response.encoding = 'utf-8'
                
                # 更新请求统计
                self.request_count += 1
                self.last_request_time = time.time()
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # 请求过多
                    wait_time = (retry + 1) * 10
                    logger.warning(f"请求过多，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"HTTP {response.status_code}: {url}")
                    time.sleep((retry + 1) * 2)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {e}")
                time.sleep((retry + 1) * 5)
        
        logger.error(f"请求失败，已达到最大重试次数: {url}")
        return None

    def get_latest_issue_info(self) -> Dict[str, Any]:
        """获取最新期号信息"""
        try:
            # 尝试从数据库获取最新记录
            records = self.db.get_all_records(order_by="CAST(issue AS INTEGER) DESC", limit=1)
            db_latest_issue = None
            if records:
                db_latest_issue = records[0].issue

            # 从网页获取最新期号
            web_latest_issue = self._get_latest_period_from_web()

            # 选择较大的期号
            if db_latest_issue and web_latest_issue:
                # 将期号转换为整数进行比较（注意：期号是字符串，如'26015'）
                db_num = int(db_latest_issue)
                web_num = int(web_latest_issue)
                latest_issue = str(max(db_num, web_num))
                source = 'web' if web_num >= db_num else 'database'
            elif db_latest_issue:
                latest_issue = db_latest_issue
                source = 'database'
            elif web_latest_issue:
                latest_issue = web_latest_issue
                source = 'web'
            else:
                latest_issue = '26017'# 默认值
                source = 'fallback'

            # 获取最新期号的日期（如果是数据库中的，则从数据库获取；否则用今天）
            if source == 'database' and records:
                draw_date = records[0].draw_date
            else:
                draw_date = datetime.now().strftime('%Y-%m-%d')

            return {
                'issue': latest_issue,
                'date': draw_date,
                'source': source
            }

        except Exception as e:
            logger.error(f"获取最新期号失败: {e}")
            return {
                'issue': '26017',  # 修改为26017
                'date': datetime.now().strftime('%Y-%m-%d'),
                'source': 'fallback'
            }

    def _get_latest_period_from_web(self) -> str:
        """从网站获取最新期号"""
        try:
            # 生成测试期号列表 - 从26020开始倒序测试
            test_periods = []
            for i in range(20, 0, -1):
                test_periods.append(f"26{i:03d}")
            
            for period in test_periods:
                url = f"{self.base_url}/{period}.html"
                response = self.smart_request(url)
                
                if response and response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 检查是否有开奖数据
                    red_balls = []
                    red_selectors = ['.ball-red-normal.ball', '.ball_red', '[class*="red"][class*="ball"]']
                    
                    for selector in red_selectors:
                        elements = soup.select(selector)
                        for elem in elements[:6]:
                            ball_text = elem.get_text().strip()
                            if ball_text.isdigit() and 1 <= int(ball_text) <= 33:
                                red_balls.append(int(ball_text))
                    
                    if len(red_balls) >= 6:
                        logger.info(f"找到有效最新期号: {period}")
                        return period
            
            # 如果没找到，返回默认值（改为26017）
            # 注意：这里需要根据实际情况手动更新最新期号
            # # 当前最新期号：26017 (更新时间：2026-02-06)
            # # 下期开奖后需更新为：26017
            return "26017"
            
        except Exception as e:
            logger.error(f"从网站获取最新期号失败: {e}")
            return "26017"
    
    def crawl_single_period(self, issue: str) -> Optional[DoubleBallRecord]:
        """爬取单期数据"""
        url = f"{self.base_url}/{issue}.html"
        
        try:
            response = self.smart_request(url)
            
            if not response or response.status_code != 200:
                logger.warning(f"请求失败: {issue}")
                return None
            
            return self._parse_draw_page(response.text, issue)
                
        except Exception as e:
            logger.error(f"爬取失败 {issue}: {e}")
            return None
    
    def _parse_draw_page(self, html: str, issue: str) -> Optional[DoubleBallRecord]:
        """解析开奖页面"""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # 1. 提取红球
            red_balls = []
            
            red_selectors = [
                '.ball-red-normal.ball',
                '.ball_red',
                'span.ball-red-normal.ball',
                'li.ball-red-normal.ball',
                '[class*="red"][class*="ball"]'
            ]
            
            for selector in red_selectors:
                red_elements = soup.select(selector)
                for elem in red_elements[:6]:
                    ball_text = elem.get_text().strip()
                    if ball_text.isdigit() and 1 <= int(ball_text) <= 33:
                        red_balls.append(int(ball_text))
                if len(red_balls) >= 6:
                    break
            
            if len(red_balls) != 6:
                logger.warning(f"红球解析失败: {issue}, 找到{len(red_balls)}个球")
                return None
            
            # 确保红球排序（DoubleBallRecord 期望排序的）
            red_balls.sort()
            
            # 2. 提取蓝球
            blue_ball = None
            
            blue_selectors = [
                '.ball-blue-normal.ball',
                '.ball_blue',
                'span.ball-blue-normal.ball',
                'li.ball-blue-normal.ball',
                '[class*="blue"][class*="ball"]'
            ]
            
            for selector in blue_selectors:
                blue_elements = soup.select(selector)
                for elem in blue_elements:
                    ball_text = elem.get_text().strip()
                    if ball_text.isdigit() and 1 <= int(ball_text) <= 16:
                        blue_ball = int(ball_text)
                        break
                if blue_ball:
                    break
            
            if not blue_ball:
                logger.warning(f"蓝球解析失败: {issue}")
                return None
            
            # 3. 提取日期
            draw_date = self._extract_date_from_page(soup, issue)
            
            # 4. 创建 DoubleBallRecord 对象
            record = DoubleBallRecord(
                issue=issue,
                draw_date=draw_date,
                red1=red_balls[0],
                red2=red_balls[1],
                red3=red_balls[2],
                red4=red_balls[3],
                red5=red_balls[4],
                red6=red_balls[5],
                blue=blue_ball
            )
            
            # 5. 计算特征
            record.calculate_basic_features()
            record.calculate_stage1_features()
            
            logger.info(f"成功解析: {issue}, 红球{red_balls}, 蓝球{blue_ball}, 日期{draw_date}")
            return record
            
        except Exception as e:
            logger.error(f"解析页面失败 {issue}: {e}")
            return None
    
    def _extract_date_from_page(self, soup: BeautifulSoup, issue: str) -> str:
        """从页面提取日期"""
        page_text = soup.get_text()
        
        date_patterns = [
            r'开奖日期[：:\s]*(\d{4}年\d{1,2}月\d{1,2}日)',
            r'开奖日期[：:\s]*(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}-\d{1,2}-\d{1,2})'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                if '2023-2-13' not in match and '2023年2月13日' not in match:
                    parsed_date = self._parse_date_string(match)
                    if parsed_date:
                        return parsed_date
        
        # 如果没有找到日期，从期号估算
        return self._estimate_date_from_issue(issue)
    
    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """解析日期字符串"""
        try:
            date_str = date_str.strip()
            
            # 中文日期格式
            chinese_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
            if chinese_match:
                year = chinese_match.group(1)
                month = chinese_match.group(2).zfill(2)
                day = chinese_match.group(3).zfill(2)
                return f"{year}-{month}-{day}"
            
            # 标准日期格式
            standard_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
            if standard_match:
                year = standard_match.group(1)
                month = standard_match.group(2).zfill(2)
                day = standard_match.group(3).zfill(2)
                return f"{year}-{month}-{day}"
            
            return None
        except Exception as e:
            logger.error(f"解析日期失败: {date_str}, 错误: {e}")
            return None
    
    def _estimate_date_from_issue(self, issue: str) -> str:
        """从期号估算日期"""
        try:
            year_part = int(issue[:2])
            issue_num = int(issue[2:])
            
            if year_part <= 99:
                full_year = 2000 + year_part if year_part >= 0 else 1900 + year_part
            else:
                full_year = year_part
            
            # 简单估算：每年1月1日开始，每周3期（二、四、日）
            weeks = (issue_num - 1) // 3
            days = weeks * 7
            
            # 每周的哪一天（0=周二, 2=周四, 5=周日）
            day_of_week = (issue_num - 1) % 3
            day_offsets = {0: 0, 1: 2, 2: 5}
            days += day_offsets[day_of_week]
            
            # 找到第一个开奖日（2003年第一期的实际日期是2003-02-23）
            if full_year == 2003:
                base_date = datetime(2003, 2, 23)
            else:
                base_date = datetime(full_year, 1, 1)
                
                # 找到第一个周二
                while base_date.weekday() != 1:  # 周二
                    base_date += timedelta(days=1)
            
            estimated_date = base_date + timedelta(days=days)
            return estimated_date.strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.error(f"估算日期失败: {issue}, 错误: {e}")
            # 返回默认日期
            year_part = int(issue[:2])
            full_year = 2000 + year_part if year_part >= 0 else 1900 + year_part
            return f"{full_year}-01-01"
    
    def generate_all_issues(self) -> List[str]:
        """生成所有期号"""
        issues = []
        
        # 1. 获取最新期号
        latest_info = self.get_latest_issue_info()
        latest_issue = latest_info['issue']
        
        if latest_issue.startswith('26'):
            latest_num = int(latest_issue[2:])
            # 生成2026年期号
            for i in range(1, latest_num + 1):
                issues.append(f"26{i:03d}")
        
        # 2. 生成2003-2025年期号
        for year in range(2003, 2026):
            short_year = year % 100
            max_issue = self.year_issues.get(year, 0)
            
            if max_issue > 0:
                for issue in range(1, max_issue + 1):
                    issues.append(f"{short_year:02d}{issue:03d}")
        
        # 排序
        issues.sort()
        logger.info(f"生成期号总数: {len(issues)}")
        return issues
    
    # ================ 新增数据获取选项 ================
    
    def crawl_single_year(self, year: int) -> List[DoubleBallRecord]:
        """爬取单个年份数据"""
        logger.info(f"开始下载 {year} 年数据...")
        
        # 生成指定年份的期号
        all_issues = []
        short_year = year % 100
        max_issue = self.year_issues.get(year, 0)
        
        if max_issue > 0:
            for issue in range(1, max_issue + 1):
                all_issues.append(f"{short_year:02d}{issue:03d}")
        
        return self._crawl_issues_list(all_issues, f"{year}年数据")
    
    def crawl_recent_years(self, years: int = 3) -> List[DoubleBallRecord]:
        """爬取最近N年数据"""
        current_year = datetime.now().year
        start_year = current_year - years + 1
        
        logger.info(f"开始下载最近 {years} 年数据 ({start_year}-{current_year})...")
        
        # 生成指定年份范围的期号
        all_issues = []
        for year in range(start_year, current_year + 1):
            short_year = year % 100
            max_issue = self.year_issues.get(year, 0)
            
            if max_issue > 0:
                for issue in range(1, max_issue + 1):
                    all_issues.append(f"{short_year:02d}{issue:03d}")
        
        return self._crawl_issues_list(all_issues, f"最近{years}年数据")
    
    def crawl_issue_range(self, start_issue: str, end_issue: str) -> List[DoubleBallRecord]:
        """爬取指定期数范围数据"""
        logger.info(f"开始下载 {start_issue} 到 {end_issue} 的数据...")

        try:
            # 解析期号 - 正确的5位期号解析
            if len(start_issue) != 5 or len(end_issue) != 5:
                logger.error("期号格式错误，应为5位数字（如26001）")
                return []

            start_year_part = int(start_issue[:2])
            start_num = int(start_issue[2:])
            end_year_part = int(end_issue[:2])
            end_num = int(end_issue[2:])

            # 检查期号格式
            if start_year_part < 3 or end_year_part < 3:
                logger.error("年份部分不能小于03（2003年）")
                return []

            if start_num < 1 or end_num < 1:
                logger.error("期数部分不能小于1")
                return []

            # 如果起始期号大于结束期号，交换
            if start_issue > end_issue:
                logger.warning(f"起始期号大于结束期号，已自动交换: {start_issue}-{end_issue}")
                start_issue, end_issue = end_issue, start_issue
                start_year_part, end_year_part = end_year_part, start_year_part
                start_num, end_num = end_num, start_num

            # 生成期号范围
            all_issues = []

            if start_year_part == end_year_part:
                # 同一年份
                for issue_num in range(start_num, end_num + 1):
                    all_issues.append(f"{start_year_part:02d}{issue_num:03d}")
            else:
                # 简单处理跨年份：按顺序添加所有期号
                # 注意：这里假设年份是连续的，且每年最多154期
                for year_part in range(start_year_part, end_year_part + 1):
                    if year_part == start_year_part:
                        # 起始年份，从start_num开始
                        issue_start = start_num
                        # 获取该年份的最大期数
                        full_year = 2000 + year_part if year_part > 23 else 1900 + year_part
                        max_issue = self.year_issues.get(full_year, 154)
                        issue_end = max_issue
                    elif year_part == end_year_part:
                        # 结束年份，到end_num结束
                        issue_start = 1
                        issue_end = end_num
                    else:
                        # 中间年份，从1到该年份的最大期数
                        full_year = 2000 + year_part if year_part > 23 else 1900 + year_part
                        max_issue = self.year_issues.get(full_year, 154)
                        issue_start = 1
                        issue_end = max_issue

                    # 生成该年份的期号
                    for issue_num in range(issue_start, issue_end + 1):
                        all_issues.append(f"{year_part:02d}{issue_num:03d}")

            logger.info(f"生成期号范围: 共{len(all_issues)}期, 从{all_issues[0]}到{all_issues[-1]}")
            return self._crawl_issues_list(all_issues, f"{start_issue}-{end_issue}期数据")

        except ValueError as e:
            logger.error(f"期号解析错误: {e}")
            return []
        except Exception as e:
            logger.error(f"生成期号范围失败: {e}")
            return []

    def crawl_historical_data(self, start_year: int = 2003, end_year: int = 2025) -> List[DoubleBallRecord]:
        """爬取历史数据 - 兼容原有接口"""
        logger.info(f"开始下载 {start_year} 到 {end_year} 年的历史数据...")
        
        # 生成指定年份的期号
        all_issues = []
        for year in range(start_year, end_year + 1):
            short_year = year % 100
            max_issue = self.year_issues.get(year, 0)
            
            if max_issue > 0:
                for issue in range(1, max_issue + 1):
                    all_issues.append(f"{short_year:02d}{issue:03d}")
        
        return self._crawl_issues_list(all_issues, "历史数据")
    
    def crawl_current_year_data(self, year: int = 2026) -> List[DoubleBallRecord]:
        """爬取当前年份数据 - 兼容原有接口"""
        logger.info(f"开始下载 {year} 年最新数据...")
        
        # 获取最新期号信息
        latest_info = self.get_latest_issue_info()
        latest_issue = latest_info['issue']
        
        # 生成当前年期号
        issues = []
        if latest_issue.startswith(str(year % 100)):
            latest_num = int(latest_issue[2:])
            short_year = year % 100
            for i in range(1, latest_num + 1):
                issues.append(f"{short_year:02d}{i:03d}")
        
        return self._crawl_issues_list(issues, f"{year}年数据")
    
    def _crawl_issues_list(self, issues: List[str], description: str) -> List[DoubleBallRecord]:
        """爬取指定的期号列表"""
        records = []
        total = len(issues)
        
        if total == 0:
            logger.warning(f"没有需要爬取的{description}")
            return records
        
        logger.info(f"需要爬取 {total} 期{description}")
        
        success = 0
        skip = 0
        fail = 0
        
        for i, issue in enumerate(issues, 1):
            # 显示进度
            if i % 10 == 0 or i <= 5 or i >= total - 5:
                progress = i / total * 100
                logger.info(f"进度: {progress:.1f}% ({i}/{total}) - 期号: {issue}")
            
            # 检查是否已存在
            existing = self.db.get_record_by_issue(issue)
            if existing:
                skip += 1
                continue
            
            # 爬取数据
            record = self.crawl_single_period(issue)
            if record and record.is_valid():
                records.append(record)
                success += 1
                
                # 每10条保存一次
                if success % 10 == 0:
                    self.db.save_records(records[-10:])
            else:
                fail += 1
                logger.warning(f"爬取失败: {issue}")
            
            # 控制请求频率
            if i % 50 == 0:
                rest_time = random.uniform(10, 20)
                logger.info(f"已处理 {i} 期，休息 {rest_time:.1f} 秒...")
                time.sleep(rest_time)
            else:
                time.sleep(random.uniform(1, 3))
        
        # 保存剩余记录
        if records:
            self.db.save_records(records)
        
        # 显示结果
        logger.info(f"{description}爬取完成!")
        logger.info(f"成功: {success} 期, 跳过: {skip} 期, 失败: {fail} 期")
        
        return records
    
    def sync_all_data_incremental(self, force_update: bool = False) -> Dict[str, Any]:
        """同步所有数据 - 增量版本（兼容原有接口）"""
        if force_update:
            self.db.clear_all_data()
            logger.info("已清空所有数据，开始重新同步")
        
        # 获取最新期号信息
        latest_info = self.get_latest_issue_info()
        
        # 爬取历史数据
        historical_records = self.crawl_historical_data(2003, 2025)
        
        # 爬取当前年份数据
        current_records = self.crawl_current_year_data(2026)
        
        total_records = len(historical_records) + len(current_records)
        
        return {
            'historical_records': len(historical_records),
            'current_records': len(current_records),
            'total_records': total_records,
            'latest_issue': latest_info.get('issue', '未知'),
            'incremental': True
        }
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            test_url = f"{self.base_url}/26001.html"
            response = self.smart_request(test_url)
            
            if response and response.status_code == 200:
                logger.info("✅ 连接测试成功")
                return True
            else:
                logger.warning("连接测试失败")
                return False
        except Exception as e:
            logger.error(f"连接测试异常: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            stats = self.db.get_database_info()
            record_count = self.db.get_record_count()
            years_with_data = self.db.get_years_with_data()
            issue_range = self.db.get_issue_range()
            date_range = self.db.get_date_range()
            
            return {
                'record_count': record_count,
                'years_with_data': years_with_data,
                'issue_range': issue_range,
                'date_range': date_range,
                'database_path': stats.get('database_path', '未知'),
                'database_size': stats.get('database_size', '未知')
            }
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {}
    
    def cleanup(self):
        """清理资源"""
        pass  # 这个版本不需要特殊的清理
    
    def __del__(self):
        """析构函数"""
        self.cleanup()

# ================ 增强的主程序菜单 ================

def display_menu():
    """显示主菜单"""
    print("\n" + "="*70)
    print("🎯 双色球数据采集系统 - 增强版")
    print("="*70)
    print("1.  🚀 同步所有数据（历史+当前）")
    print("2.  📊 查看数据库统计")
    print("3.  🔄 测试连接和最新期号")
    print("4.  📅 测试单个年份 (2023年)")
    print("5.  📈 获取最近3年数据 (2023-2025)")
    print("6.  🗓️  获取指定年份数据")
    print("7.  🔢 获取指定期数范围（如26002至26017）")
    print("8.  📚 获取全部历史数据 (2003-2025)")
    print("9.  🆕 获取当前年份数据 (2026)")
    print("10. 🧹 清空数据库（谨慎使用！）")
    print("11. 🚪 退出")
    print("="*70)

def get_year_input(prompt: str) -> int:
    """获取年份输入"""
    while True:
        try:
            year = int(input(prompt))
            if 2003 <= year <= datetime.now().year:
                return year
            else:
                print(f"❌ 年份必须在2003-{datetime.now().year}之间")
        except ValueError:
            print("❌ 请输入有效的年份数字")

def get_issue_input(prompt: str) -> str:
    """获取期号输入"""
    while True:
        issue = input(prompt).strip()
        if len(issue) == 5 and issue.isdigit():
            # 检查期号格式
            year_part = int(issue[:2])
            issue_num = int(issue[2:])
            # 年份部分从03开始（2003年），期数从1开始
            if 3 <= year_part <= 99 and 1 <= issue_num <= 154:
            # if year_part >= 3 and issue_num >= 1:
                return issue
        print("❌ 请输入有效的5位期号（如26001）")

# 兼容原有代码的主函数
if __name__ == "__main__":
    """增强版主程序"""
    import sys
    import os
    
    # 添加路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    db = DoubleBallDatabase()
    crawler = DoubleBallCrawler(db)
    
    try:
        # 显示欢迎信息
        print("\n" + "="*70)
        print("🎯 双色球数据采集系统 - 增强版")
        print("="*70)
        
        while True:
            display_menu()
            
            try:
                choice = input("\n请选择选项 (1-11): ").strip()
                
                if choice == '1':
                    # 🚀 同步所有数据
                    print("\n开始同步所有数据...")
                    result = crawler.sync_all_data_incremental()
                    print(f"同步完成: {result}")
                    
                elif choice == '2':
                    # 📊 查看数据库统计
                    stats = crawler.get_database_stats()
                    print(f"\n📊 数据库统计:")
                    print(f"  记录总数: {stats.get('record_count', 0)} 期")
                    print(f"  期号范围: {stats.get('issue_range', {}).get('min_issue', '未知')} - {stats.get('issue_range', {}).get('max_issue', '未知')}")
                    print(f"  日期范围: {stats.get('date_range', {}).get('min_date', '未知')} - {stats.get('date_range', {}).get('max_date', '未知')}")
                    print(f"  数据年份: {stats.get('years_with_data', [])}")
                    
                elif choice == '3':
                    # 🔄 测试连接和最新期号
                    print("\n测试连接和最新期号...")
                    if crawler.test_connection():
                        latest_info = crawler.get_latest_issue_info()
                        print(f"✅ 连接正常")
                        print(f"📅 最新期号: {latest_info['issue']}")
                        print(f"📅 来源: {latest_info['source']}")
                    else:
                        print("❌ 连接失败，请检查网络")
                        
                elif choice == '4':
                    # 📅 测试单个年份 (2023年)
                    print("\n开始下载2023年数据...")
                    records = crawler.crawl_single_year(2023)
                    print(f"✅ 2023年数据下载完成，共 {len(records)} 期")
                    
                elif choice == '5':
                    # 📈 获取最近3年数据
                    print("\n开始下载最近3年数据 (2023-2025)...")
                    records = crawler.crawl_recent_years(3)
                    print(f"✅ 最近3年数据下载完成，共 {len(records)} 期")
                    
                elif choice == '6':
                    # 🗓️ 获取指定年份数据
                    year = get_year_input("\n请输入要下载的年份 (2003-2026): ")
                    print(f"\n开始下载{year}年数据...")
                    records = crawler.crawl_single_year(year)
                    print(f"✅ {year}年数据下载完成，共 {len(records)} 期")
                    
                elif choice == '7':
                    # 🔢 获取指定期数范围
                    print("\n获取指定期数范围数据")
                    start_issue = get_issue_input("请输入起始期号 (如26002): ")
                    end_issue = get_issue_input("请输入结束期号 (如26017: ")
                    
                    if start_issue > end_issue:
                        print("❌ 起始期号不能大于结束期号")
                        continue
                    
                    print(f"\n开始下载 {start_issue} 到 {end_issue} 的数据...")
                    records = crawler.crawl_issue_range(start_issue, end_issue)
                    print(f"✅ 指定期数范围数据下载完成，共 {len(records)} 期")
                    
                elif choice == '8':
                    # 📚 获取全部历史数据
                    print("\n开始下载全部历史数据 (2003-2025)...")
                    records = crawler.crawl_historical_data(2003, 2025)
                    print(f"✅ 全部历史数据下载完成，共 {len(records)} 期")
                    
                elif choice == '9':
                    # 🆕 获取当前年份数据
                    current_year = datetime.now().year
                    print(f"\n开始下载{current_year}年数据...")
                    records = crawler.crawl_current_year_data(current_year)
                    print(f"✅ {current_year}年数据下载完成，共 {len(records)} 期")
                    
                elif choice == '10':
                    # 🧹 清空数据库
                    confirm = input("\n⚠️  警告：此操作将清空所有数据！确定继续吗？(y/N): ").strip().lower()
                    if confirm == 'y' or confirm == 'yes':
                        db.clear_all_data()
                        print("✅ 数据库已清空")
                    else:
                        print("❌ 操作已取消")
                        
                elif choice == '11':
                    # 🚪 退出
                    print("\n👋 再见！")
                    break
                    
                else:
                    print("❌ 无效选项，请重新选择")
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断操作")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        crawler.cleanup()
# [file content end]
