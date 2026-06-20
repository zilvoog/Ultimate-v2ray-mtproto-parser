import os
import asyncio
import aiohttp
import re
from aiohttp_socks import ProxyConnector

# Безопасное получение конфигурации из переменных окружения GitHub Actions
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DESTINATION_CHANNEL = os.environ.get("DESTINATION_CHANNEL", "rjaviiiiii").strip().lstrip("@")
CONFIG_DIR = "Config"
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]


async def check_proxy(semaphore: asyncio.Semaphore, proto: str, config: str) -> dict | None:
    """Проверяет работоспособность конфига через SOCKS5"""
    async with semaphore:
        try:
            match = re.search(r'@([^:/]+):(\d+)', config)
            if not match:
                return None

            host, port = match.group(1), match.group(2)
            proxy_url = f"socks5://{host}:{port}"
            connector = ProxyConnector.from_url(proxy_url)
            timeout = aiohttp.ClientTimeout(total=3)

            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # generate_204 быстрее и реже блокируется в CI/CD, чем главная страница
                async with session.get("http://www.google.com/generate_204") as resp:
                    if resp.status in (200, 204):
                        return {"proto": proto, "config": config.strip()}
        except Exception:
            pass
        return None


async def send_text(session: aiohttp.ClientSession, text: str) -> bool:
    """Отправляет текстовое сообщение в Telegram"""
    if not BOT_TOKEN:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не задан в Secrets!")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"}

    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                print(f"❌ TG API Error (text): {await resp.text()}")
                return False            return True
    except Exception as e:
        print(f"❌ Ошибка сети (text): {e}")
        return False


async def send_file(session: aiohttp.ClientSession, filename: str, content: bytes, caption: str) -> bool:
    """Отправляет .txt файл в Telegram"""
    if not BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    form = aiohttp.FormData()
    form.add_field("chat_id", DESTINATION_CHANNEL)
    form.add_field("document", content, filename=filename, content_type="text/plain")
    form.add_field("caption", caption)
    form.add_field("parse_mode", "HTML")

    try:
        async with session.post(url, data=form, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                print(f"❌ TG API Error ({filename}): {await resp.text()}")
                return False
            print(f"📎 Файл {filename} отправлен")
            return True
    except Exception as e:
        print(f"❌ Ошибка сети ({filename}): {e}")
        return False


async def main():
    if not BOT_TOKEN:
        print("❌ Завершение: TELEGRAM_BOT_TOKEN отсутствует в переменных окружения")
        return

    semaphore = asyncio.Semaphore(20)
    tasks = []

    # Сбор задач на проверку
    for proto in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                configs = {line.strip() for line in f if line.strip()}
                for cfg in configs:
                    tasks.append(check_proxy(semaphore, proto, cfg))

    if not tasks:
        async with aiohttp.ClientSession() as s:
            await send_text(s, "⚠️ <b>ЧЕКЕР:</b>\nНет конфигов для проверки.")        return

    print(f"🔍 Проверяем {len(tasks)} конфигов...")
    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]

    # Сортировка: по протоколу, затем по конфигу
    results.sort(key=lambda x: (x["proto"], x["config"]))
    print(f"✅ Найдено рабочих: {len(results)}")

    async with aiohttp.ClientSession() as session:
        if results:
            # Группировка для файлов
            grouped: dict[str, list[str]] = {}
            for r in results:
                grouped.setdefault(r["proto"], []).append(r["config"])

            # Текстовое превью (первые 5 ключей)
            preview_limit = min(5, len(results))
            lines = [
                f"⚡ {r['proto'].upper()}\n<code>{r['config']}</code>"
                for r in results[:preview_limit]
            ]
            text = f"✅ <b>РАБОЧИХ КЛЮЧЕЙ: {len(results)}</b>\n\n" + "\n".join(lines)
            if len(results) > preview_limit:
                text += f"\n\n<i>...и ещё {len(results) - preview_limit} в файлах ниже 👇</i>"

            await send_text(session, text)
            await asyncio.sleep(1)

            # Отправка файлов по протоколам
            for proto, configs in grouped.items():
                filename = f"{proto}_working.txt"
                content = "\n".join(configs).encode("utf-8")
                caption = f"📂 <b>{proto.upper()}</b> — {len(configs)} шт."
                await send_file(session, filename, content, caption)
                await asyncio.sleep(1)
        else:
            msg = (
                "❌ <b>ПРОВЕРКА ЗАВЕРШЕНА</b>\n\n"
                f"Из {len(tasks)} конфигов не найдено ни одного рабочего.\n"
                "Возможные причины:\n"
                "• Блокировка IP GitHub Actions\n"
                "• Все прокси устарели"
            )
            await send_text(session, msg)


if __name__ == "__main__":
    asyncio.run(main())
