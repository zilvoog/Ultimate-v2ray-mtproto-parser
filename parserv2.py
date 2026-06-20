import os
import re
import json
import asyncio
import aiohttp

CHANNELS_FILE = "telegram_channels.json"
OUTPUT_DIR = "Config"

PATTERNS = {
    "vless": r"vless://[^\s\"'<]+",
    "vmess": r"vmess://[^\s\"'<]+",
    "shadowsocks": r"ss://[^\s\"'<]+",
    "trojan": r"trojan://[^\s\"'<]+",
    "hysteria2": r"hy2://[^\s\"'<]+",
    "mtproto": r"tg://proxy\?[^\s\"'<]+"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def fetch(session, username):
    url = f"https://t.me/s/{username}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=7)) as r:
            if r.status == 200:
                text = await r.text()
                channels = re.findall(r't\.me/([a-zA-Z0-9_]{5,30})', text)
                return text, list(set(channels))
    except Exception:
        pass
    return "", []

async def main():
    print("Start parser")
    
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        channels = [c.strip().lstrip("@") for c in json.load(f) if c.strip()]
    
    configs = {p: set() for p in PATTERNS}
    parsed = set()
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        queue = channels
        
        for _ in range(2):
            next_queue = []
            for ch in queue:
                if ch in parsed:
                    continue
                print(f"Parse: {ch}")
                text, found = await fetch(session, ch)
                parsed.add(ch)
                
                for proto, pattern in PATTERNS.items():
                    matches = re.findall(pattern, text)
                    configs[proto].update(m.replace("&amp;", "&") for m in matches)
                
                next_queue.extend(found[:3])
                await asyncio.sleep(0.8)
            queue = next_queue
    
    for proto, data in configs.items():
        if data:
            path = os.path.join(OUTPUT_DIR, f"{proto}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(data))
            print(f"Saved {len(data)} {proto}")
    
    print("Parser done")

if __name__ == "__main__":
    asyncio.run(main())
