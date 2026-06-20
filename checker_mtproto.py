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

async def send_message(session, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": DESTINATION_CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with session.post(url, json=data, timeout=10) as resp:
            if resp.status != 200:
                print(f"Send error: {await resp.text()}")
    except Exception as e:
        print(f"Send exception: {e}")

async def main():
    path = os.path.join(CONFIG_DIR, "mtproto.txt")
    if not os.path.exists(path):
        print("mtproto.txt not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        configs = list(set(line.strip() for line in f if line.strip()))

    semaphore = asyncio.Semaphore(30)
    tasks = [check_mt(semaphore, cfg) for cfg in configs]
    results = [r for r in await asyncio.gather(*tasks) if r]

    if not results:
        print("No working mtproto configs")
        return

    # Преобразуем каждый рабочий конфиг в ссылку tg://proxy
    links = []
    for idx, cfg in enumerate(results, 1):
        # Если строка не начинается с tg://, заменяем префикс до server= на tg://proxy?
        if not cfg.startswith("tg://"):
            link = re.sub(r'^.*?(server=)', r'tg://proxy?\1', cfg)
        else:
            link = cfg
        # Экранируем спецсимволы для HTML (амперсанды уже корректны)
        links.append(f'<a href="{link}">MTProto #{idx}</a>')

    header = "✅ <b>РАБОЧИЕ MTPROTO (нажмите для подключения):</b>\n\n"
    body = "\n".join(links)
    full_text = header + body

    # Лимит Telegram на длину сообщения
    MAX_LEN = 4096
    if len(full_text) <= MAX_LEN:
        async with aiohttp.ClientSession() as session:
            await send_message(session, full_text)
    else:
        # Разбиваем, сохраняя целостность ссылок
        parts = []
        current = header
        for link in links:
            if len(current) + len(link) + 1 > MAX_LEN:
                parts.append(current)
                current = header  # новая часть начинается с заголовка
            current += link + "\n"
        if current.strip():
            parts.append(current)

        async with aiohttp.ClientSession() as session:
            for part in parts:
                await send_message(session, part)
                await asyncio.sleep(0.5)  # небольшая задержка между сообщениями

if __name__ == "__main__":
    asyncio.run(main())
