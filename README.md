# 🚀 parserv2

<p align="center">
  <img src="https://img.shields.io/badge/Developer-Rjavii__Gang-blueviolet?style=for-the-badge&logo=telegram" alt="Developer">
  <img src="https://img.shields.io/badge/Version-2.0.0-green?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Platform-GitHub%20Actions-blue?style=for-the-badge&logo=githubactions" alt="Platform">
</p>

An automated, high-performance V2Ray configuration harvester and MTProto proxy extractor. Powered by Python and automated seamlessly via GitHub Actions.

---

## 🛠️ System Architecture

Every 30 minutes, **parserv2** triggers an automated workflow that executes the following pipeline:

1. **Scraping Nodes:** Dynamically parses target Telegram channels specified in `telegram_channels.json`.
2. **Resource Extraction:** Captures live nodes across multiple secure protocols (VLESS, VMess, Shadowsocks, Trojan, Hysteria 2) alongside operational MTProto proxies.

---

## 📂 Repository Structure

### Configuration Subscription Feeds
| Protocol | Source Location |
| :--- | :--- |
| **VLESS** | [`Config/vless.txt`](Config/vless.txt) |
| **VMess** | [`Config/vmess.txt`](Config/vmess.txt) |
| **Shadowsocks** | [`Config/shadowsocks.txt`](Config/shadowsocks.txt) |
| **Trojan** | [`Config/trojan.txt`](Config/trojan.txt) |
| **Hysteria 2** | [`Config/hysteria2.txt`](Config/hysteria2.txt) |
| **MTProto Proxies** | [`Config/proxies.txt`](Config/proxies.txt) |

### System Logs & Analytics
* [`telegram_channels.json`](telegram_channels.json) — Dynamically updated node mapping index. Inaccessible or faulty channels are automatically pruned.
* [`Logs/channel_stats.json`](Logs/channel_stats.json) — Live metric tracking displaying specific counts per protocol and performance sorting scores (`score`).
* [`Logs/invalid_channels.txt`](Logs/invalid_channels.txt) — Quarantined list tracking offline or legacy source endpoints.

---

## 💡 Contribution & Issues

* **Discovered a new resource?** If you know of a public Telegram channel providing active configurations, please open an entry in the **Issues** section so we can merge it into the tracking matrix!
* **System Cron:** Runs entirely serverless on a 30-minute automated cron cycle.

---

<p align="center">
  <b>parserv2</b> is maintained and curated by <b>Rjavii_Gang</b>.
</p>
