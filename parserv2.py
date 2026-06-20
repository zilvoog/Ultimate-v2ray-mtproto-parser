import os
import re
import json
import asyncio
import aiohttp

CHANNELS_FILE = "telegram_channels.json"
OUTPUT_DIR = "Config"

CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+"
}

# Универсальный паттерн ловит ссылки tg://proxy?..., t.me/proxy?..., telegram.me/proxy?...
PROXY_PATTERN = r'(?:tg:\/\/proxy\?|t\.me\/proxy\?|telegram\.me\/proxy\?)[^\s\n\"\'<)]+'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

async def fetch_from_web_preview(session, channel_username):
    """Парсит публичную веб-страницу канала Telegram без авторизации"""
    username = channel_username.replace("@", "").split("/")[-1].strip()
    url = f"https://t.me/s/{username}"
    
    configs = {proto: [] for proto in CONFIG_PATTERNS.keys()}
    proxies = []
    
    # ЖЁСТКИЙ ТАЙМАУТ: Если Telegram не ответит за 8 секунд, скрипт пойдет дальше, а не зависнет
    timeout = aiohttp.ClientTimeout(total=8)
    
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status != 200:
                print(f"   ⚠️ Telegram вернул статус {response.status} для {channel_username}")
                return configs, proxies
            
            html = await response.text()
            
            if "If you have <strong>Telegram</strong>, you can view and join" in html and not "tgme_widget_message_text" in html:
                print(f"   ⚠️ Страница {channel_username} пуста или защищена от парсинга.")
            
            # Ищем V2Ray/Hysteria ключи
            for proto, pattern in CONFIG_PATTERNS.items():
                matches = re.findall(pattern, html)
                configs[proto] = [m.replace("&amp;", "&") for m in matches]
                
            # Ищем MTProto прокси
            proxy_matches = re.findall(PROXY_PATTERN, html)
            for p in proxy_matches:
                cleaned = p.replace("&amp;", "&")
                if "t.me/" in cleaned:
                    cleaned = cleaned.split("t.me/")[-1]
                    cleaned = f"tg://{cleaned}"
                elif "telegram.me/" in cleaned:
                    cleaned = cleaned.split("telegram.me/")[-1]
                    cleaned = f"tg://{cleaned}"
                proxies.append(cleaned)
            
    except asyncio.TimeoutError:
        print(f"   ⏱️ Таймаут ожидания ответа от {channel_username} (сервер перегружен).")
    except Exception as e:
        print(f"   ❌ Ошибка при обработке {channel_username}: {e}")
        
    return configs, proxies

async def main():
    print("🌐 Запуск веб-парсера каналов (без аккаунта)...")
    channels = load_channels()
    if not channels:
        print("⚠️ Список channels в telegram_channels.json пуст или поврежден.")
        return

    all_configs = {proto: [] for proto in CONFIG_PATTERNS.keys()}
    all_proxies = []

    # Настройка заголовков (User-Agent), чтобы Telegram видел в нас обычный браузер
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        for index, channel in enumerate(channels, start=1):
            print(f"📡 [{index}/{len(channels)}] Парсим веб-превью: {channel}")
            c_configs, c_proxies = await fetch_from_web_preview(session, channel)
            
            for proto in all_configs:
                all_configs[proto].extend(c_configs[proto])
            all_proxies.extend(c_proxies)
            
            # Увеличим паузу до 2 секунд, чтобы обойти Cloudflare/Anti-DDoS защиту телеграма
            await asyncio.sleep(2)

    print("💾 Сохранение результатов в файлы...")
    # Удаляем дубликаты и сохраняем результаты
    for proto in all_configs:
        unique_list = list(set(all_configs[proto]))
        with open(os.path.join(OUTPUT_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(unique_list) + "\n" if unique_list else "No configs found.\n")
        print(f"   └─ Сохранено {proto.upper()}: {len(unique_list)} шт.")

    unique_proxies = list(set(all_proxies))
    with open(os.path.join(OUTPUT_DIR, "proxies.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(unique_proxies) + "\n" if unique_proxies else "No proxies found.\n")
    print(f"   └─ Сохранено MTProto Прокси: {len(unique_proxies)} шт.")

if __name__ == "__main__":
    asyncio.run(main())
