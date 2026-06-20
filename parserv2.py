import os
import re
import json
import asyncio
import aiohttp

# --- НАСТРОЙКИ ---
CHANNELS_FILE = "telegram_channels.json"
OUTPUT_DIR = "Config"

# Регулярные выражения для поиска
CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+"
}
PROXY_PATTERN = r'(?:tg|t|telegram)(?::|\.)(?:me|me)\/(?:proxy\?|join\?invite=)[^\s\n\"\'<)]+|tg:\/\/proxy\?[^\s\n\"\'<)]+'

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

async def fetch_content(session, username):
    """Скачивает ленту канала и ищет упоминания новых каналов"""
    url = f"https://t.me/s/{username}"
    try:
        async with session.get(url, timeout=7) as resp:
            if resp.status == 200:
                text = await resp.text()
                # Извлекаем потенциальные новые каналы из текста постов
                new_channels = re.findall(r't\.me/([a-zA-Z0-9_]{5,30})', text)
                return text, list(set(new_channels))
    except: pass
    return "", []

async def main():
    print("🚀 Запуск интеллектуального парсера с саморасширением...")
    
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        channels_to_parse = [c.replace("@", "") for c in json.load(f)]
    
    all_configs = {p: set() for p in CONFIG_PATTERNS}
    all_proxies = set()
    parsed_channels = set()
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        # Очередь для парсинга
        queue = channels_to_parse
        
        # 2 итерации: сначала заданные, потом найденные внутри
        for i in range(2):
            next_queue = []
            for username in queue:
                if username in parsed_channels: continue
                
                print(f"📡 Анализ: @{username}")
                text, found_refs = await fetch_content(session, username)
                parsed_channels.add(username)
                
                # Извлечение данных
                for proto, pattern in CONFIG_PATTERNS.items():
                    matches = re.findall(pattern, text)
                    all_configs[proto].update([m.replace("&amp;", "&") for m in matches])
                
                proxies = re.findall(PROXY_PATTERN, text)
                all_proxies.update([p.replace("&amp;", "&") for p in proxies])
                
                # Добавляем найденные каналы в очередь (берем только 2-3 ссылки, чтобы не уйти в бесконечность)
                next_queue.extend(found_refs[:3])
                await asyncio.sleep(0.8)
            queue = next_queue

    # Сохранение результатов
    for proto, configs in all_configs.items():
        with open(os.path.join(OUTPUT_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(configs) + "\n")
            
    with open(os.path.join(OUTPUT_DIR, "proxies.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(all_proxies) + "\n")
        
    print(f"✅ Сбор завершен. Найдено уникальных ключей: {sum(len(c) for c in all_configs.values())}")

if __name__ == "__main__":
    asyncio.run(main())
