import os
import re
import json
import asyncio
import aiohttp
from urllib.parse import quote

CHANNELS_FILE = "telegram_channels.json"
GITHUB_SOURCES_FILE = "github_sources.json"
OUTPUT_DIR = "Config"

# Добавим иранские специфичные домены и слова для приоритета
IRAN_KEYWORDS = ["iran", "mci", "irancell", "hamrah", "freevpniran"]

CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+"
}
PROXY_PATTERN = r'(?:tg:\/\/proxy\?|t\.me\/proxy\?|telegram\.me\/proxy\?)[^\s\n\"\'<)]+'

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

async def search_github_for_sources(session):
    """Ищет новые файлы с ключами на GitHub"""
    queries = ["v2ray subscription", "vless vmess", "mtproto proxy", "iran vpn free"]
    found_urls = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for query in queries:
        url = f"https://api.github.com/search/code?q={quote(query)}+extension:txt"
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    items = (await resp.json()).get("items", [])
                    for item in items:
                        raw_url = item['html_url'].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                        found_urls.append(raw_url)
        except: pass
    return list(set(found_urls))

async def fetch_content(session, url):
    try:
        async with session.get(url, timeout=5) as resp:
            return await resp.text() if resp.status == 200 else ""
    except: return ""

async def main():
    print("🚀 Запуск глубокого парсинга (включая иранские источники)...")
    all_configs = {p: [] for p in CONFIG_PATTERNS}
    all_proxies = []
    
    async with aiohttp.ClientSession() as session:
        # 1. Поиск новых источников
        github_urls = await search_github_for_sources(session)
        
        # 2. Парсинг каналов (включая те, что вы добавите в json)
        # Совет: добавьте иранские каналы в telegram_channels.json (например: @v2ray_free_iran)
        channels = ["@v2ray_free_iran", "@free_v2ray_iran"] # Пример иранских каналов
        
        for url in (github_urls + [f"https://t.me/s/{c.replace('@','')}" for c in channels]):
            print(f"📡 Парсинг: {url}")
            text = await fetch_content(session, url)
            
            # Извлекаем всё
            for proto, pattern in CONFIG_PATTERNS.items():
                all_configs[proto].extend(re.findall(pattern, text))
            all_proxies.extend(re.findall(PROXY_PATTERN, text))
            await asyncio.sleep(0.5)

    # Сохранение результатов
    for proto, configs in all_configs.items():
        unique = list(set(configs))
        with open(os.path.join(OUTPUT_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(unique) + "\n")
            
    with open(os.path.join(OUTPUT_DIR, "proxies.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(list(set(all_proxies))) + "\n")
        
    print("✅ Сбор завершен.")

if __name__ == "__main__":
    asyncio.run(main())
