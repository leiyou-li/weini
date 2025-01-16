import asyncio
import aiohttp
import time
from pathlib import Path
import re

async def test_stream_speed(session, url):
    """测试直播源的响应速度"""
    try:
        start_time = time.time()
        timeout = aiohttp.ClientTimeout(total=5)
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                end_time = time.time()
                return url, end_time - start_time
            return url, float('inf')
    except:
        return url, float('inf')

def extract_url(line):
    """从信息行中提取URL"""
    if 'URL:' in line:
        return line.split('URL:')[1].split('|')[0].strip()
    return line.strip()

def read_valid_streams(file_path):
    """读取有效的直播源列表"""
    if not file_path.exists():
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return [extract_url(line) for line in f if line.strip()]

async def test_all_streams(urls):
    """测试所有直播源的速度"""
    async with aiohttp.ClientSession() as session:
        tasks = [test_stream_speed(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        return sorted(results, key=lambda x: x[1])

def write_streams(file_path, stream_results):
    """将排序后的直播源写入文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for url, speed in stream_results:
            f.write(f"速度: {speed:.2f}秒 | URL: {url}\n")

async def main():
    input_file = Path('data/valid_streams.txt')
    
    if not input_file.exists():
        print("未找到有效直播源文件！")
        return
    
    # 读取有效的直播源
    streams = read_valid_streams(input_file)
    if not streams:
        print("文件中没有找到直播源！")
        return
    
    print(f"正在测试 {len(streams)} 个直播源的速度...")
    
    # 测试速度并排序
    sorted_results = await test_all_streams(streams)
    
    # 保存排序后的直播源
    output_file = Path('data/sorted_streams.txt')
    write_streams(output_file, sorted_results)
    print(f"已完成 {len(sorted_results)} 个直播源的速度排序")

if __name__ == '__main__':
    asyncio.run(main()) 