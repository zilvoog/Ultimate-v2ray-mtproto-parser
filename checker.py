import os, asyncio, aiohttp, re
from aiohttp_socks import ProxyConnector

CONFIG_DIR = "Config"
BOT_TOKEN = "8624370798:AAGT0Bxx73nINuwYO1rzgjuUvF78cPpvg_k"
DESTINATION_CHANNEL = "@rjaviiiiii"
# Только HTTP-протоколы
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]

def parse_proxy_params(config):
    try:
        # Регулярка для извлечения IP и порта
        match = re.search(r'@([\d\.]+):(\d+)', config)
        if match:
            return match.group(1), int(match.group(2))
    except: pass
    return None, None

async def test_key_strict(config):
    ip, port = parse_proxy_params(config)
    if not ip or not port: return False
    
    try:
        connector = ProxyConnector.from_url(f"socks5://{ip}:{port}")
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.get("http://www.google.com") as resp:
                return resp.status == 200
    except:
        return False

async def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=payload)

async def main():
    scored = []
    for proto in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                configs = list(set([line.strip() for line in f if line.strip()]))
                for cfg in configs:
                    if await test_key_strict(cfg):
                        scored.append({"proto": proto, "config": cfg})
                    await asyncio.sleep(0.05)

    if scored:
        for i in range(0, len(scored), 5):
            chunk = scored[i:i+5]
            text = "✅ <b>РАБОЧИЕ КЛЮЧИ:</b>\n\n"
            for item in chunk:
                text += f"⚡ {item['proto'].upper()}\n<code>{item['config']}</code>\n\n"
            await send_to_telegram(text)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
