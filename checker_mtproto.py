import os
import asyncio
import re
import aiohttp

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DESTINATION_CHANNEL = "@rjaviiiiii"

async def check_mt(semaphore, config):
    async with semaphore:
        match = re.search(r'server=([^&]+)&port=(\d+)', config)
        if not match:
            return None
        try:
            conn = await asyncio.wait_for(
                asyncio.open_connection(match.group(1), int(match.group(2))),
                timeout=1.5
            )
            conn[1].close()
            return config
        except:
            return None

async def main():
    path = os.path.join(CONFIG_DIR, "mtproto.txt")
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        configs = list(set(line.strip() for line in f if line.strip()))

    semaphore = asyncio.Semaphore(30)
    tasks = [check_mt(semaphore, cfg) for cfg in configs]
    results = [r for r in await asyncio.gather(*tasks) if r]

    if results:
        async with aiohttp.ClientSession() as s:
            for i in range(0, len(results), 5):
                text = "✅ <b>РАБОЧИЕ MTPROTO:</b>\n\n" + "\n".join(
                    f"<code>{c}</code>" for c in results[i:i+5]
                )
                await s.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"}
                )
                await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
