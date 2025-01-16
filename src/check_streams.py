import asyncio
import aiohttp
import time
from pathlib import Path
import yaml

async def fetch_content(session, url):
    """从URL获取内容"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def parse_m3u(content):
    """解析M3U格式的内容，只返回URL列表"""
    if not content:
        return []
    urls = []
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            urls.append(line)
    return urls

def parse_txt(content):
    """解析TXT格式的内容，返回直播源URL列表"""
    if not content:
        return []
    return [line.strip() for line in content.split('\n') 
            if line.strip() and not line.startswith('#')]

async def fetch_streams_from_url(session, url):
    """从URL获取直播源列表"""
    content = await fetch_content(session, url)
    if not content:
        return []
    
    # 根据URL后缀决定解析方法
    if url.lower().endswith(('.m3u', '.m3u8')):
        return parse_m3u(content)
    else:
        return parse_txt(content)

def load_config():
    """加载配置文件"""
    config_path = Path('data/config.yml')
    if not config_path.exists():
        print("配置文件不存在！")
        return []
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('source_urls', [])

def write_streams(file_path, streams):
    """将直播源写入文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for stream in streams:
            f.write(f"{stream}\n")

async def check_stream(session, url):
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                return url, True
            return url, False
    except:
        return url, False

async def check_all_streams(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [check_stream(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        return [url for url, is_valid in results if is_valid]

async def main():
    # 加载配置
    source_urls = load_config()
    if not source_urls:
        print("没有找到源地址配置！")
        return
    
    # 获取所有直播源
    all_streams = set()  # 使用集合去重
    async with aiohttp.ClientSession() as session:
        for url in source_urls:
            print(f"正在获取直播源: {url}")
            streams = await fetch_streams_from_url(session, url)
            all_streams.update(streams)
    
    print(f"总共获取到 {len(all_streams)} 个直播源")
    
    # 检测有效性
    valid_streams = await check_all_streams(list(all_streams))
    
    # 保存有效的直播源
    output_file = Path('data/valid_streams.txt')
    write_streams(output_file, valid_streams)
    print(f"找到 {len(valid_streams)} 个有效直播源")

if __name__ == '__main__':
    asyncio.run(main()) 