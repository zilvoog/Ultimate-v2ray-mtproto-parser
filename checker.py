import os
import asyncio
import re
import aiohttp

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL = "@rjaviiiiii"                     # канал для отправки

# Список файлов для проверки: протоколы + whitelist
FILES = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2", "whitelist"]


def extract_host_port(config: str):
    """
    Извлекает хост и порт из конфига.
    Поддерживает все форматы: vless://, vmess://, ss://, trojan://, hy2://,
    а также обычные строки с @host:port или server=...&port=...
    """
    # vless, vmess, trojan – обычно @host:port
    match = re.search(r'@([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))

    # shadowsocks: ss://method:password@host:port или ss://base64@host:port
    match = re.search(r'ss://[^@]+@([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))

    # hysteria2 с параметрами: ...?server=host&port=...
    match = re.search(r'(?:server|host)=([^&]+)&.*?port=(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))

    # hysteria2: hy2://host:port
    match = re.search(r'hy2://([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))

    # Если ничего не найдено
    return None, None


async def check(semaphore, file_name, config):
    """Проверяет доступность сервера через TCP-соединение (таймаут 2 с)."""
    async with semaphore:
        host, port = extract_host_port(config)
        if not host or not port:
            return None
        try:
            conn = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=2.0
            )
            conn[1].close()
            return {"file": file_name, "config": config.strip()}
        except:
            return None


async def send_file(session, filename, content, caption):
    """Отправляет файл с рабочими конфигами."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    form = aiohttp.FormData()
    form.add_field("chat_id", CHANNEL)
    form.add_field("document", content, filename=filename, content_type="text/plain")
    form.add_field("caption", caption)
    form.add_field("parse_mode", "HTML")
    try:
        async with session.post(url, data=form, timeout=30) as resp:
            if resp.status != 200:
                print(f"Send file error: {await resp.text()}")
            else:
                print(f"Sent file: {filename}")
    except Exception as e:
        print(f"Send file exception: {e}")


async def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан")
        return

    semaphore = asyncio.Semaphore(50)
    tasks = []

    # 1. Читаем все файлы из списка FILES
    for file_name in FILES:
        path = os.path.join(CONFIG_DIR, f"{file_name}.txt")
        if not os.path.exists(path):
            print(f"ℹ️ Файл {file_name}.txt не найден, пропускаем.")
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                cfg = line.strip()
                if cfg:
                    tasks.append(check(semaphore, file_name, cfg))

    if not tasks:
        print("⚠️ Нет конфигов для проверки.")
        return

    print(f"🔍 Проверяем {len(tasks)} конфигов...")
    results = [r for r in await asyncio.gather(*tasks) if r]
    print(f"✅ Найдено рабочих: {len(results)}")

    if not results:
        print("❌ Рабочих конфигов не найдено.")
        return

    # 2. Группируем результаты по имени файла
    grouped = {}
    for r in results:
        grouped.setdefault(r["file"], []).append(r["config"])

    # 3. Отправляем файлы для каждой группы
    async with aiohttp.ClientSession() as session:
        for file_name, configs in grouped.items():
            filename = f"{file_name}.txt"
            content = "\n".join(configs).encode("utf-8")
            caption = f"{file_name.upper()}: {len(configs)} рабочих"
            await send_file(session, filename, content, caption)
            await asyncio.sleep(1)   # пауза между файлами

if __name__ == "__main__":
    asyncio.run(main())
