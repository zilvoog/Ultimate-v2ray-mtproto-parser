import os
import asyncio
import aiohttp
import re

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DESTINATION_CHANNEL = os.environ.get("DESTINATION_CHANNEL", "rjaviiiiii").strip().lstrip("@")


async def check_mt(semaphore, config):
    async with semaphore:
        match = re.search(r'server=([^&:\s]+)[&:]port=(\d+)', config)
        if not match:
            return None
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(match.group(1), int(match.group(2))),
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            return config.strip()
        except Exception:
            return None


async def send_text(session, text):
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан!")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"}
    try:
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                print(f"❌ TG Text Error: {await resp.text()}")
                return False
            return True
    except Exception as e:
        print(f"❌ Ошибка отправки текста: {e}")
        return False


async def send_file(session, filename, content_bytes, caption):
    if not BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    form = aiohttp.FormData()
    form.add_field("chat_id", DESTINATION_CHANNEL)    form.add_field("document", content_bytes, filename=filename, content_type="text/plain")
    form.add_field("caption", caption)
    form.add_field("parse_mode", "HTML")
    try:
        async with session.post(url, data=form, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                print(f"❌ TG File Error ({filename}): {await resp.text()}")
                return False
            print(f"📎 Файл {filename} отправлен")
            return True
    except Exception as e:
        print(f"❌ Ошибка отправки файла {filename}: {e}")
        return False


async def main():
    if not BOT_TOKEN:
        print("❌ Завершение: TELEGRAM_BOT_TOKEN отсутствует")
        return

    path = os.path.join(CONFIG_DIR, "mtproto.txt")
    if not os.path.exists(path):
        async with aiohttp.ClientSession() as s:
            await send_text(s, "⚠️ <b>MTPROTO ЧЕКЕР:</b>\nФайл mtproto.txt не найден.")
        return

    with open(path, "r", encoding="utf-8") as f:
        configs = list({line.strip() for line in f if line.strip()})

    if not configs:
        async with aiohttp.ClientSession() as s:
            await send_text(s, "⚠️ <b>MTPROTO:</b> Нет конфигов для проверки.")
        return

    print(f"🔍 Проверяем {len(configs)} MTProto...")
    semaphore = asyncio.Semaphore(30)
    tasks = [check_mt(semaphore, cfg) for cfg in configs]
    raw_results = await asyncio.gather(*tasks)
    results = sorted([r for r in raw_results if r is not None])
    print(f"✅ Найдено рабочих MTProto: {len(results)}")

    async with aiohttp.ClientSession() as session:
        if results:
            preview_limit = min(5, len(results))
            lines = [f"<code>{c}</code>" for c in results[:preview_limit]]
            text = f"✅ <b>РАБОЧИХ MTPROTO: {len(results)}</b>\n\n" + "\n".join(lines)
            if len(results) > preview_limit:
                text += f"\n\n<i>...и ещё {len(results) - preview_limit} в файле ниже 👇</i>"

            await send_text(session, text)            await asyncio.sleep(1)

            filename = "mtproto_working.txt"
            content = "\n".join(results).encode("utf-8")
            caption = f"📂 <b>MTPROTO</b> — {len(results)} шт."
            await send_file(session, filename, content, caption)
        else:
            msg = (
                "❌ <b>MTPROTO ПРОВЕРКА ЗАВЕРШЕНА</b>\n\n"
                f"Из {len(configs)} конфигов не найдено ни одного рабочего."
            )
            await send_text(session, msg)


if __name__ == "__main__":
    asyncio.run(main())
