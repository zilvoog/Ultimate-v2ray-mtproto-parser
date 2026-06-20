import os
import re
import json
import random
import asyncio
import base64
import shutil
import urllib.request
import tarfile
import time

CONFIG_DIR = "Config"
SUB_DIR = "sub"
TIMEOUT = 5  
TEST_URL = "http://cp.cloudflare.com/generate_204"

BOT_TOKEN = "8624370798:AAGT0Bxx73nINuwYO1rzgjuUvF78cPpvg_k"
DESTINATION_CHANNEL = "@rjaviiiiii" 

PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]
SING_BOX_PATH = "./sing-box"

# (Оставьте ваши функции get_flag_by_host, extract_host_and_flag, ensure_sing_box, load_configs, load_collected_proxies, test_http_via_sing_box без изменений, так как они были верны)

async def send_to_telegram(text):
    if not BOT_TOKEN or not text.strip(): return
    import aiohttp
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)
    except: pass

async def check_all_configs():
    ensure_sing_box()
    raw_configs = load_configs()
    valid_configs = {proto: [] for proto in PROTOCOLS}
    all_scored_configs = [] 
    
    for proto, configs in raw_configs.items():
        print(f"⏳ Тест {proto.upper()} ({len(configs)} шт.)...")
        semaphore = asyncio.Semaphore(15)
        async def worker(cfg):
            async with semaphore: return await test_http_via_sing_box(proto, cfg)
        tasks = [worker(config) for config in configs]
        if tasks:
            results = await asyncio.gather(*tasks)
            for config, ping in zip(configs, results):
                if ping is not None: 
                    valid_configs[proto].append(config)
                    flag = extract_host_and_flag(proto, config)
                    all_scored_configs.append({"config": config, "ping": ping, "proto": proto, "flag": flag})
    return valid_configs, all_scored_configs

async def main():
    # 1. Запускаем тесты
    valid_configs, all_scored_configs = await check_all_configs()
    # 2. Сортируем
    sorted_configs = sorted(all_scored_configs, key=lambda x: x["ping"])
    proxies_list = load_collected_proxies()
    
    # 3. Публикуем ключи
    if sorted_configs:
        post_text = "🚀 <b>parserv2 | РАБОЧИЕ КОНФИГУРАЦИИ</b> 🚀\n\n"
        for idx, item in enumerate(sorted_configs, start=1):
            chunk = f"{item['flag']} <b>{idx}. [{item['proto'].upper()}]</b> ⚡ Ping: <code>{item['ping']}ms</code>\n<code>{item['config']}</code>\n\n"
            if len(post_text) + len(chunk) > 3900:
                await send_to_telegram(post_text)
                await asyncio.sleep(2)
                post_text = ""
            post_text += chunk
        await send_to_telegram(post_text)

    # 4. Публикуем прокси
    if proxies_list:
        proxy_text = "🔗 <b>Свежие MTProto прокси для Telegram</b>\n\n"
        # Выбираем до 7 штук
        sample = random.sample(proxies_list, min(len(proxies_list), 7))
        for p_idx, proxy in enumerate(sample, start=1):
            p_flag = get_flag_by_host(proxy)
            proxy_text += f"• {p_flag} <a href='{proxy}'>Подключить MTProto Proxy №{p_idx}</a>\n"
        await send_to_telegram(proxy_text)

if __name__ == "__main__":
    asyncio.run(main())
