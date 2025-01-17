import requests
import logging
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import time

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_url_validity(url):
    try:
        response = requests.head(url, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"URL {url} is invalid or unreachable: {e}")
        return False

def fetch_content(url):
    try:
        logging.info(f"Fetching content from {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.content.decode('utf-8-sig')
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch content from {url}: {e}")
        return None

def filter_content(content):
    if content is None:
        return []
    keywords = ["㊙VIP测试", "关注公众号", "天微科技", "获取测试密码", "更新时间", "♥聚玩盒子", "🌹防失联","📡  更新日期","👉", 
                "💓专享源🅰️", "💓专享源🅱️", "关于本源", "每日一首", "MovieMusic", "AMC音乐", "公告"]
    
    # 首先按关键词过滤
    filtered_lines = [line for line in content.splitlines() if not any(keyword in line for keyword in keywords)]
    
    # 然后移除每行中的emoji和特殊符号
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    
    cleaned_lines = []
    for line in filtered_lines:
        # 移除emoji
        line = emoji_pattern.sub('', line)
        # 如果行不是空的，添加到结果中
        if line.strip():
            cleaned_lines.append(line)
    
    return cleaned_lines

def measure_stream_speed(url):
    try:
        start_time = time.time()
        # 使用ffmpeg获取前3秒的流数据来测试速度
        command = ['ffmpeg', '-i', url, '-t', '3', '-f', 'null', '-']
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        end_time = time.time()
        
        if result.returncode == 0:
            # 返回响应时间（秒）
            return end_time - start_time
        return float('inf')  # 如果失败返回无穷大
    except Exception:
        return float('inf')

def check_stream_validity(url):
    try:
        # 使用ffmpeg检查流媒体是否能正常播放
        command = ['ffmpeg', '-i', url, '-t', '10', '-f', 'null', '-']
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        if result.returncode == 0:
            return True
        else:
            logging.error(f"Stream {url} is not playable: {result.stderr.decode('utf-8')}")
            return False
    except subprocess.TimeoutExpired:
        logging.error(f"Stream {url} check timed out")
        return False
    except Exception as e:
        logging.error(f"Error checking stream {url}: {e}")
        return False

def extract_channel_name(line):
    # 尝试从行中提取频道名称
    if ',' in line:  # m3u格式
        return line.split(',')[-1].strip()
    else:  # 其他格式
        parts = line.split()
        if len(parts) > 1:
            # 假设URL在前，名称在后
            return ' '.join(parts[1:]).strip()
    return None

def fetch_and_filter(urls):
    filtered_lines = []
    
    with ThreadPoolExecutor() as executor:
        # 首先检查URL的有效性
        valid_urls = [url for url in urls if check_url_validity(url)]
        # 然后获取内容
        results = list(executor.map(fetch_content, valid_urls))
    
    for content in results:
        filtered_lines.extend(filter_content(content))
    
    # 按频道名称分组并测试速度
    channel_groups = defaultdict(list)
    valid_lines = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        valid_streams = []
        
        # 首先检查流的有效性
        for line in filtered_lines:
            if line.startswith('http'):
                url = line.split()[0]
                if check_stream_validity(url):
                    valid_streams.append(line)
            else:
                valid_streams.append(line)
        
        # 对有效的流进行速度测试和分组
        for line in valid_streams:
            if line.startswith('http'):
                url = line.split()[0]
                channel_name = extract_channel_name(line)
                if channel_name:
                    speed = measure_stream_speed(url)
                    channel_groups[channel_name].append((speed, line))
            else:
                valid_lines.append(line)
    
    # 对每个频道组内的流按速度排序
    sorted_lines = []
    for channel_name, streams in channel_groups.items():
        # 按速度排序（升序）
        sorted_streams = sorted(streams, key=lambda x: x[0])
        # 只添加有效的流（速度不是无穷大的）
        sorted_lines.extend([stream[1] for stream in sorted_streams if stream[0] != float('inf')])
    
    # 将非http行和排序后的流合并
    final_lines = valid_lines + sorted_lines
    
    with open('live_ipv4.txt', 'w', encoding='utf-8') as file:
        file.write('\n'.join(final_lines))
    logging.info("Filtered and speed-sorted content saved to live_ipv4.txt")

if __name__ == "__main__":
    urls = [
        'https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output.txt',
        'https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv4.txt',
        'https://raw.githubusercontent.com/YueChan/Live/main/APTV.m3u',
        'http://ww.weidonglong.com/dsj.txt',
        'http://live.nctv.top/x.txt',
        'http://aktv.top/live.txt',
        'https://raw.githubusercontent.com/yuanzl77/IPTV/main/直播/央视频道.txt',
        'https://live.zhoujie218.top/tv/iptv4.txt',
        'https://raw.githubusercontent.com/Guovin/TV/gd/output/result.txt',
        'https://raw.githubusercontent.com/jiangnan1224/iptv_ipv4_live/refs/heads/main/live_ipv4.txt'
    ]
    fetch_and_filter(urls)