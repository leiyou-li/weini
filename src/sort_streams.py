import asyncio
import aiohttp
import time
from pathlib import Path
from check_streams import read_streams, write_streams  # 复用解析函数

async def test_stream_speed(session, url):
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

async def test_all_streams(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [test_stream_speed(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        # 按响应时间排序
        sorted_results = sorted(results, key=lambda x: x[1])
        return [url for url, _ in sorted_results]

async def main():
    # 查找valid_streams文件
    input_file = Path('data/valid_streams.txt')
    
    if not input_file.exists():
        print("No valid streams file found!")
        return
    
    # 输出文件统一使用 .txt 格式
    output_file = Path('data/sorted_streams.txt')
    
    # 读取有效的直播源
    streams = read_streams(input_file)
    
    # 测试速度并排序
    sorted_streams = await test_all_streams(streams)
    
    # 保存排序后的直播源
    write_streams(output_file, sorted_streams, input_file)
    print(f"Sorted {len(sorted_streams)} streams by speed")

if __name__ == '__main__':
    asyncio.run(main()) 