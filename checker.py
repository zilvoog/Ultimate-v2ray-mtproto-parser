import os
import asyncio
import re
import aiohttp

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL = "@rjaviiiiii"                     # обязательно с @ для публичного канала
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]


def extract_host_port(config: str):
    """
    Извлекает хост и порт из конфига.
    Поддерживает форматы:
      - vless://..., vmess://..., trojan://... с @хост:порт
      - ss://...@хост:порт
      - hy2://...?server=хост&port=порт...
      - hy2://хост:порт
    Возвращает (хост, порт) или (None, None)
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

    return None, None


async def check(semaphore, proto, config):
    """Проверяет доступность сервера через TCP-соединение (таймаут 2 с)"""
    async with semaphore:
        host, port = extract_host_port(config)
        if not host or not port:
            return None
        try:
            conn = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=2.0
            )
            conn[1].close()   # закрываем соединение
            return {"proto": proto, "config": config.strip()}
        except:
            return None


async def send_text(session, text):
    """Отправляет текстовое сообщение в канал"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with session.post(url, json=data, timeout=10) as resp:
            if resp.status != 200:
                print(f"Send text error: {await resp.text()}")
    except Exception as e:
        print(f"Send text exception: {e}")


async def send_file(session, filename, content, caption):
    """Отправляет файл с рабочими конфигами"""
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

    semaphore = asyncio.Semaphore(50)   # TCP-проверка лёгкая
    tasks = []

    # 1. Читаем все файлы конфигов из папки Config
    for proto in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                cfg = line.strip()
                if cfg:
                    tasks.append(check(semaphore, proto, cfg))

    if not tasks:
        async with aiohttp.ClientSession() as session:
            await send_text(session, "⚠️ Нет конфигов для проверки")
        return

    print(f"🔍 Проверяем {len(tasks)} конфигов...")
    results = [r for r in await asyncio.gather(*tasks) if r]
    results.sort(key=lambda x: (x["proto"], x["config"]))

    print(f"✅ Найдено рабочих: {len(results)}")

    async with aiohttp.ClientSession() as session:
        if not results:
            await send_text(session, "❌ Рабочих конфигов не найдено")
            return

        # 2. Формируем красивое первое сообщение (первые 5, сгруппированы по протоколам)
        preview = results[:5]
        preview_by_proto = {}
        for r in preview:
            preview_by_proto.setdefault(r["proto"], []).append(r["config"])

        text = f"✅ <b>Найдено рабочих конфигов: {len(results)}</b>\n\n"
        for proto, configs in preview_by_proto.items():
            text += f"<b>{proto.upper()}</b>\n"
            text += "\n".join(f"<code>{c}</code>" for c in configs)
            text += "\n\n"

        if len(results) > 5:
            text += f"… и ещё {len(results) - 5} в прикреплённых файлах"

        await send_text(session, text)
        await asyncio.sleep(1)

        # 3. Отправляем файлы по протоколам (только для тех, у которых есть рабочие)
        grouped = {}
        for r in results:
            grouped.setdefault(r["proto"], []).append(r["config"])

        for proto, configs in grouped.items():
            filename = f"{proto}.txt"
            content = "\n".join(configs).encode("utf-8")
            caption = f"{proto.upper()}: {len(configs)} рабочих"
            await send_file(session, filename, content, caption)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
