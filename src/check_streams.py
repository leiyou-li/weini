import asyncio
import aiohttp
import logging
import subprocess
from pathlib import Path
import yaml
import re

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_content(session, url):
    """从URL获取内容"""
    try:
        logging.info(f"正在获取内容: {url}")
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.text(encoding='utf-8-sig')
    except Exception as e:
        logging.error(f"获取内容失败 {url}: {e}")
    return None

def filter_content(content):
    """过滤内容"""
    if content is None:
        return []
    
    # 定义需要过滤的关键词
    keywords = [
        "㊙VIP测试", "关注公众号", "天微科技", "获取测试密码", 
        "更新时间", "♥聚玩盒子", "🌹防失联", "📡  更新日期", "👉"
    ]
    
    # 过滤包含关键词的行和ipv6
    return [line for line in content.splitlines() 
            if line.strip() and 
            'ipv6' not in line.lower() and 
            not any(keyword in line for keyword in keywords)]

async def check_stream(url):
    """检查流媒体是否可用"""
    try:
        # 使用ffmpeg检查流
        command = ['ffmpeg', '-i', url, '-t', '10', '-f', 'null', '-']
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            await asyncio.wait_for(process.communicate(), timeout=20)
            return process.returncode == 0
        except asyncio.TimeoutError:
            process.kill()
            logging.error(f"流检查超时: {url}")
            return False
            
    except Exception as e:
        logging.error(f"检查流时出错 {url}: {e}")
        return False

async def process_url(session, url):
    """处理单个URL源"""
    content = await fetch_content(session, url)
    if content:
        return filter_content(content)
    return []

async def check_streams(streams):
    """检查所有流的有效性"""
    valid_streams = []
    total = len(streams)
    
    logging.info(f"开始检查 {total} 个直播源...")
    
    async def check_single_stream(stream):
        if await check_stream(stream):
            return stream
        return None
    
    # 限制并发数
    semaphore = asyncio.Semaphore(5)
    
    async def bounded_check(stream):
        async with semaphore:
            return await check_single_stream(stream)
    
    tasks = [bounded_check(stream) for stream in streams]
    results = await asyncio.gather(*tasks)
    
    valid_streams = [stream for stream in results if stream]
    logging.info(f"检查完成，找到 {len(valid_streams)} 个有效直播源")
    
    return valid_streams

def load_config():
    """加载配置文件"""
    config_path = Path('data/config.yml')
    if not config_path.exists():
        logging.error("配置文件不存在！")
        return []
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('source_urls', [])

def write_streams(file_path, streams):
    """保存直播源到文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for stream in streams:
            f.write(f"{stream}\n")

async def main():
    # 加载源URL列表
    source_urls = load_config()
    if not source_urls:
        logging.error("没有找到源地址配置！")
        return
    
    # 获取所有直播源
    all_streams = set()
    async with aiohttp.ClientSession() as session:
        for url in source_urls:
            streams = await process_url(session, url)
            all_streams.update(streams)
    
    logging.info(f"总共获取到 {len(all_streams)} 个直播源")
    
    # 检查直播源有效性
    valid_streams = await check_streams(list(all_streams))
    
    # 保存有效的直播源
    output_file = Path('data/valid_streams.txt')
    write_streams(output_file, valid_streams)
    logging.info(f"已保存 {len(valid_streams)} 个有效直播源到 {output_file}")

if __name__ == '__main__':
    asyncio.run(main()) 