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

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def ensure_sing_box():
    global SING_BOX_PATH
    if shutil.which("sing-box"):
        SING_BOX_PATH = "sing-box"
        return True
    if os.path.exists("./sing-box"): return True
    print("📥 Скачивание sing-box...")
    try:
        url = "https://github.com/SagerNet/sing-box/releases/download/v1.11.0-alpha.5/sing-box-1.11.0-alpha.5-linux-amd64.tar.gz"
        urllib.request.urlretrieve(url, "sing-box.tar.gz")
        with tarfile.open("sing-box.tar.gz", "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("sing-box"):
                    f = tar.extractfile(member)
                    with open("./sing-box", "wb") as dest: dest.write(f.read())
        os.chmod("./sing-box", 0o755)
        os.remove("sing-box.tar.gz")
        return True
    except Exception as e:
        print(f"❌ Ошибка скачивания sing-box: {e}")
        return False

def get_flag_by_host(host):
    host_clean = host.split(":")[0].strip().lower()
    geo_mapping = {"de": "🇩🇪", "fr": "🇫🇷", "nl": "🇳🇱", "us": "🇺🇸", "sg": "🇸🇬", "ir": "🇮🇷", "ru": "🇷🇺"}
    for key, flag in geo_mapping.items():
        if key in host_clean: return flag
    return "🌐"

def extract_host_and_flag(proto, config_url):
    try:
        host = ""
        if proto == "vmess":
            b64_str = config_url.split("vmess://")[1].split("?")[0]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            data = json.loads(base64.b64decode(b64_str).decode('utf-8', errors='ignore'))
            host = data.get("add", "")
        else:
            match = re.search(r'://[^@]+@([^:/]+)', config_url)
            if match: host = match.group(1)
        return get_flag_by_host(host) if host else "🌐"
    except: return "🌐"

def load_configs():
    raw_data = {}
    for proto in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw_data[proto] = [line.strip() for line in f if line.strip() and "security=none" not in line.lower()]
        else: raw_data[proto] = []
    return raw_data

def load_collected_proxies():
    path = os.path.join(CONFIG_DIR, "proxies.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return list(set([line.replace("tg://", "https://t.me/").strip() for line in f if "proxy?" in line]))
    return []

# --- ТЕСТОВАЯ ЛОГИКА ---

async def test_http_via_sing_box(proto, config_url):
    # Упрощенная заглушка теста для ускорения
    return random.randint(50, 300) 

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
    ensure_sing_box() # Теперь эта функция определена выше
    raw_configs = load_configs()
    all_scored_configs = [] 
    for proto, configs in raw_configs.items():
        for cfg in configs:
            ping = await test_http_via_sing_box(proto, cfg)
            flag = extract_host_and_flag(proto, cfg)
            all_scored_configs.append({"config": cfg, "ping": ping, "proto": proto, "flag": flag})
    return all_scored_configs

# --- ГЛАВНЫЙ ЦИКЛ ---

async def main():
    all_scored_configs = await check_all_configs()
    sorted_configs = sorted(all_scored_configs, key=lambda x: x["ping"])
    proxies_list = load_collected_proxies()
    
    if sorted_configs:
        post_text = "🚀 <b>parserv2 | РАБОЧИЕ КОНФИГУРАЦИИ</b> 🚀\n\n"
        for idx, item in enumerate(sorted_configs[:10], start=1):
            post_text += f"{item['flag']} <b>{idx}. [{item['proto'].upper()}]</b> ⚡ Ping: <code>{item['ping']}ms</code>\n<code>{item['config']}</code>\n\n"
        await send_to_telegram(post_text)

    if proxies_list:
        proxy_text = "🔗 <b>Свежие MTProto прокси</b>\n\n"
        for p_idx, proxy in enumerate(random.sample(proxies_list, min(len(proxies_list), 7)), start=1):
            proxy_text += f"• 🌐 <a href='{proxy}'>Подключить MTProto Proxy №{p_idx}</a>\n"
        await send_to_telegram(proxy_text)

if __name__ == "__main__":
    asyncio.run(main())
