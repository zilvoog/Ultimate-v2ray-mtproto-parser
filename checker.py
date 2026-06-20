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
TIMEOUT = 5  # Максимальное время ожидания ответа (в секундах)
TEST_URL = "http://cp.cloudflare.com/generate_204"

# Загрузка токена бота из секретов GitHub Actions
BOT_TOKEN = os.getenv("8624370798:AAGT0Bxx73nINuwYO1rzgjuUvF78cPpvg_k", None)
# Укажи здесь юзернейм своего канала (обязательно с @)
DESTINATION_CHANNEL = "@rjaviiiiii" 

PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]
SING_BOX_PATH = "./sing-box"

if not os.path.exists(SUB_DIR):
    os.makedirs(SUB_DIR)

def ensure_sing_box():
    """Проверяет наличие sing-box в системе, либо скачивает его для Linux amd64"""
    global SING_BOX_PATH
    if shutil.which("sing-box"):
        SING_BOX_PATH = "sing-box"
        return True
    if os.path.exists("./sing-box"):
        return True
        
    print("📥 Скачивание sing-box для точных HTTP-тестов...")
    try:
        url = "https://github.com/SagerNet/sing-box/releases/download/v1.11.0-alpha.5/sing-box-1.11.0-alpha.5-linux-amd64.tar.gz"
        archive_name = "sing-box.tar.gz"
        urllib.request.urlretrieve(url, archive_name)
        
        with tarfile.open(archive_name, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.endswith("sing-box"):
                    f = tar.extractfile(member)
                    if f:
                        with open("./sing-box", "wb") as dest:
                            dest.write(f.read())
                        break
        os.chmod("./sing-box", 0o755)
        os.remove(archive_name)
        print("⚙️ sing-box успешно установлен.")
        return True
    except Exception as e:
        print(f"❌ Не удалось скачать sing-box: {e}")
        return False

def load_configs():
    """Читает сырые конфиги, собранные файлом FetchConfig.py"""
    raw_data = {}
    for proto in PROTOCOLS:
        file_path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("No configs")]
                raw_data[proto] = lines
        else:
            raw_data[proto] = []
    return raw_data

def load_raw_proxies():
    """Читает собранные прокси для Телеграма из файла proxies.txt"""
    file_path = os.path.join(CONFIG_DIR, "proxies.txt")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and line.startswith("https://t.me/proxy")]
    return []

async def test_tg_proxy(proxy_url):
    """Проверяет доступность прокси-сервера Telegram (TCP-тест)"""
    try:
        server_match = re.search(r'server=([^&]+)', proxy_url)
        port_match = re.search(r'port=(\d+)', proxy_url)
        if not server_match or not port_match:
            return None
            
        server = server_match.group(1)
        port = int(port_match.group(2))
        
        conn = asyncio.open_connection(server, port)
        reader, writer = await asyncio.wait_for(conn, timeout=TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return proxy_url
    except:
        return None

async def test_http_via_sing_box(proto, config_url):
    """Запускает изолированный sing-box и замеряет скорость HTTP-ответа (пинг в мс)"""
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
            outbound = {
                "type": "vmess", "tag": "proxy",
                "server": data.get("add"), "server_port": int(data.get("port")),
                "uuid": data.get("id"), "security": "auto",
                "alter_id": int(data.get("aid", 0))
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
                "type": p_type, "tag": "proxy",
                "server": match.group(3), "server_port": int(match.group(4)),
            }
            if p_type == "vless": outbound.update({"uuid": match.group(2), "flow": ""})
            elif p_type == "trojan": outbound.update({"password": match.group(2)})
            elif p_type == "shadowsocks": outbound.update({"method": "aes-256-gcm", "password": match.group(2)})
                
        sb_config["outbounds"].insert(0, outbound)
        sb_config["route"] = {"rules": [{"outbound": "proxy"}], "final": "proxy"}
    except Exception:
        return None  # Ошибка парсинга ссылки
        
    config_filename = f"temp_{local_port}.json"
    with open(config_filename, "w") as f:
        json.dump(sb_config, f)
        
    proc = await asyncio.create_subprocess_exec(
        SING_BOX_PATH, "run", "-c", config_filename,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    
    await asyncio.sleep(0.4) # Даем время ядру подняться
    
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
    """Отправляет готовый пост в Telegram-канал"""
    if not BOT_TOKEN:
        print("⚠️ Секрет TELEGRAM_BOT_TOKEN не задан. Публикация отменена.")
        return
    import aiohttp
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": DESTINATION_CHANNEL,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    print("✅ Бот успешно опубликовал топ-5 конфигов и прокси в канал!")
                else:
                    print(f"❌ Ошибка публикации: {await resp.text()}")
    except Exception as e:
        print(f"❌ Не удалось отправить сообщение: {e}")

async def check_all_configs():
    ensure_sing_box()
    raw_configs = load_configs()
    valid_configs = {proto: [] for proto in PROTOCOLS}
    all_scored_configs = [] # Для отбора топ-5 по всему списку
    
    # 1. Тестируем V2Ray/Hysteria ключи
    for proto, configs in raw_configs.items():
        print(f"⏳ HTTP-тест протокола {proto.upper()} ({len(configs)} шт.)...")
        semaphore = asyncio.Semaphore(15)
        
        async def worker(cfg):
            async with semaphore: 
                return await test_http_via_sing_box(proto, cfg)
                
        tasks = [worker(config) for config in configs]
        if tasks:
            results = await asyncio.gather(*tasks)
            for config, ping in zip(configs, results):
                if ping is not None: 
                    valid_configs[proto].append(config)
                    all_scored_configs.append({"config": config, "ping": ping, "proto": proto})
                    
        print(f"   └─ Рабочих {proto.upper()}: {len(valid_configs[proto])}")
        
    # 2. Тестируем Telegram MTProto прокси
    raw_proxies = load_raw_proxies()
    print(f"⏳ Тестируем {len(raw_proxies)} собранных TG-прокси...")
    proxy_tasks = [test_tg_proxy(p) for p in raw_proxies]
    working_proxies = []
    if proxy_tasks:
        proxy_results = await asyncio.gather(*proxy_tasks)
        working_proxies = [p for p in proxy_results if p is not None]
    print(f"   └─ Рабочих ТГ-прокси: {len(working_proxies)}")
    
    return valid_configs, all_scored_configs, working_proxies

def save_and_export_subscriptions(valid_configs):
    """Сохраняет ВСЕ рабочие ключи в plain-text файлы подписок"""
    all_clean_configs = []
    for proto, configs in valid_configs.items():
        # Обновляем файлы в Config/
        with open(os.path.join(CONFIG_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(configs) + "\n" if configs else "No configs found.\n")
        # Создаем файлы в sub/
        if configs:
            with open(os.path.join(SUB_DIR, f"{proto}.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(configs) + "\n")
            all_clean_configs.extend(configs)
            
    if all_clean_configs:
        with open(os.path.join(SUB_DIR, "all.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(all_clean_configs) + "\n")

async def main():
    valid_configs, all_scored_configs, working_proxies = await check_all_configs()
    
    # 1. Сначала экспортируем ВСЕ рабочие ключи во все файлы подписок
    save_and_export_subscriptions(valid_configs)
    print("📂 Все рабочие ключи добавлены в файлы папки /sub")
    
    # 2. Сортируем абсолютно все проверенные ключи по пингу (от меньшего к большему)
    # И выбираем 5 самых лучших (быстрых)
    sorted_top_configs = sorted(all_scored_configs, key=lambda x: x["ping"])
    top_5_configs = sorted_top_configs[:5]
    
    # 3. Формируем единый красивый пост для публикации в канал
    post_text = "🔥 **TOP 5 FASTEST CONFIGS & PROXIES** 🔥\n\n"
    post_text += "⚡ Эти конфигурации показали наименьшую задержку при HTTP-тесте и добавлены в подписку:\n\n"
    
    if top_5_configs:
        for idx, item in enumerate(top_5_configs, start=1):
            post_text += f"📍 **{idx}. [{item['proto'].upper()}]** Ping: `{item['ping']}ms`\n"
            post_text += f"```{item['config']}```\n\n"
    else:
        post_text += "⚠️ Рабочие V2Ray конфигурации не найдены.\n\n"
        
    if working_proxies:
        post_text += "🔗 **Рабочие MTProto прокси для Telegram:**\n"
        # Берем до 5 штук рабочих прокси, чтобы пост не был гигантским
        for p_idx, proxy in enumerate(working_proxies[:5], start=1):
            post_text += f"• [MTProto Proxy №{p_idx}]({proxy})\n"
        post_text += "\n"
        
    post_text += f"🆔 {DESTINATION_CHANNEL}\n"
    post_text += "📂 _Все остальные проверенные ключи уже доступны в ваших файлах подписок!_"
    
    # Отправляем пост в канал
    if top_5_configs or working_proxies:
        await send_to_telegram(post_text)
    else:
        print("⚠️ Публикация отменена: не найдено ни одного живого элемента.")

if __name__ == "__main__":
    asyncio.run(main())
