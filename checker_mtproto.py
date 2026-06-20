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

async def send_telegram(text):
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан!")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    print(f"❌ TG Error: {await resp.text()}")
                else:
                    print("✅ Сообщение отправлено в Telegram")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

async def main():
    path = os.path.join(CONFIG_DIR, "mtproto.txt")
    if not os.path.exists(path):
        msg = "⚠️ <b>MTPROTO ЧЕКЕР:</b>\nФайл mtproto.txt не найден (парсер не собрал MTProto)."
        print("Файл mtproto.txt не найден")
        await send_telegram(msg)
        return
        
    with open(path, "r", encoding="utf-8") as f:
        configs = list(set(line.strip() for line in f if line.strip()))
    
    if not configs:
        await send_telegram("⚠️ <b>MTPROTO:</b> Нет конфигов для проверки.")
        return
        
    print(f"🔍 Проверяем {len(configs)} MTProto...")
    semaphore = asyncio.Semaphore(30)
    tasks = [check_mt(semaphore, cfg) for cfg in configs]
    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]
    
    print(f"✅ Найдено рабочих MTProto: {len(results)}")
    
    if results:
        title = "✅ <b>РАБОЧИЕ MTPROTO:</b>\n\n"
        for i in range(0, len(results), 5):
            chunk = results[i:i+5]
            text = title + "\n".join([f"<code>{c}</code>" for c in chunk])
            await send_telegram(text)
            await asyncio.sleep(1)
    else:
        msg = "❌ <b>MTPROTO ПРОВЕРКА:</b>\nНе найдено рабочих MTProto прокси."
        await send_telegram(msg)

if __name__ == "__main__":
    asyncio.run(main())
