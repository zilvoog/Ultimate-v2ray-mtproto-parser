import os
import asyncio
import aiohttp
import re
from aiohttp_socks import ProxyConnector

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL = "rjaviiiiii"
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]

async def check(semaphore, proto, config):
    async with semaphore:
        try:
            match = re.search(r'@([^:/]+):(\d+)', config)
            if not match:
                return None
            host, port = match.group(1), match.group(2)
            proxy = f"socks5://{host}:{port}"
            conn = ProxyConnector.from_url(proxy)
            timeout = aiohttp.ClientTimeout(total=3)
            
            async with aiohttp.ClientSession(connector=conn, timeout=timeout) as s:
                async with s.get("http://www.google.com/generate_204") as r:
                    if r.status in (200, 204):
                        return {"proto": proto, "config": config.strip()}
        except Exception:
            pass
        return None

async def send_text(session, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL, "text": text, "parse_mode": "HTML"}
    try:
        async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                print(f"Error: {await r.text()}")
    except Exception as e:
        print(f"Send error: {e}")

async def send_file(session, filename, content, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    form = aiohttp.FormData()
    form.add_field("chat_id", CHANNEL)
    form.add_field("document", content, filename=filename, content_type="text/plain")
    form.add_field("caption", caption)
    form.add_field("parse_mode", "HTML")
    try:
        async with session.post(url, data=form, timeout=aiohttp.ClientTimeout(total=30)) as r:
            if r.status != 200:                print(f"File error: {await r.text()}")
            else:
                print(f"Sent: {filename}")
    except Exception as e:
        print(f"File send error: {e}")

async def main():
    if not BOT_TOKEN:
        print("No token")
        return
    
    semaphore = asyncio.Semaphore(20)
    tasks = []
    
    for proto in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    cfg = line.strip()
                    if cfg:
                        tasks.append(check(semaphore, proto, cfg))
    
    if not tasks:
        async with aiohttp.ClientSession() as s:
            await send_text(s, "No configs")
        return
    
    print(f"Checking {len(tasks)} configs")
    results = [r for r in await asyncio.gather(*tasks) if r]
    results.sort(key=lambda x: (x["proto"], x["config"]))
    print(f"Found: {len(results)}")
    
    async with aiohttp.ClientSession() as session:
        if results:
            grouped = {}
            for r in results:
                grouped.setdefault(r["proto"], []).append(r["config"])
            
            preview = results[:5]
            text = f"Found: {len(results)}\n\n"
            text += "\n".join(f"{r['proto'].upper()}\n{r['config']}" for r in preview)
            if len(results) > 5:
                text += f"\n\n...and {len(results) - 5} more in files"
            
            await send_text(session, text)
            await asyncio.sleep(1)
            
            for proto, configs in grouped.items():
                filename = f"{proto}.txt"                content = "\n".join(configs).encode("utf-8")
                caption = f"{proto.upper()}: {len(configs)}"
                await send_file(session, filename, content, caption)
                await asyncio.sleep(1)
        else:
            await send_text(session, "No working configs found")

if __name__ == "__main__":
    asyncio.run(main())
