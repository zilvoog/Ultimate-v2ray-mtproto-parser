import os
import asyncio
import re
import aiohttp
import socket
from typing import Optional

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DESTINATION_CHANNEL = "@rjaviiiiii"

# Преобразование кода страны в флаг-эмодзи
def country_to_flag(country_code: str) -> str:
    if not country_code or len(country_code) != 2:
        return "🌐"
    # Unicode флаги: буквы A-Z -> кодовые точки 127397..127462
    return "".join(chr(ord(ch) + 127397) for ch in country_code.upper())

async def get_country_code(host: str, session: aiohttp.ClientSession) -> Optional[str]:
    """Возвращает двухбуквенный код страны для IP-адреса (или None)"""
    # Проверяем, является ли хост IP-адресом (простейшая проверка)
    if not re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
        # Если это домен, пробуем разрешить в IP (только для гео)
        try:
            # Блокирующий вызов, но мы запускаем в отдельном потоке через run_in_executor
            loop = asyncio.get_running_loop()
            ip = await loop.run_in_executor(None, socket.gethostbyname, host)
            host = ip
        except:
            return None
    url = f"http://ip-api.com/json/{host}?fields=countryCode"
    try:
        async with session.get(url, timeout=3) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("countryCode")
    except:
        pass
    return None

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

    # 1. Проверка работоспособности
    semaphore = asyncio.Semaphore(30)
    tasks = [check_mt(semaphore, cfg) for cfg in configs]
    results = [r for r in await asyncio.gather(*tasks) if r]

    if not results:
        print("No working mtproto configs")
        return

    # 2. Получение стран для каждого сервера
    geo_semaphore = asyncio.Semaphore(15)  # ограничиваем параллельные запросы к API
    async with aiohttp.ClientSession() as session:
        country_tasks = []
        for cfg in results:
            # Извлекаем сервер
            match = re.search(r'server=([^&]+)', cfg)
            host = match.group(1) if match else None
            if host:
                country_tasks.append(get_country_code(host, session))
            else:
                country_tasks.append(asyncio.sleep(0, result=None))  # заглушка

        # Ждём все ответы с таймаутом, чтобы не зависнуть
        countries = await asyncio.gather(*[asyncio.wait_for(t, timeout=5) for t in country_tasks])

    # 3. Формируем ссылки с флагами
    links = []
    for idx, (cfg, country) in enumerate(zip(results, countries), 1):
        # Преобразуем конфиг в tg:// ссылку, если ещё не
        if not cfg.startswith("tg://"):
            link = re.sub(r'^.*?(server=)', r'tg://proxy?\1', cfg)
        else:
            link = cfg
        # Добавляем флаг
        flag = country_to_flag(country) if country else "🌐"
        links.append(f'{flag} <a href="{link}">MTProxy #{idx}</a>')

    header = "✅ <b>РАБОЧИЕ MTPROXY (нажмите для подключения):</b>\n\n"
    body = "\n".join(links)
    full_text = header + body

    # 4. Отправка с учётом лимита 4096 символов
    MAX_LEN = 4096
    if len(full_text) <= MAX_LEN:
        async with aiohttp.ClientSession() as session:
            await send_message(session, full_text)
    else:
        parts = []
        current = header
        for link in links:
            if len(current) + len(link) + 1 > MAX_LEN:
                parts.append(current)
                current = header
            current += link + "\n"
        if current.strip():
            parts.append(current)

        async with aiohttp.ClientSession() as session:
            for part in parts:
                await send_message(session, part)
                await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
