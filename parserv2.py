import os
import re
import json
import asyncio
import aiohttp
from datetime import datetime

CHANNELS_FILE = "telegram_channels.json"
OUTPUT_DIR = "Config"

CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+"
}
PROXY_PATTERN = r"https:\/\/t\.me\/proxy\?server=[^&\s\"'<)]+&port=\d+&secret=[^\s\"'<)]+"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

async def fetch_from_web_preview(session, channel_username):
    """Парсит публичную веб-страницу канала Telegram без авторизации"""
    # Очищаем юзернейм от @ и ссылок
    username = channel_username.replace("@", "").split("/")[-1].strip()
    url = f"https://t.me/s/{username}"
    
    configs = {proto: [] for proto in CONFIG_PATTERNS.keys()}
    proxies = []
    
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                return configs, proxies
            
            html = await response.text()
            
            # Ищем V2Ray/Hysteria ключи
            for proto, pattern in CONFIG_PATTERNS.items():
                matches = re.findall(pattern, html)
                # Веб-превью может кодировать амперсанды как &amp;, исправляем это
                configs[proto] = [m.replace("&amp;", "&") for m in matches]
                
            # Ищем MTProto прокси
            proxy_matches = re.findall(PROXY_PATTERN, html)
            proxies = [p.replace("&amp;", "&") for p in proxy_matches]
            
    except Exception as e:
        print(f"❌ Ошибка парсинга веб-версии {channel_username}: {e}")
        
    return configs, proxies

async def main():
    print("🌐 Запуск веб-парсера каналов (без аккаунта)...")
    channels = load_channels()
    if not channels:
        print("⚠️ Список каналов в telegram_channels.json пуст.")
        return

    all_configs = {proto: [] for proto in CONFIG_PATTERNS.keys()}
    all_proxies = []

    async with aiohttp.ClientSession() as session:
        for channel in channels:
            print(f"📡 Парсим веб-превью: {channel}")
            c_configs, c_proxies = await fetch_from_web_preview(session, channel)
            
            for proto in all_configs:
                all_configs[proto].extend(c_configs[proto])
            all_proxies.extend(c_proxies)
            await asyncio.sleep(1) # Небольшая пауза, чтобы Telegram не заблокировал IP

    # Удаляем дубликаты и сохраняем результаты
    for proto in all_configs:
        unique_list = list(set(all_configs[proto]))
        with open(os.path.join(OUTPUT_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(unique_list) + "\n" if unique_list else "No configs found.\n")
        print(f"   └─ Собрано {proto.upper()}: {len(unique_list)} шт.")

    unique_proxies = list(set(all_proxies))
    with open(os.path.join(OUTPUT_DIR, "proxies.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(unique_proxies) + "\n" if unique_proxies else "No proxies found.\n")
    print(f"   └─ Собрано MTProto Прокси: {len(unique_proxies)} шт.")

if __name__ == "__main__":
    asyncio.run(main())
