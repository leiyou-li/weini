import requests
import logging
import subprocess
import re
import time
import urllib3
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_url_validity(url):
    try:
        response = requests.head(url, timeout=10, verify=False)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"URL {url} is invalid or unreachable: {e}")
        return False

def fetch_content(url):
    try:
        logging.info(f"Fetching content from {url}")
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()
        return response.content.decode('utf-8-sig')
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch content from {url}: {e}")
        return None

def filter_content(content):
    if content is None:
        return []
    keywords = ["㊙VIP测试", "关注公众号", "天微科技", "获取测试密码", "更新时间", "♥聚玩盒子", "🌹防失联","📡  更新日期","👉",]
    return [line for line in content.splitlines() if not any(keyword in line for keyword in keywords)]

def check_stream_quality(url) -> Tuple[bool, float]:
    try:
        # 使用ffmpeg检查流媒体质量
        command = ['ffmpeg', '-i', url, '-t', '10', '-filter:v', 'fps=fps=1', '-f', 'null', '-']
        start_time = time.time()
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        
        if result.returncode == 0:
            # 计算处理速度作为质量指标
            duration = time.time() - start_time
            stderr_output = result.stderr.decode('utf-8')
            
            # 提取视频信息
            bitrate_match = re.search(r'bitrate: (\d+) kb/s', stderr_output)
            fps_match = re.search(r'(\d+(?:\.\d+)?) fps', stderr_output)
            
            # 计算质量分数 (基于比特率、FPS和响应时间)
            quality_score = 0.0
            if bitrate_match:
                quality_score += float(bitrate_match.group(1)) / 1000  # 将比特率转换为Mbps
            if fps_match:
                quality_score += float(fps_match.group(1))
            quality_score += (20 - min(duration, 20)) / 2  # 响应时间影响（最大10分）
            
            return True, quality_score
        else:
            logging.error(f"Stream {url} is not playable: {result.stderr.decode('utf-8')}")
            return False, 0.0
    except subprocess.TimeoutExpired:
        logging.error(f"Stream {url} check timed out")
        return False, 0.0
    except Exception as e:
        logging.error(f"Error checking stream {url}: {e}")
        return False, 0.0

def extract_channel_name(line: str) -> str:
    # 尝试从行中提取频道名称
    if ',' in line:
        return line.split(',')[1].strip()
    elif '#' in line:
        return line.split('#')[1].strip()
    return "Unknown Channel"

def fetch_and_filter(urls):
    stream_data: Dict[str, Tuple[str, float]] = {}  # {频道名: (完整行, 质量分数)}
    
    with ThreadPoolExecutor() as executor:
        # 首先检查URL的有效性
        valid_urls = [url for url in urls if check_url_validity(url)]
        # 然后获取内容
        results = list(executor.map(fetch_content, valid_urls))
    
    filtered_lines = []
    for content in results:
        filtered_lines.extend(filter_content(content))
    
    # 检查每个直播源的可用性和质量
    with ThreadPoolExecutor(max_workers=5) as executor:
        for line in filtered_lines:
            if line.startswith('http'):
                url = line.split()[0]  # 提取URL部分
                channel_name = extract_channel_name(line)
                is_valid, quality_score = check_stream_quality(url)
                
                if is_valid:
                    if channel_name in stream_data:
                        # 如果已存在该频道，保留质量更好的源
                        if quality_score > stream_data[channel_name][1]:
                            stream_data[channel_name] = (line, quality_score)
                    else:
                        stream_data[channel_name] = (line, quality_score)
            else:
                # 保留非URL行（如分类标题）
                stream_data[line] = (line, float('inf'))  # 使用无穷大确保标题行排在最前面
    
    # 按质量分数排序并写入文件
    sorted_streams = sorted(stream_data.items(), key=lambda x: (-x[1][1], x[0]))  # 按分数降序，频道名升序
    
    with open('live.txt', 'w', encoding='utf-8') as file:
        for _, (line, _) in sorted_streams:
            file.write(line + '\n')
    logging.info("Filtered and sorted content saved to live.txt")

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