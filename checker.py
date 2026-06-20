import os
import asyncio
import aiohttp
import re
from aiohttp_socks import ProxyConnector

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# ВАЖНО: Убрали @ и пробелы. Можно использовать username без @ или числовой ID канала
DESTINATION_CHANNEL = os.environ.get("DESTINATION_CHANNEL", "rjaviiiiii").strip().lstrip("@")
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]


async def check_http(semaphore, proto, config):
    async with semaphore:
        try:
            # Поддержка как IP, так и доменных имен в конфиге
            match = re.search(r'@([^:/]+):(\d+)', config)
            if not match:
                return None
            
            host, port = match.group(1), match.group(2)
            proxy_url = f"socks5://{host}:{port}"
            
            connector = ProxyConnector.from_url(proxy_url)
            timeout = aiohttp.ClientTimeout(total=3)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get("http://www.google.com/generate_204") as resp:
                    # generate_204 быстрее и надежнее для проверки прокси, чем главная страница
                    if resp.status == 204 or resp.status == 200:
                        return {"proto": proto, "config": config.strip()}
        except Exception:
            pass
        return None


async def send_to_telegram(session, results, title):
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не задан в переменных окружения!")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    for i in range(0, len(results), 5):
        chunk = results[i:i+5]
        text = title + "\n\n" + "\n".join([
            f"⚡ {r['proto'].upper()}\n<code>{r['config']}</code>" 
            for r in chunk
        ])
        
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
                    print(f"✅ Отправлено {len(chunk)} конфигов")
        except Exception as e:
            print(f"❌ Ошибка сети при отправке: {e}")
        
        await asyncio.sleep(1)  # Защита от Flood Control


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
        print("⚠️ Нет конфигов для проверки")
        return
        
    print(f"🔍 Проверяем {len(tasks)} конфигов...")
    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]
    
    print(f"✅ Найдено рабочих: {len(results)}")
    
    if results:
        async with aiohttp.ClientSession() as session:
            await send_to_telegram(session, results, "✅ <b>РАБОЧИЕ КЛЮЧИ:</b>")


if __name__ == "__main__":
    asyncio.run(main())
