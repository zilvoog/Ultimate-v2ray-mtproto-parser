import os
import re
import json
import asyncio
import aiohttp

CHANNELS_FILE = "telegram_channels.json"
OUTPUT_DIR = "Config"
OUTPUT_CHANNEL = "@rjaviiiiii"   # канал, куда отправляются результаты (исключаем из парсинга)

CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+"
}
PROXY_PATTERN = r'(?:tg|t|telegram)(?::|\.)(?:me|me)\/(?:proxy\?|join\?invite=)[^\s\n\"\'<)]+|tg:\/\/proxy\?[^\s\n\"\'<)]+'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

async def fetch_content(session, username):
    url = f"https://t.me/s/{username}"
    try:
        async with session.get(url, timeout=7) as resp:
            if resp.status == 200:
                text = await resp.text()
                new_channels = re.findall(r't\.me/([a-zA-Z0-9_]{5,30})', text)
                return text, list(set(new_channels))
    except:
        pass
    return "", []

async def main():
    print("🚀 Запуск интеллектуального парсера с саморасширением...")

    # Загружаем список каналов для парсинга
    if not os.path.exists(CHANNELS_FILE):
        print(f"❌ Файл {CHANNELS_FILE} не найден. Парсинг невозможен.")
        return  # завершаем работу, чтобы не парсить канал-назначение по умолчанию

    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        channels_to_parse = [c.replace("@", "") for c in json.load(f)]

    # Удаляем канал-назначение из списка парсинга (если он там случайно указан)
    output_channel_clean = OUTPUT_CHANNEL.replace("@", "")
    if output_channel_clean in channels_to_parse:
        channels_to_parse.remove(output_channel_clean)
        print(f"⚠️ Канал {OUTPUT_CHANNEL} исключён из парсинга (он является каналом-получателем).")

    if not channels_to_parse:
        print("ℹ️ Нет каналов для парсинга после исключения канала-назначения.")
        return

    all_configs = {p: set() for p in CONFIG_PATTERNS}
    all_proxies = set()
    parsed_channels = set()

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        queue = channels_to_parse

        for i in range(2):   # два уровня глубины
            next_queue = []
            for username in queue:
                if username in parsed_channels or username == output_channel_clean:
                    continue

                print(f"📡 Анализ: @{username}")
                text, found_refs = await fetch_content(session, username)
                parsed_channels.add(username)

                # Извлечение конфигов с фильтрацией security=none
                for proto, pattern in CONFIG_PATTERNS.items():
                    matches = re.findall(pattern, text)
                    for m in matches:
                        cfg = m.replace("&amp;", "&")
                        if "security=none" in cfg.lower():
                            continue
                        all_configs[proto].add(cfg)

                proxies = re.findall(PROXY_PATTERN, text)
                all_proxies.update([p.replace("&amp;", "&") for p in proxies])

                # Добавляем найденные каналы, но не добавляем канал-назначение
                new_refs = [ref for ref in found_refs if ref != output_channel_clean]
                next_queue.extend(new_refs[:3])
                await asyncio.sleep(0.8)
            queue = next_queue

    # Сохраняем результаты
    for proto, configs in all_configs.items():
        with open(os.path.join(OUTPUT_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(configs) + "\n")

    with open(os.path.join(OUTPUT_DIR, "proxies.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(all_proxies) + "\n")

    total = sum(len(c) for c in all_configs.values())
    print(f"✅ Сбор завершён. Найдено уникальных ключей: {total} (без security=none)")

if __name__ == "__main__":
    asyncio.run(main())
