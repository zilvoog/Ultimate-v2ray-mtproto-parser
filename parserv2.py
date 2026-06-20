import os
import re
import json
import asyncio
import aiohttp
import sys
import base64
from urllib.parse import quote

CHANNELS_FILE = "telegram_channels.json"
GITHUB_FILE = "github_sources.json"
OUTPUT_DIR = "Config"

CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+"
}

# Универсальный паттерн для поиска MTProto прокси
PROXY_PATTERN = r'(?:tg:\/\/proxy\?|t\.me\/proxy\?|telegram\.me\/proxy\?)[^\s\n\"\'<)]+'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def load_sources(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def filter_unsafe_configs(configs_list, proto):
    cleaned = []
    for cfg in configs_list:
        if "security=none" in cfg.lower():
            continue
            
        if proto == "vmess":
            try:
                b64_str = cfg.split("vmess://")[1].split("?")[0]
                b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
                decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                data = json.loads(decoded)
                if str(data.get("security")).lower() == "none":
                    continue
            except:
                pass
        cleaned.append(cfg)
    return cleaned

def extract_data_from_text(text):
    """Ищет ключи V2Ray и MTProto прокси в тексте, включая декодирование base64"""
    extracted_configs = {proto: [] for proto in CONFIG_PATTERNS.keys()}
    extracted_proxies = []
    
    try:
        padded_text = text.strip().replace("\n", "").replace("\r", "")
        padded_text += "=" * ((4 - len(padded_text) % 4) % 4)
        decoded_text = base64.b64decode(padded_text).decode('utf-8', errors='ignore')
        if any(proto in decoded_text for proto in CONFIG_PATTERNS.keys()) or "proxy?" in decoded_text:
            text = decoded_text
    except:
        pass

    # 1. Поиск V2Ray конфигураций
    for proto, pattern in CONFIG_PATTERNS.items():
        matches = re.findall(pattern, text)
        cleaned_matches = [m.replace("&amp;", "&") for m in matches]
        extracted_configs[proto] = filter_unsafe_configs(cleaned_matches, proto)
        
    # 2. Поиск MTProto прокси
    proxy_matches = re.findall(PROXY_PATTERN, text)
    for p in proxy_matches:
        cleaned = p.replace("&amp;", "&")
        if "t.me/" in cleaned:
            cleaned = "tg://" + cleaned.split("t.me/")[-1]
        elif "telegram.me/" in cleaned:
            cleaned = "tg://" + cleaned.split("telegram.me/")[-1]
        extracted_proxies.append(cleaned)
        
    return extracted_configs, extracted_proxies

async def discover_github_sources(session):
    """Автоматически находит новые репозитории и файлы на GitHub (Ключи + MTProto)"""
    print("🔍 Запуск автопоиска новых источников на GitHub...", flush=True)
    found_urls = set()
    
    # Расширенные поисковые запросы, включая прокси
    search_queries = [
        "vless vmess sub node",
        "free v2ray subscription",
        "mtproto telegram proxy",
        "tg proxy secret port"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/vnd.github.v3+json"
    }
    
    for query in search_queries:
        url = f"https://api.github.com/search/code?q={quote(query)}+in:path+extension:txt"
        try:
            async with session.get(url, headers=headers, timeout=8) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("items", [])
                    for item in items:
                        raw_url = item.get("html_url", "")
                        if raw_url:
                            raw_url = raw_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                            found_urls.add(raw_url)
                elif response.status == 403:
                    print("   ⚠️ Лимит GitHub API достигнут. Переходим к скачиванию.", flush=True)
                    break
        except:
            pass
        await asyncio.sleep(1)
        
    print(f"   └─ Автопоиск обнаружил {len(found_urls)} потенциальных списков на GitHub.", flush=True)
    return list(found_urls)

async def fetch_url_content(session, url):
    timeout = aiohttp.ClientTimeout(total=10, connect=4)
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                return extract_data_from_text(await response.text())
    except:
        pass
    return {proto: [] for proto in CONFIG_PATTERNS.keys()}, []

async def main():
    print("🌐 Запуск универсального веб-парсера v2.5 (Telegram + GitHub + Прокси)...", flush=True)
    
    channels = load_sources(CHANNELS_FILE)
    static_github_urls = load_sources(GITHUB_FILE)
    
    all_configs = {proto: [] for proto in CONFIG_PATTERNS.keys()}
    all_proxies = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. Сбор из Telegram-каналов
        if channels:
            print(f"📡 Сбор данных из {len(channels)} Telegram каналов...", flush=True)
            for i, channel in enumerate(channels, start=1):
                username = channel.replace("@", "").split("/")[-1].strip()
                tg_url = f"https://t.me/s/{username}"
                res_c, res_p = await fetch_url_content(session, tg_url)
                for proto in all_configs:
                    all_configs[proto].extend(res_c[proto])
                all_proxies.extend(res_p)
                await asyncio.sleep(1.5)

        # 2. Автопоиск на GitHub
        discovered_urls = await discover_github_sources(session)
        final_github_list = list(set(static_github_urls + discovered_urls))
        final_github_list = [u for u in final_github_list if "ЮЗЕР" not in u and u.strip()]

        # 3. Парсинг файлов с GitHub
        if final_github_list:
            print(f"🐙 Сбор данных из {len(final_github_list)} источников GitHub...", flush=True)
            for i, url in enumerate(final_github_list[:30], start=1):
                res_c, res_p = await fetch_url_content(session, url)
                for proto in all_configs:
                    all_configs[proto].extend(res_c[proto])
                all_proxies.extend(res_p)
                await asyncio.sleep(0.5)

    print("💾 Фиксация результатов...", flush=True)
    for proto in all_configs:
        unique_list = list(set(all_configs[proto]))
        with open(os.path.join(OUTPUT_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(unique_list) + "\n" if unique_list else "No configs found.\n")
        print(f"   └─ Сохранено {proto.upper()}: {len(unique_list)} шт.", flush=True)

    unique_proxies = list(set(all_proxies))
    with open(os.path.join(OUTPUT_DIR, "proxies.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(unique_proxies) + "\n" if unique_proxies else "No proxies found.\n")
    print(f"   └─ Сохранено MTProto Прокси: {len(unique_proxies)} шт.", flush=True)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
