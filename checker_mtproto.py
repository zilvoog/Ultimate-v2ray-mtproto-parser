import os
import asyncio
import aiohttp
import re

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DESTINATION_CHANNEL = os.environ.get("DESTINATION_CHANNEL", "rjaviiiiii").strip().lstrip("@")


async def check_mt(semaphore, config):
    async with semaphore:
        try:
            # Поддержка разных форматов MTProto ссылок
            match = re.search(r'server=([^&]+)&port=(\d+)', config)
            if not match:
                # Fallback для формата tg://proxy?server=...
                match = re.search(r'server=([^&:\s]+)[&:]port=(\d+)', config)
            
            if not match:
                return None
                
            host = match.group(1)
            port = int(match.group(2))
            
            # Простая TCP проверка доступности сервера
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), 
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            return config.strip()
            
        except Exception:
            return None


async def send_to_telegram(session, results, title):
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан в переменных окружения!")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    for i in range(0, len(results), 5):
        chunk = results[i:i+5]
        text = title + "\n\n" + "\n".join([f"<code>{c}</code>" for c in chunk])
        
        payload = {
            "chat_id": DESTINATION_CHANNEL,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                answer = await resp.json()
                if resp.status != 200:
                    print(f"❌ Telegram API Error: {answer}")
                else:
                    print(f"✅ Отправлено {len(chunk)} MTProto")
        except Exception as e:
            print(f"❌ Ошибка сети при отправке: {e}")
        
        await asyncio.sleep(1)


async def main():
    path = os.path.join(CONFIG_DIR, "mtproto.txt")
    if not os.path.exists(path):
        print("⚠️ Файл mtproto.txt не найден")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        configs = list(set(line.strip() for line in f if line.strip()))
    
    if not configs:
        print("⚠️ Нет MTProto конфигов для проверки")
        return
        
    print(f"🔍 Проверяем {len(configs)} MTProto...")
    semaphore = asyncio.Semaphore(30)
    tasks = [check_mt(semaphore, cfg) for cfg in configs]
    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]
    
    print(f"✅ Найдено рабочих MTProto: {len(results)}")
    
    if results:
        async with aiohttp.ClientSession() as session:
            await send_to_telegram(session, results, "✅ <b>РАБОЧИЕ MTPROTO:</b>")


if __name__ == "__main__":
    asyncio.run(main())
