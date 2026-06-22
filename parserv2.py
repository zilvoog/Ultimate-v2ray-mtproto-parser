import os
import re
import json
import asyncio
import aiohttp

# -------------------- НАСТРОЙКИ --------------------
CHANNELS_FILE = "telegram_channels.json"      # список Telegram-каналов
GITHUB_URLS_FILE = "github_repos.json"        # список raw-ссылок
OUTPUT_DIR = "Config"
OUTPUT_CHANNEL = "@rjaviiiiii"                # канал-получатель (исключаем)

# Паттерны для пяти основных протоколов
CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+"
}

# Паттерн для MTProto ссылок (tg://proxy?…)
MTPROTO_PATTERN = r'tg://proxy?[^\s\n\"\'<]+'

# Паттерн для подписок (для 4pda)
SUBSCRIPTION_PATTERN = r'https?://[^\s\n\"\'<>]+(?:subscription|sub|config|link)[^\s\n\"\'<>]*'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ --------------------
async def fetch_content(session, username):
    url = f"https://t.me/s/{username}"
    try:
        async with session.get(url, timeout=7) as resp:
            if resp.status == 200:
                text = await resp.text()
                new_channels = re.findall(r't\.me/([a-zA-Z0-9_]{5,30})', text)
                return text, list(set(new_channels))
    except:
        pass
    return "", []

async def fetch_4pda_page(session, topic_id=1110469, start=0):
    url = f"https://4pda.to/forum/index.php?showtopic={topic_id}&st={start}"
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status == 200:
                return await resp.text()
    except:
        pass
    return None

def extract_configs_from_text(text: str) -> set:
    """Извлекает все основные конфиги (vless, vmess, ss, trojan, hy2), фильтруя security=none."""
    configs = set()
    for pattern in CONFIG_PATTERNS.values():
        for match in re.finditer(pattern, text):
            cfg = match.group(0).replace("&amp;", "&")
            if "security=none" in cfg.lower():
                continue
            configs.add(cfg)
    return configs

def extract_configs_by_proto(text: str) -> dict:
    """Извлекает основные конфиги с группировкой по протоколам."""
    result = {proto: set() for proto in CONFIG_PATTERNS}
    for proto, pattern in CONFIG_PATTERNS.items():
        for match in re.finditer(pattern, text):
            cfg = match.group(0).replace("&amp;", "&")
            if "security=none" in cfg.lower():
                continue
            result[proto].add(cfg)
    return result

def extract_mtproto_links(text: str) -> set:
    """Извлекает все MTProto ссылки (tg://proxy?…)."""
    links = set()
    for match in re.finditer(MTPROTO_PATTERN, text, re.IGNORECASE):
        link = match.group(0).replace("&amp;", "&")
        links.add(link)
    return links

def extract_subscription_links(html: str) -> list:
    links = re.findall(SUBSCRIPTION_PATTERN, html, re.IGNORECASE)
    extra = re.findall(r'\[url\s*=\s*["\']?(https?://[^\s"\']+)["\']?\]', html, re.IGNORECASE)
    links.extend(extra)
    return list(set(l for l in links if '4pda.to/forum' not in l and 'showtopic' not in l))

# -------------------- ОСНОВНАЯ ФУНКЦИЯ --------------------
async def main():
    print("🚀 Парсер: Telegram -> протоколы, 4pda+GitHub -> whitelist.txt, MTProto -> mtproto.txt")

    # Для Telegram – по протоколам
    telegram_configs = {proto: set() for proto in CONFIG_PATTERNS}
    # Для 4pda+GitHub – общий набор
    whitelist_configs = set()
    # Для MTProto – общий набор (из всех источников)
    mtproto_configs = set()

    parsed_channels = set()

    async with aiohttp.ClientSession(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    ) as session:

        # ---------- 1. Telegram ----------
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                channels = [c.replace("@", "") for c in json.load(f)]
            output_clean = OUTPUT_CHANNEL.replace("@", "")
            if output_clean in channels:
                channels.remove(output_clean)
                print(f"⚠️ Канал {OUTPUT_CHANNEL} исключён")

            if channels:
                queue = channels
                for depth in range(2):   # два уровня глубины
                    next_queue = []
                    for username in queue:
                        if username in parsed_channels or username == output_clean:
                            continue
                        print(f"📡 Telegram: @{username}")
                        text, found_refs = await fetch_content(session, username)
                        parsed_channels.add(username)

                        # Основные конфиги по протоколам
                        proto_configs = extract_configs_by_proto(text)
                        for proto, cfgs in proto_configs.items():
                            telegram_configs[proto].update(cfgs)

                        # MTProto ссылки
                        mtproto_configs.update(extract_mtproto_links(text))

                        new_refs = [ref for ref in found_refs if ref != output_clean]
                        next_queue.extend(new_refs[:3])
                        await asyncio.sleep(0.8)
                    queue = next_queue

        # ---------- 2. 4pda ----------
        print("📡 4pda: 'Суверенный Интернет'...")
        subscription_links = set()
        for start in range(0, 200, 20):  # первые 10 страниц
            html = await fetch_4pda_page(session, start=start)
            if not html:
                break
            whitelist_configs.update(extract_configs_from_text(html))
            mtproto_configs.update(extract_mtproto_links(html))
            subscription_links.update(extract_subscription_links(html))
            await asyncio.sleep(1)

        # Загружаем найденные подписки
        if subscription_links:
            print(f"🔗 Найдено подписок: {len(subscription_links)}")
            for link in subscription_links:
                try:
                    async with session.get(link, timeout=10) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            whitelist_configs.update(extract_configs_from_text(content))
                            mtproto_configs.update(extract_mtproto_links(content))
                except:
                    pass

        # ---------- 3. GitHub (raw-ссылки) ----------
        if os.path.exists(GITHUB_URLS_FILE):
            with open(GITHUB_URLS_FILE, "r", encoding="utf-8") as f:
                raw_urls = json.load(f)   # список строк
            if isinstance(raw_urls, list):
                print(f"📥 GitHub: загрузка {len(raw_urls)} raw-файлов")
                for url in raw_urls:
                    try:
                        async with session.get(url, timeout=15) as resp:
                            if resp.status == 200:
                                content = await resp.text()
                                configs = extract_configs_from_text(content)
                                whitelist_configs.update(configs)
                                mtproto_configs.update(extract_mtproto_links(content))
                                print(f"   ✅ Загружено {len(configs)} конфигов из {url}")
                            else:
                                print(f"   ⚠️ Ошибка {resp.status}: {url}")
                    except Exception as e:
                        print(f"   ❌ Не удалось загрузить {url}: {e}")
            else:
                print("⚠️ github_repos.json должен содержать список строк (raw-ссылки)")
        else:
            print("ℹ️ github_repos.json не найден — пропускаем GitHub")

        # ---------- 4. Сохранение результатов ----------
        # 4a. Telegram – по протоколам
        for proto, cfgs in telegram_configs.items():
            if cfgs:
                path = os.path.join(OUTPUT_DIR, f"{proto}.txt")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(sorted(cfgs)) + "\n")
                print(f"💾 {proto}.txt: {len(cfgs)} конфигов")

        # 4b. 4pda+GitHub – единый whitelist.txt
        if whitelist_configs:
            path = os.path.join(OUTPUT_DIR, "whitelist.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(whitelist_configs)) + "\n")
            print(f"✅ whitelist.txt: {len(whitelist_configs)} конфигов")
        else:
            print("⚠️ Конфигов для whitelist не найдено")

        # 4c. MTProto – единый mtproto.txt
        if mtproto_configs:
            path = os.path.join(OUTPUT_DIR, "mtproto.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(mtproto_configs)) + "\n")
            print(f"✅ mtproto.txt: {len(mtproto_configs)} ссылок")
        else:
            print("⚠️ MTProto ссылок не найдено")

if __name__ == "__main__":
    asyncio.run(main())
