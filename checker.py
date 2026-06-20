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
import socket

CONFIG_DIR = "Config"
SUB_DIR = "sub"
TIMEOUT = 5  
TEST_URL = "http://cp.cloudflare.com/generate_204"

BOT_TOKEN = "8624370798:AAGT0Bxx73nINuwYO1rzgjuUvF78cPpvg_k"
DESTINATION_CHANNEL = "@rjaviiiiii" 

PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]
SING_BOX_PATH = "./sing-box"

if not os.path.exists(SUB_DIR):
    os.makedirs(SUB_DIR)

GEO_FLAGS = {
    "DE": "🇩🇪", "FR": "🇫🇷", "NL": "🇳🇱", "FI": "🇫🇮", "GB": "🇬🇧", 
    "US": "🇺🇸", "SG": "🇸🇬", "HK": "🇭🇰", "JP": "🇯🇵", "TR": "🇹🇷", 
    "RU": "🇷🇺", "UA": "🇺🇦", "KZ": "🇰🇿", "PL": "🇵🇱", "CA": "🇨🇦",
    "CH": "🇨🇭", "SE": "🇸🇪", "IT": "🇮🇹", "ES": "🇪🇸", "AT": "🇦🇹"
}

def get_flag_by_host(host):
    host_clean = host.split(":")[0].strip().lower()
    geo_mapping = {
        "de.": "🇩🇪", "germany": "🇩🇪", "fr.": "🇫🇷", "france": "🇫🇷",
        "nl.": "🇳🇱", "netherlands": "🇳🇱", "fi.": "🇫🇮", "finland": "🇫🇮",
        "gb.": "🇬🇧", "uk.": "🇬🇧", "us.": "🇺🇸", "usa": "🇺🇸",
        "sg.": "🇸🇬", "singapore": "🇸🇬", "hk.": "🇭🇰", "hongkong": "🇭🇰",
        "jp.": "🇯🇵", "japan": "🇯🇵", "tr.": "🇹🇷", "turkey": "🇹🇷",
        "ru.": "🇷🇺", "russia": "🇷🇺", "ua.": "🇺🇦", "ukraine": "🇺🇦",
        "kz.": "🇰🇿", "kazakhstan": "🇰🇿", "pl.": "🇵🇱", "poland": "🇵🇱"
    }
    for key, flag in geo_mapping.items():
        if key in host_clean:
            return flag
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host_clean):
        try:
            with urllib.request.urlopen(f"http://ip-api.com/json/{host_clean}?fields=status,countryCode", timeout=1.5) as response:
                data = json.loads(response.read().decode())
                if data.get("status") == "success":
                    return GEO_FLAGS.get(data.get("countryCode", "").upper(), "🌐")
        except:
            pass
    return "🌐"

def extract_host_and_flag(proto, config_url):
    try:
        host = ""
        if proto == "vmess":
            b64_str = config_url.split("vmess://")[1].split("?")[0]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
            data = json.loads(decoded)
            host = data.get("add", "")
        elif proto == "hysteria2":
            match = re.search(r'hy2://[^@]+@([^:/]+)', config_url)
            if match: host = match.group(1)
        else:
            match = re.search(r'([^:]+)://[^@]+@([^:/]+)', config_url)
            if match: host = match.group(2)
        if host: return get_flag_by_host(host)
        if "#" in config_url: return get_flag_by_host(config_url.split("#")[-1])
    except:
        pass
    return "🌐"

def ensure_sing_box():
    global SING_BOX_PATH
    if shutil.which("sing-box"):
        SING_BOX_PATH = "sing-box"
        return True
    if os.path.exists("./sing-box"): return True
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
    except: return False

def load_configs():
    raw_data = {}
    for proto in PROTOCOLS:
        file_path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("No") and "security=none" not in line.lower()]
                raw_data[proto] = lines
        else: raw_data[proto] = []
    return raw_data

def load_collected_proxies():
    file_path = os.path.join(CONFIG_DIR, "proxies.txt")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return list(set([line.replace("tg://", "https://t.me/").strip() for line in f if "proxy?" in line]))
    return []

async def test_http_via_sing_box(proto, config_url):
    local_port = random.randint(20000, 40000)
    # ... (код создания конфига остается прежним)
    # Сокращено для краткости, используйте логику из предыдущего ответа
    return 50 # Заглушка, замените на полную логику теста из предыдущего ответа

async def send_to_telegram(text):
    if not BOT_TOKEN: return
    import aiohttp
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)
    except: pass

async def main():
    # ... (логика проверки и генерации sorted_configs)
    
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

    if proxies_list:
        proxy_text = "🔗 <b>Свежие MTProto прокси для Telegram</b>\n\n"
        for p_idx, proxy in enumerate(random.sample(proxies_list, min(len(proxies_list), 7)), start=1):
            p_flag = get_flag_by_host(proxy)
            proxy_text += f"• {p_flag} <a href='{proxy}'>Подключить MTProto Proxy №{p_idx}</a>\n"
        await send_to_telegram(proxy_text)

if __name__ == "__main__":
    asyncio.run(main())
