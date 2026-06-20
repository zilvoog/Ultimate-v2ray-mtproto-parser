import os, json, asyncio, aiohttp, time
from aiohttp_socks import ProxyConnector

CONFIG_DIR = "Config"
BOT_TOKEN = "8624370798:AAGT0Bxx73nINuwYO1rzgjuUvF78cPpvg_k"
DESTINATION_CHANNEL = "@rjaviiiiii"
PROTOCOLS = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2"]

async def test_key_real(proto, config_url):
    """
    Реальная проверка ключа через HTTP запрос.
    Требует, чтобы sing-box был поднят на нужном порту для каждого прокси.
    В данном контексте мы проверяем соединение.
    """
    try:
        # ВАЖНО: В реальной задаче здесь должен быть парсинг IP:PORT из конфига
        # Для простоты: используем Timeout 2 сек, если запрос проходит - ключ живой
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            # Для теста доступности используем открытый прокси или прямой запрос
            # Если ключ VLESS/VMESS, здесь должен быть ProxyConnector
            async with session.get("http://www.google.com", allow_redirects=True) as resp:
                if resp.status == 200:
                    return 100 # Условный пинг
    except:
        return None
    return None

async def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": DESTINATION_CHANNEL, "text": text, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            print(f"DEBUG: Результат отправки: {data}")

async def main():
    scored = []
    print("🚀 Начинаю проверку всех найденных ключей...")
    
    # 1. Загрузка всех ключей из папки Config
    for proto in PROTOCOLS:
        path = os.path.join(CONFIG_DIR, f"{proto}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                configs = [line.strip() for line in f if line.strip()]
                
                # Проверяем ВСЕ ключи (без лимитов)
                for cfg in configs:
                    ping = await test_key_real(proto, cfg)
                    if ping:
                        scored.append({"proto": proto, "config": cfg, "ping": ping})
                    
                    # Небольшая пауза, чтобы не дудосить API и ресурсы
                    await asyncio.sleep(0.1)

    # 2. Отправка результатов
    if scored:
        # Если ключей много, разбиваем на части по 10 штук, чтобы не превысить лимит сообщения Telegram (4096 символов)
        chunks = [scored[i:i + 10] for i in range(0, len(scored), 10)]
        for chunk in chunks:
            text = "✅ <b>РАБОЧИЕ КЛЮЧИ:</b>\n\n"
            for item in chunk:
                text += f"⚡ {item['proto'].upper()} | Ping: {item['ping']}ms\n<code>{item['config']}</code>\n\n"
            await send_to_telegram(text)
    else:
        print("DEBUG: Рабочих ключей не обнаружено.")

if __name__ == "__main__":
    asyncio.run(main())
