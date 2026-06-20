import os, asyncio, aiohttp, re
from aiohttp_socks import ProxyConnector

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DESTINATION_CHANNEL = "@rjaviiiiii"
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]

async def check_http(semaphore, proto, config):
    async with semaphore:
        try:
            match = re.search(r'@([\d\.]+):(\d+)', config)
            if not match: return None
            connector = ProxyConnector.from_url(f"socks5://{match.group(1)}:{match.group(2)}")
            async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get("http://www.google.com") as resp:
                    return {"proto": proto, "config": config} if resp.status == 200 else None
        except: return None

async def main():
    semaphore = asyncio.Semaphore(20) # 20 параллельных проверок
    tasks = []
    for proto in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for cfg in set(f.read().splitlines()):
                    if cfg.strip():
                        tasks.append(check_http(semaphore, proto, cfg))
    
    results = [r for r in await asyncio.gather(*tasks) if r]
    
    if results:
        async with aiohttp.ClientSession() as s:
            for i in range(0, len(results), 5):
                text = "✅ <b>РАБОЧИЕ КЛЮЧИ:</b>\n\n" + "\n".join([f"⚡ {r['proto'].upper()}\n<code>{r['config']}</code>" for r in results[i:i+5]])
                await s.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"})
                await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
