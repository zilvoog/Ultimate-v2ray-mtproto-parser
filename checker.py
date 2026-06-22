import os
import asyncio
import re
import aiohttp

CONFIG_DIR = "Config"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL = os.environ.get("TELEGRAM_CHANNEL")
if not CHANNEL:
    print("TELEGRAM_CHANNEL environment variable is not set")
    exit(1)
if not CHANNEL.startswith("@"):
    CHANNEL = "@" + CHANNEL

FILES = ["vless", "vmess", "shadowsocks", "trojan", "hysteria2", "whitelist"]
SUB_DIR = "sub"
os.makedirs(SUB_DIR, exist_ok=True)

def extract_host_port(config: str):
    match = re.search(r'@([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))
    match = re.search(r'ss://[^@]+@([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))
    match = re.search(r'(?:server|host)=([^&]+)&.*?port=(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))
    match = re.search(r'hy2://([^:]+):(\d+)', config)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

async def check(semaphore, file_name, config):
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

async def send_message(session, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        async with session.post(url, json=data, timeout=10) as resp:
            if resp.status != 200:
                print(f"Send error: {await resp.text()}")
    except Exception as e:
        print(f"Send exception: {e}")

async def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN not set")
        return

    semaphore = asyncio.Semaphore(50)
    tasks = []

    for file_name in FILES:
        path = os.path.join(CONFIG_DIR, f"{file_name}.txt")
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                cfg = line.strip()
                if cfg:
                    tasks.append(check(semaphore, file_name, cfg))

    if not tasks:
        print("No configs to check")
        return

    print(f"Checking {len(tasks)} configs...")
    results = [r for r in await asyncio.gather(*tasks) if r]
    print(f"Working: {len(results)}")

    if not results:
        async with aiohttp.ClientSession() as session:
            await send_message(session, "No working configs found")
        return

    grouped = {}
    for r in results:
        grouped.setdefault(r["file"], []).append(r["config"])

    all_configs = []
    for file_name, configs in grouped.items():
        sub_path = os.path.join(SUB_DIR, f"{file_name}.txt")
        with open(sub_path, "w", encoding="utf-8") as f:
            f.write("\n".join(configs) + "\n")
        all_configs.extend(configs)

    all_path = os.path.join(SUB_DIR, "allconfig.txt")
    with open(all_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_configs) + "\n")

    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo:
        base_raw = f"https://raw.githubusercontent.com/{repo}/main/sub/"
    else:
        base_raw = "https://raw.githubusercontent.com/your-username/your-repo/main/sub/"

    message = "✅ <b>Подписка обновлена!</b>\n\n"
    message += f"📦 <a href=\"{base_raw}allconfig.txt\">Все рабочие конфиги (все протоколы)</a>\n"

    if "whitelist" in grouped and grouped["whitelist"]:
        message += f"📦 <a href=\"{base_raw}whitelist.txt\">Whitelist (только vless+hy2)</a>\n"

    message += f"\n📊 Всего рабочих конфигов: {len(all_configs)}"

    async with aiohttp.ClientSession() as session:
        await send_message(session, message)

if __name__ == "__main__":
    asyncio.run(main())
