import os
import re
import json
import asyncio
import aiohttp

CHANNELS_FILE = "telegram_channels.json"
OUTPUT_DIR = "Config"

# Убраны все лишние пробелы в ключах!
CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+",
    "mtproto": r"tg://proxy\?[^\s\n\"'<]+|https://t\.me/proxy\?[^\s\n\"'<]+"
}

PROXY_PATTERN = r'(?:tg|t|telegram)(?::|\.)?(?:me|me)/(?:proxy\?|join\?invite=)[^\s\n"\'<)]+|tg://proxy\?[^\s\n"\'<)]+'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

async def fetch_content(session, username):
    url = f"https://t.me/s/{username}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as resp:
            if resp.status == 200:
                text = await resp.text()
                new_channels = re.findall(r't\.me/([a-zA-Z0-9_]{5,30})', text)
                return text, list(set(new_channels))
    except Exception:
        pass
    return "", []

async def main():
    print("🚀 Запуск парсера...")
    if not os.path.exists(CHANNELS_FILE):
        print(f"❌ Файл {CHANNELS_FILE} не найден!")
        return

    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        channels_to_parse = [c.strip().lstrip("@") for c in json.load(f) if c.strip()]

    all_configs = {p: set() for p in CONFIG_PATTERNS}
    parsed_channels = set()

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        queue = channels_to_parse
        
        for i in range(2):
            next_queue = []
            for username in queue:
                if username in parsed_channels:
                    continue
                
                print(f"📡 Анализ: @{username}")
                text, found_refs = await fetch_content(session, username)
                parsed_channels.add(username)
                
                for proto, pattern in CONFIG_PATTERNS.items():
                    matches = re.findall(pattern, text)
                    # Очистка HTML-entities
                    cleaned = [m.replace("&amp;", "&").strip() for m in matches]
                    all_configs[proto].update(cleaned)
                
                next_queue.extend(found_refs[:3])
                await asyncio.sleep(0.8)
            queue = next_queue

    # Сохранение результатов (имена файлов теперь точно совпадают с PROTOCOLS в чекере)
    total = 0
    for proto, configs in all_configs.items():
        if configs:
            path = os.path.join(OUTPUT_DIR, f"{proto}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(configs) + "\n")
            total += len(configs)
            print(f"💾 Сохранено {len(configs)} {proto}")
            
    print(f"✅ Сбор завершен. Всего уникальных ключей: {total}")

if __name__ == "__main__":
    asyncio.run(main())
