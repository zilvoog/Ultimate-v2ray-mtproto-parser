import os
import asyncio
import aiohttp
import re
from aiohttp_socks import ProxyConnector

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Убираем @ и пробелы для корректной работы API
DESTINATION_CHANNEL = os.environ.get("DESTINATION_CHANNEL", "rjaviiiiii").strip().lstrip("@")
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]


async def check_http(semaphore, proto, config):
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
                async with session.get("http://www.google.com/generate_204") as resp:
                    if resp.status in (200, 204):
                        return {"proto": proto, "config": config.strip()}
        except Exception:
            pass
        return None


async def send_telegram_text(session, text):
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан!")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"}
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                err = await resp.text()
                print(f"❌ TG Text Error: {err}")
                return False
            return True
    except Exception as e:
        print(f"❌ Ошибка отправки текста: {e}")
        return False

async def send_telegram_file(session, filename, content_bytes, caption=""):
    if not BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    data = aiohttp.FormData()
    data.add_field('chat_id', DESTINATION_CHANNEL)
    data.add_field('document', content_bytes, filename=filename, content_type='text/plain')
    if caption:
        data.add_field('caption', caption)
        data.add_field('parse_mode', 'HTML')
    try:
        async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                err = await resp.text()
                print(f"❌ TG File Error ({filename}): {err}")
                return False
            print(f"📎 Файл {filename} успешно отправлен")
            return True
    except Exception as e:
        print(f"❌ Ошибка отправки файла {filename}: {e}")
        return False


async def main():
    semaphore = asyncio.Semaphore(20)
    tasks = []
    for proto in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                configs = set(line.strip() for line in f if line.strip())
                for cfg in configs:
                    tasks.append(check_http(semaphore, proto, cfg))

    if not tasks:
        msg = "⚠️ <b>ПАРСЕР:</b>\nНет конфигов для проверки."
        print("Нет конфигов для проверки")
        async with aiohttp.ClientSession() as s:
            await send_telegram_text(s, msg)
        return

    print(f"🔍 Проверяем {len(tasks)} конфигов...")
    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]
    results.sort(key=lambda x: (x['proto'], x['config']))
    print(f"✅ Найдено рабочих: {len(results)}")

    async with aiohttp.ClientSession() as session:
        if results:
            grouped = {}            for r in results:
                grouped.setdefault(r['proto'], []).append(r['config'])

            preview_count = min(5, len(results))
            preview_text = f"✅ <b>НАЙДЕНО РАБОЧИХ КЛЮЧЕЙ: {len(results)}</b>\n\n"
            preview_text += "\n".join([
                f"⚡ {r['proto'].upper()}\n<code>{r['config']}</code>"
                for r in results[:preview_count]
            ])
            if len(results) > preview_count:
                preview_text += f"\n\n<i>...и еще {len(results) - preview_count} ключей в прикрепленных файлах 👇</i>"

            await send_telegram_text(session, preview_text)
            await asyncio.sleep(1)

            for proto, configs in grouped.items():
                filename = f"{proto}_working.txt"
                content = "\n".join(configs).encode("utf-8")
                caption = f"📂 <b>{proto.upper()}</b>: {len(configs)} шт."
                await send_telegram_file(session, filename, content, caption)
                await asyncio.sleep(1)
        else:
            msg = (
                "❌ <b>ПРОВЕРКА ЗАВЕРШЕНА</b>\n\n"
                f"Из {len(tasks)} проверенных конфигов не найдено ни одного рабочего.\n"
                "Возможные причины:\n"
                "• Блокировка IP GitHub Actions\n"
                "• Все прокси устарели"
            )
            await send_telegram_text(session, msg)


if __name__ == "__main__":
    asyncio.run(main())
