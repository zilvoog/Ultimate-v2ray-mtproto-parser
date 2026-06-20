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

if not os.path.exists(SUB_DIR):
    os.makedirs(SUB_DIR)

def get_flag_by_host(host):
    """Определяет флаг страны по текстовым маркерам в адресе сервера или имени ключа"""
    host = host.lower()
    geo_mapping = {
        "de": "🇩🇪", "germany": "🇩🇪", "fr": "🇫🇷", "france": "🇫🇷",
        "nl": "🇳🇱", "netherlands": "🇳🇱", "fi": "🇫🇮", "finland": "🇫🇮",
        "gb": "🇬🇧", "uk": "🇬🇧", "london": "🇬🇧", "us": "🇺🇸", "usa": "🇺🇸",
        "sg": "🇸🇬", "singapore": "🇸🇬", "hk": "🇭🇰", "hongkong": "🇭🇰",
        "jp": "🇯🇵", "japan": "🇯🇵", "tr": "🇹🇷", "turkey": "🇹🇷",
        "ru": "🇷🇺", "russia": "🇷🇺", "ua": "🇺🇦", "ukraine": "🇺🇦",
        "kz": "🇰🇿", "kazakhstan": "🇰🇿", "pl": "🇵🇱", "poland": "🇵🇱"
    }
    for key, flag in geo_mapping.items():
        if key in host:
            return flag
    return "🌐"

def extract_host_and_flag(proto, config_url):
    """Извлекает адрес сервера и подбирает флаг страны"""
    flag = "🌐"
    try:
        # Пробуем найти имя/заметку в конце урла после символа #
        if "#" in config_url:
            name_part = config_url.split("#")[-1]
            flag = get_flag_by_host(name_part)
            if flag != "🌐":
                return flag

        if proto == "vmess":
            b64_str = config_url.split("vmess://")[1].split("?")[0]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
            data = json.loads(decoded)
            flag = get_flag_by_host(data.get("add", ""))
            if flag == "🌐" and data.get("ps"):
                flag = get_flag_by_host(data.get("ps", ""))
        elif proto == "hysteria2":
            match = re.search(r'hy2://[^@]+@([^:/]+)', config_url)
            if match: flag = get_flag_by_host(match.group(1))
        else:
            match = re.search(r'([^:]+)://[^@]+@([^:/]+)', config_url)
            if match: flag = get_flag_by_host(match.group(2))
    except:
        pass
    return flag

def load_configs():
    raw_data = {}
    for proto in PROTOCOLS:
        file_path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = []
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("No configs") or "No proxies" in line:
                        continue
                    if "security=none" in line.lower():
                        continue
                    lines.append(line)
                raw_data[proto] = lines
        else:
            raw_data[proto] = []
    return raw_data

def load_collected_proxies():
    file_path = os.path.join(CONFIG_DIR, "proxies.txt")
    proxies = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "proxy?" in line:
                    if line.startswith("tg://"):
                        line = line.replace("tg://", "https://t.me/")
                    proxies.append(line)
    return list(set(proxies))

async def test_http_via_sing_box(proto, config_url):
    local_port = random.randint(20000, 40000)
    sb_config = {
        "log": {"level": "panic"},
        "inbounds": [{"type": "socks", "listen": "127.0.0.1", "listen_port": local_port}],
        "outbounds": [{"type": "direct", "tag": "direct"}]
    }
    try:
        if proto == "vmess":
            b64_str = config_url.split("vmess://")[1].split("?")[0]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
            data = json.loads(decoded)
            if str(data.get("security")).lower() == "none": return None
            outbound = {
                "type": "vmess", "tag": "proxy",
                "server": data.get("add"), "server_port": int(data.get("port")),
                "uuid": data.get("id"), "security": "auto", "alter_id": int(data.get("aid", 0))
            }
            if data.get("net") == "ws": outbound["transport"] = {"type": "ws", "path": data.get("path", "")}
        elif proto == "hysteria2":
            match = re.search(r'hy2://([^@]+)@([^:/]+):(\d+)', config_url)
            outbound = {
                "type": "hysteria2", "tag": "proxy",
                "server": match.group(2), "server_port": int(match.group(3)),
                "password": match.group(1), "tls": {"enabled": True, "insecure": True}
            }
        else:
            match = re.search(r'([^:]+)://([^@]+)@([^:/]+):(\d+)', config_url)
            p_type = "shadowsocks" if proto == "shadowsocks" else proto
            outbound = {
                "type": p_type, "tag": "proxy", "server": match.group(3), "server_port": int(match.group(4)),
            }
            if p_type == "vless": outbound.update({"uuid": match.group(2), "flow": ""})
            elif p_type == "trojan": outbound.update({"password": match.group(2)})
            elif p_type == "shadowsocks": outbound.update({"method": "aes-256-gcm", "password": match.group(2)})
                
        sb_config["outbounds"].insert(0, outbound)
        sb_config["route"] = {"rules": [{"outbound": "proxy"}], "final": "proxy"}
    except Exception:
        return None  
        
    config_filename = f"temp_{local_port}.json"
    with open(config_filename, "w") as f:
        json.dump(sb_config, f)
        
    proc = await asyncio.create_subprocess_exec(
        SING_BOX_PATH, "run", "-c", config_filename,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    await asyncio.sleep(0.4) 
    
    ping_ms = None
    try:
        import aiohttp
        from aiohttp_socks import ProxyConnector
        connector = ProxyConnector.from_url(f"socks5://127.0.0.1:{local_port}")
        async with aiohttp.ClientSession(connector=connector) as session:
            start_time = time.time()
            async with session.get(TEST_URL, timeout=TIMEOUT) as response:
                if response.status in [200, 204]:
                    ping_ms = int((time.time() - start_time) * 1000)
    except:
        pass
    finally:
        try:
            proc.terminate()
            await proc.wait()
        except:
            pass
        if os.path.exists(config_filename):
            os.remove(config_filename)
            
    return ping_ms

async def send_to_telegram(text):
    if not BOT_TOKEN: return
    import aiohttp
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": DESTINATION_CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    print("✅ Успешно опубликовано!")
                else:
                    print(f"❌ Код {resp.status}: {await resp.text()}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

async def check_all_configs():
    shutil.which("sing-box") or ensure_sing_box()
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

def save_and_export_subscriptions(valid_configs):
    all_clean_configs = []
    for proto, configs in valid_configs.items():
        with open(os.path.join(CONFIG_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(configs) + "\n" if configs else "No configs found.\n")
        if configs:
            with open(os.path.join(SUB_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(configs) + "\n")
            all_clean_configs.extend(configs)
    if all_clean_configs:
        with open(os.path.join(SUB_DIR, "all.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(all_clean_configs) + "\n")

async def main():
    valid_configs, all_scored_configs = await check_all_configs()
    save_and_export_subscriptions(valid_configs)
    
    proxies_list = load_collected_proxies()
    sorted_configs = sorted(all_scored_configs, key=lambda x: x["ping"])
    
    if sorted_configs or proxies_list:
        print("📊 Генерация постов в новом стиле...")
        
        # ПОСТ 1: Ключи V2Ray (Название, Пинг, Флаг)
        if sorted_configs:
            post_text = "🚀 <b>parserv2 | РАБОЧИЕ КОНФИГУРАЦИИ</b> 🚀\n\n"
            for idx, item in enumerate(sorted_configs, start=1):
                chunk = f"{item['flag']} <b>{idx}. [{item['proto'].upper()}]</b> ⚡ Ping: <code>{item['ping']}ms</code>\n<code>{item['config']}</code>\n\n"
                
                if len(post_text) + len(chunk) > 3900:
                    post_text += f"🆔 {DESTINATION_CHANNEL}"
                    await send_to_telegram(post_text)
                    await asyncio.sleep(3)
                    post_text = "🚀 <b>РАБОЧИЕ КОНФИГУРАЦИИ (Продолжение)</b>\n\n"
                post_text += chunk
                
            post_text += f"🆔 {DESTINATION_CHANNEL}\n📂 <i>Общие файлы подписок обновлены автоматически!</i>"
            await send_to_telegram(post_text)
            await asyncio.sleep(4)

        # ПОСТ 2: Выделенный пост под MTProto прокси в виде гиперссылок
        if proxies_list:
            sample_size = min(len(proxies_list), 7)
            selected_proxies = random.sample(proxies_list, sample_size)
            
            proxy_text = "🔗 <b>Свежие MTProto прокси для Telegram</b>\n"
            proxy_text += "<i>Нажмите на ссылку, чтобы моментально подключить:</i>\n\n"
            
            for p_idx, proxy in enumerate(selected_proxies, start=1):
                # Извлекаем хост для определения флага прокси
                host_match = re.search(r'server=([^&]+)', proxy)
                p_flag = get_flag_by_host(host_match.group(1)) if host_match else "🌐"
                
                proxy_text += f"• {p_flag} <a href='{proxy}'>Подключить MTProto Прокси №{p_idx}</a>\n"
                
            proxy_text += f"\n🆔 {DESTINATION_CHANNEL}"
            await send_to_telegram(proxy_text)
            
    else:
        print("⚠️ Новых рабочих элементов не найдено.")

if __name__ == "__main__":
    asyncio.run(main())
