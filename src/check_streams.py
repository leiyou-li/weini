import asyncio
import aiohttp
import time
from pathlib import Path
import yaml
import re

async def fetch_content(session, url):
    """从URL获取内容"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

async def fetch_m3u8_info(session, url):
    """获取M3U8流的详细信息"""
    try:
        content = await fetch_content(session, url)
        if not content:
            return None

        info = {
            'url': url,
            'resolution': None,
            'bandwidth': None,
            'codecs': None
        }

        # 解析M3U8内容
        lines = content.split('\n')
        for line in lines:
            if line.startswith('#EXT-X-STREAM-INF:'):
                # 解析流信息
                if 'RESOLUTION=' in line:
                    resolution = re.search(r'RESOLUTION=(\d+x\d+)', line)
                    if resolution:
                        info['resolution'] = resolution.group(1)
                if 'BANDWIDTH=' in line:
                    bandwidth = re.search(r'BANDWIDTH=(\d+)', line)
                    if bandwidth:
                        info['bandwidth'] = int(bandwidth.group(1))
                if 'CODECS=' in line:
                    codecs = re.search(r'CODECS="([^"]+)"', line)
                    if codecs:
                        info['codecs'] = codecs.group(1)

        return info
    except Exception as e:
        print(f"Error parsing M3U8 {url}: {e}")
        return None

def write_streams(file_path, streams):
    """将直播源信息写入文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for stream in streams:
            if isinstance(stream, dict):
                # 写入详细信息
                info = []
                info.append(f"URL: {stream['url']}")
                if stream['resolution']:
                    info.append(f"分辨率: {stream['resolution']}")
                if stream['bandwidth']:
                    info.append(f"带宽: {stream['bandwidth']}bps")
                if stream['codecs']:
                    info.append(f"编码: {stream['codecs']}")
                f.write(f"{' | '.join(info)}\n")
            else:
                # 如果只有URL
                f.write(f"{stream}\n")

async def check_stream(session, url):
    """检查直播源是否有效并获取信息"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                # 获取更多信息
                info = await fetch_m3u8_info(session, url)
                return url, True, info
            return url, False, None
    except:
        return url, False, None

async def check_all_streams(urls):
    """检查所有直播源"""
    async with aiohttp.ClientSession() as session:
        tasks = [check_stream(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        valid_streams = []
        for url, is_valid, info in results:
            if is_valid:
                valid_streams.append(info if info else url)
        return valid_streams

def load_config():
    """加载配置文件"""
    config_path = Path('data/config.yml')
    if not config_path.exists():
        print("配置文件不存在！")
        return []
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('source_urls', [])

async def main():
    # 加载配置
    source_urls = load_config()
    if not source_urls:
        print("没有找到源地址配置！")
        return
    
    print(f"开始检查 {len(source_urls)} 个直播源...")
    
    # 检测有效性并获取信息
    valid_streams = await check_all_streams(source_urls)
    
    # 保存有效的直播源
    output_file = Path('data/valid_streams.txt')
    write_streams(output_file, valid_streams)
    print(f"找到 {len(valid_streams)} 个有效直播源")

if __name__ == '__main__':
    asyncio.run(main()) 