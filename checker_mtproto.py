import os, asyncio, re

CONFIG_DIR = "Config"
BOT_TOKEN = "8624370798:AAGT0Bxx73nINuwYO1rzgjuUvF78cPpvg_k"
DESTINATION_CHANNEL = "@rjaviiiiii"

async def is_port_open(host, port):
    try:
        conn = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2)
        conn[1].close()
        return True
    except:
        return False

async def main():
    path = os.path.join(CONFIG_DIR, "mtproto.txt")
    if not os.path.exists(path): return

    with open(path, "r", encoding="utf-8") as f:
        configs = list(set([line.strip() for line in f if line.strip()]))

    working_mt = []
    for cfg in configs:
        match = re.search(r'server=([^&]+)&port=(\d+)', cfg)
        if match:
            if await is_port_open(match.group(1), int(match.group(2))):
                working_mt.append(cfg)

    for i in range(0, len(working_mt), 5):
        chunk = working_mt[i:i+5]
        text = "✅ <b>РАБОЧИЕ MTPROTO:</b>\n\n"
        for cfg in chunk:
            text += f"<code>{cfg}</code>\n\n"
        # Отправка... (логика та же, что в основном чекере)
        # Можно вынести send_to_telegram в общий utils.py, если захотите
        import aiohttp
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"}
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=payload)
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
