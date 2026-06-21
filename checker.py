import os
import asyncio
import re
import aiohttp

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL = "@rjaviiiiii"
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]

def extract_host_port(config: str):
    """Извлекает хост и порт из конфига (поддерживает разные форматы)"""
    # Попытка найти @host:port (vless, vmess, trojan)
    match = re.search(r'@([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))
    # Для shadowsocks: ss://base64@host:port или ss://method:password@host:port
    match = re.search(r'ss://[^@]+@([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))
    # Для hysteria2: hy2://...?server=host&port=... или hy2://host:port
    match = re.search(r'(?:server|host)=([^&]+)&.*?port=(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))
    match = re.search(r'hy2://([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))
    # Если ничего не найдено
    return None, None

async def check(semaphore, proto, config):
    async with semaphore:
        host, port = extract_host_port(config)
        if not host or not port:
            return None
        try:
            # Попытка TCP-подключения с таймаутом 2 секунды
            conn = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=2
            )
            conn[1].close()  # закрываем соединение
            return {"proto": proto, "config": config.strip()}
        except:
            return None

async def send_text(session, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL, "text": text, "parse_mode": "HTML"}
    try:
        async with session.post(url, json=data, timeout=10) as r:
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
        async with session.post(url, data=form, timeout=30) as r:
            if r.status != 200:
                print(f"File error: {await r.text()}")
            else:
                print(f"Sent: {filename}")
    except Exception as e:
        print(f"File send error: {e}")

async def main():
    if not BOT_TOKEN:
        print("No token")
        return

    semaphore = asyncio.Semaphore(50)  # можно больше, т.к. проверка лёгкая
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
            await send_text(s, "No configs to check")
        return

    print(f"Checking {len(tasks)} configs")
    results = [r for r in await asyncio.gather(*tasks) if r]
    results.sort(key=lambda x: (x["proto"], x["config"]))
    print(f"Found working: {len(results)}")

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
                filename = f"{proto}.txt"
                content = "\n".join(configs).encode("utf-8")
                caption = f"{proto.upper()}: {len(configs)}"
                await send_file(session, filename, content, caption)
                await asyncio.sleep(1)
        else:
            await send_text(session, "No working configs found")

if __name__ == "__main__":
    asyncio.run(main())
