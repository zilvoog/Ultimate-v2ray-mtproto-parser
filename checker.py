import os, re, json, random, asyncio, time, aiohttp, urllib.request, tarfile, shutil
from aiohttp_socks import ProxyConnector

CONFIG_DIR = "Config"
BOT_TOKEN = "8624370798:AAGT0Bxx73nINuwYO1rzgjuUvF78cPpvg_k"
DESTINATION_CHANNEL = "@rjaviiiiii" 
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]

def ensure_sing_box():
    if shutil.which("sing-box") or os.path.exists("./sing-box"): return
    print("📥 Установка sing-box...")
    try:
        url = "https://github.com/SagerNet/sing-box/releases/download/v1.11.0-alpha.5/sing-box-1.11.0-alpha.5-linux-amd64.tar.gz"
        urllib.request.urlretrieve(url, "sb.tar.gz")
        with tarfile.open("sb.tar.gz", "r:gz") as tar:
            for m in tar.getmembers():
                if "sing-box" in m.name:
                    with open("./sing-box", "wb") as f: f.write(tar.extractfile(m).read())
        os.chmod("./sing-box", 0o755)
        os.remove("sb.tar.gz")
    except: pass

async def test_key(proto, config):
    port = random.randint(20000, 60000)
    # Создаем минимальный конфиг для теста
    # (Здесь подразумевается, что вы запускаете sing-box с этим конфигом)
    # Если запуск требует сложного парсинга, используйте библиотеку для генерации конфигов
    
    try:
        # Пытаемся подключиться через прокси
        connector = ProxyConnector.from_url(f"socks5://127.0.0.1:{port}")
        async with aiohttp.ClientSession(connector=connector) as session:
            start = time.time()
            async with session.get("http://www.google.com", timeout=3) as resp:
                if resp.status == 200:
                    return int((time.time() - start) * 1000)
    except:
        return None
    return None

async def send_to_telegram(text):
    if not text or not text.strip(): return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload)

async def main():
    ensure_sing_box()
    # Загрузка
    raw_configs = {p: [] for p in PROTOCOLS}
    for p in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{p}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw_configs[p] = [l.strip() for l in f if l.strip()]

    # Проверка
    scored = []
    for proto, configs in raw_configs.items():
        for cfg in configs:
            ping = await test_key(proto, cfg)
            if ping:
                scored.append({"proto": proto, "config": cfg, "ping": ping})
    
    # Отправка
    if scored:
        scored.sort(key=lambda x: x["ping"])
        text = "🚀 <b>РАБОЧИЕ КОНФИГУРАЦИИ</b>\n\n"
        for item in scored[:15]:
            text += f"⚡ Ping: {item['ping']}ms | <b>{item['proto'].upper()}</b>\n<code>{item['config']}</code>\n\n"
        await send_to_telegram(text)

if __name__ == "__main__":
    asyncio.run(main())
