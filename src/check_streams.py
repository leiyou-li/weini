import asyncio
import aiohttp
import time
from pathlib import Path
import re

def parse_m3u(content):
    """解析M3U格式的内容，只返回URL列表"""
    urls = []
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        # 只提取非空且不以#开头的行（URL行）
        if line and not line.startswith('#'):
            urls.append(line)
    return urls

def parse_txt(content):
    """解析TXT格式的内容，返回直播源URL列表"""
    return [line.strip() for line in content.split('\n') 
            if line.strip() and not line.startswith('#')]

def read_streams(file_path):
    """读取并解析直播源文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 判断文件类型
    if file_path.suffix.lower() == '.m3u' or file_path.suffix.lower() == '.m3u8':
        return parse_m3u(content)
    else:  # 默认作为txt处理
        return parse_txt(content)

def write_streams(file_path, streams, original_file):
    """将直播源写入文件，统一转换为txt格式"""
    # 直接按纯文本格式写入，每行一个URL
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
    # 支持多个输入文件
    input_files = [
        Path('data/streams.txt'),
        Path('data/streams.m3u'),
        Path('data/streams.m3u8')
    ]
    
    all_streams = []
    original_file = None
    
    # 读取所有存在的输入文件
    for file_path in input_files:
        if file_path.exists():
            original_file = file_path  # 记住第一个存在的文件作为格式参考
            streams = read_streams(file_path)
            all_streams.extend(streams)
            break
    
    if not original_file:
        print("No input file found!")
        return
    
    # 检测有效性
    valid_streams = await check_all_streams(all_streams)
    
    # 统一使用 .txt 格式输出
    output_file = Path('data/valid_streams.txt')
    
    # 保存有效的直播源
    write_streams(output_file, valid_streams, original_file)
    print(f"Found {len(valid_streams)} valid streams out of {len(all_streams)}")

if __name__ == '__main__':
    asyncio.run(main()) 