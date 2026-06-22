import os
import re
import json
import asyncio
import aiohttp

CHANNELS_FILE = "telegram_channels.json"
GITHUB_URLS_FILE = "github_repos.json"
OUTPUT_DIR = "Config"
OUTPUT_CHANNEL = os.environ.get("TELEGRAM_CHANNEL")
if not OUTPUT_CHANNEL:
    print("TELEGRAM_CHANNEL environment variable is not set")
    exit(1)
if not OUTPUT_CHANNEL.startswith("@"):
    OUTPUT_CHANNEL = "@" + OUTPUT_CHANNEL

CONFIG_PATTERNS = {
    "vless": r"vless://[^\s\n\"'<]+",
    "vmess": r"vmess://[^\s\n\"'<]+",
    "shadowsocks": r"ss://[^\s\n\"'<]+",
    "trojan": r"trojan://[^\s\n\"'<]+",
    "hysteria2": r"hy2://[^\s\n\"'<]+"
}

MTPROTO_PATTERN = r'tg://proxy?[^\s\n\"\'<]+'
GIT_RAW_PATTERN = r'https?://(?:raw\.githubusercontent\.com|gitlab\.com/.*?/raw/|gitverse\.ru/.*?/raw/)[^\s\n\"\'<>]+'
GIT_BLOB_PATTERN = r'https?://(?:github\.com/[^/]+/[^/]+/blob/|gitlab\.com/[^/]+/[^/]+/-/blob/|gitverse\.ru/[^/]+/[^/]+/blob/)[^\s\n\"\'<>]+'
SUBSCRIPTION_PATTERN = r'https?://[^\s\n\"\'<>]+(?:subscription|sub|config|link)[^\s\n\"\'<>]*'

os.makedirs(OUTPUT_DIR, exist_ok=True)

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

def extract_configs_from_text(text):
    configs = set()
    for pattern in CONFIG_PATTERNS.values():
        for match in re.finditer(pattern, text):
            cfg = match.group(0).replace("&amp;", "&")
            if "security=none" in cfg.lower():
                continue
            configs.add(cfg)
    return configs

def extract_vless_hy2_from_text(text):
    configs = set()
    for match in re.finditer(CONFIG_PATTERNS["vless"], text):
        cfg = match.group(0).replace("&amp;", "&")
        if "security=none" in cfg.lower():
            continue
        configs.add(cfg)
    for match in re.finditer(CONFIG_PATTERNS["hysteria2"], text):
        cfg = match.group(0).replace("&amp;", "&")
        if "security=none" in cfg.lower():
            continue
        configs.add(cfg)
    return configs

def extract_configs_by_proto(text):
    result = {proto: set() for proto in CONFIG_PATTERNS}
    for proto, pattern in CONFIG_PATTERNS.items():
        for match in re.finditer(pattern, text):
            cfg = match.group(0).replace("&amp;", "&")
            if "security=none" in cfg.lower():
                continue
            result[proto].add(cfg)
    return result

def extract_mtproto_links(text):
    links = set()
    for match in re.finditer(MTPROTO_PATTERN, text, re.IGNORECASE):
        link = match.group(0).replace("&amp;", "&")
        links.add(link)
    return links

def extract_subscription_links(html):
    links = re.findall(SUBSCRIPTION_PATTERN, html, re.IGNORECASE)
    extra = re.findall(r'\[url\s*=\s*["\']?(https?://[^\s"\']+)["\']?\]', html, re.IGNORECASE)
    links.extend(extra)
    return list(set(l for l in links if '4pda.to/forum' not in l and 'showtopic' not in l))

def convert_to_raw(url):
    if "github.com" in url and "/blob/" in url:
        parts = url.split("/")
        if len(parts) >= 7:
            user = parts[3]
            repo = parts[4]
            branch = parts[6]
            path = "/".join(parts[7:])
            return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}"
    if "gitlab.com" in url and "/-/blob/" in url:
        parts = url.split("/")
        try:
            idx = parts.index("-")
            if idx + 2 < len(parts) and parts[idx+1] == "blob":
                parts[idx+1] = "raw"
                return "/".join(parts)
        except ValueError:
            pass
    if "gitverse.ru" in url and "/blob/" in url:
        parts = url.split("/")
        try:
            idx = parts.index("blob")
            parts[idx] = "raw"
            return "/".join(parts)
        except ValueError:
            pass
    return url

def extract_git_links(html):
    raw_links = set(re.findall(GIT_RAW_PATTERN, html, re.IGNORECASE))
    blob_links = set(re.findall(GIT_BLOB_PATTERN, html, re.IGNORECASE))
    all_links = raw_links.union(blob_links)
    converted = {convert_to_raw(l) for l in all_links}
    return list(converted)

async def main():
    print("Starting parser (vless/hy2 -> whitelist, all protocols from Telegram)")
    telegram_configs = {proto: set() for proto in CONFIG_PATTERNS}
    whitelist_configs = set()
    mtproto_configs = set()
    parsed_channels = set()

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                channels = [c.replace("@", "") for c in json.load(f)]
            output_clean = OUTPUT_CHANNEL.replace("@", "")
            if output_clean in channels:
                channels.remove(output_clean)
                print(f"Channel {OUTPUT_CHANNEL} excluded")
            if channels:
                queue = channels
                for depth in range(2):
                    next_queue = []
                    for username in queue:
                        if username in parsed_channels or username == output_clean:
                            continue
                        print(f"Telegram: @{username}")
                        text, found_refs = await fetch_content(session, username)
                        parsed_channels.add(username)
                        proto_configs = extract_configs_by_proto(text)
                        for proto, cfgs in proto_configs.items():
                            telegram_configs[proto].update(cfgs)
                        mtproto_configs.update(extract_mtproto_links(text))
                        new_refs = [ref for ref in found_refs if ref != output_clean]
                        next_queue.extend(new_refs[:3])
                        await asyncio.sleep(0.8)
                    queue = next_queue

        print("Parsing 4pda: Sovereign Internet topic...")
        subscription_links = set()
        git_links = set()
        for start in range(0, 200, 20):
            html = await fetch_4pda_page(session, start=start)
            if not html:
                break
            whitelist_configs.update(extract_vless_hy2_from_text(html))
            mtproto_configs.update(extract_mtproto_links(html))
            subscription_links.update(extract_subscription_links(html))
            git_links.update(extract_git_links(html))
            await asyncio.sleep(1)

        if subscription_links:
            print(f"Found {len(subscription_links)} subscription links")
            for link in subscription_links:
                try:
                    async with session.get(link, timeout=10) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            whitelist_configs.update(extract_vless_hy2_from_text(content))
                            mtproto_configs.update(extract_mtproto_links(content))
                except:
                    pass

        if git_links:
            print(f"Found {len(git_links)} git file links")
            for link in git_links:
                try:
                    async with session.get(link, timeout=15) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            configs = extract_vless_hy2_from_text(content)
                            whitelist_configs.update(configs)
                            mtproto_configs.update(extract_mtproto_links(content))
                            if configs:
                                print(f"Loaded {len(configs)} vless/hy2 from {link}")
                except Exception as e:
                    print(f"Failed to load {link}: {e}")

        if os.path.exists(GITHUB_URLS_FILE):
            try:
                with open(GITHUB_URLS_FILE, "r", encoding="utf-8") as f:
                    raw_urls = json.load(f)
                if isinstance(raw_urls, list):
                    print(f"GitHub from list: {len(raw_urls)} raw files")
                    for url in raw_urls:
                        try:
                            async with session.get(url, timeout=15) as resp:
                                if resp.status == 200:
                                    content = await resp.text()
                                    configs = extract_vless_hy2_from_text(content)
                                    whitelist_configs.update(configs)
                                    mtproto_configs.update(extract_mtproto_links(content))
                                    print(f"Loaded {len(configs)} vless/hy2 from {url}")
                        except Exception as e:
                            print(f"Failed to load {url}: {e}")
                else:
                    print("github_repos.json must contain a list of strings, skipping")
            except:
                print("Error reading github_repos.json, skipping")
        else:
            print("github_repos.json not found, skipping")

        for proto, cfgs in telegram_configs.items():
            if cfgs:
                path = os.path.join(OUTPUT_DIR, f"{proto}.txt")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(sorted(cfgs)) + "\n")
                print(f"Saved {proto}.txt: {len(cfgs)} configs")

        if whitelist_configs:
            path = os.path.join(OUTPUT_DIR, "whitelist.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(whitelist_configs)) + "\n")
            print(f"Saved whitelist.txt: {len(whitelist_configs)} vless/hy2 configs")
        else:
            print("No vless/hy2 configs for whitelist")

        if mtproto_configs:
            path = os.path.join(OUTPUT_DIR, "mtproto.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(mtproto_configs)) + "\n")
            print(f"Saved mtproto.txt: {len(mtproto_configs)} links")
        else:
            print("No MTProto links found")

if __name__ == "__main__":
    asyncio.run(main())
