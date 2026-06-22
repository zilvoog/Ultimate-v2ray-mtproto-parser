# 🚀 V2Ray Config Harvester & Checker

<p align="center">
  <img src="https://img.shields.io/badge/Developer-Rjavii__Gang-blueviolet?style=for-the-badge&logo=telegram" alt="Developer">
  <img src="https://img.shields.io/badge/Version-3.0.0-green?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Platform-GitHub%20Actions-blue?style=for-the-badge&logo=githubactions" alt="Platform">
</p>

---

## 🌐 English / Английский

### System Overview

**parserv3** is an automated V2Ray configuration harvester and MTProto proxy extractor that runs every 30 minutes via GitHub Actions. It collects configs from multiple sources, checks their availability, and publishes a subscription feed with clickable links.

#### What it does

1. **Harvests** V2Ray configs (`vless://`, `vmess://`, `ss://`, `trojan://`, `hy2://`) from:
   - Telegram channels (specified in `telegram_channels.json`)
   - 4pda forum (topic "Sovereign Internet")
   - Raw files from GitHub/GitLab/GitVerse (links found on 4pda or manually specified in `github_repos.json`)

2. **Filters**:
   - Excludes configs with `security=none`
   - Saves only `vless://` and `hy2://` from 4pda/GitHub sources into `Config/whitelist.txt`

3. **Checks** availability:
   - TCP connection to the server (port open)
   - For `vless`, `vmess`, `hysteria2` – additional HTTP request to `http://connectivitycheck.gstatic.com/generate_204`
   - For other protocols – TCP + (if TLS required) TLS handshake

4. **Publishes** the results:
   - Saves working configs into the `sub/` folder:
     - `allconfig.txt` – all working configs (all protocols)
     - `whitelist.txt` – working `vless` + `hy2` (if any)
     - Individual files per protocol (`vless.txt`, `vmess.txt`, etc.)
   - Sends a Telegram message with raw links to these files (subscription feed).
   - Also processes MTProto proxies (`tg://proxy?…`) and sends a separate message with clickable proxy links.

#### Repository Structure

| File / Folder | Description |
| :--- | :--- |
| `Config/` | Raw harvested configs (before checking) |
| `Config/vless.txt`, `vmess.txt`, ... | Configs by protocol (from Telegram) |
| `Config/whitelist.txt` | `vless` + `hy2` from 4pda/GitHub |
| `Config/mtproto.txt` | Collected MTProto links (`tg://proxy?…`) |
| `sub/` | **Checked & working** configs (published) |
| `sub/allconfig.txt` | All working configs (subscription) |
| `sub/whitelist.txt` | Working `vless` + `hy2` (if any) |
| `sub/vless.txt`, `vmess.txt`, ... | Working configs per protocol |
| `telegram_channels.json` | List of Telegram channels to parse |
| `github_repos.json` | List of raw URLs to additional config files |
| `parserv3.py` | Main harvester script |
| `checker.py` | Availability checker & publisher |
| `checker_mtproto.py` | MTProto checker & publisher |
| `.github/workflows/run.yml` | GitHub Actions workflow (runs every 30 min) |

#### Secrets Configuration (required)

You must set these GitHub secrets for Telegram publishing:

- `TELEGRAM_BOT_TOKEN` – your bot token
- `TELEGRAM_CHANNEL` – channel username (with or without `@`, e.g. `rjaviiiiii`)

#### How to use

1. Fork this repository.
2. Add the required secrets in your repository settings.
3. Update `telegram_channels.json` with channels you want to scrape.
4. Optionally add raw URLs to `github_repos.json` for additional config sources.
5. The workflow will run automatically every 30 minutes.
6. You can also trigger it manually from the "Actions" tab.

#### Credits

Developed and maintained by **Rjavii_Gang**.

---

## 🇷🇺 Русский / Russian

### Обзор системы

**parserv3** — это автоматический сборщик и проверщик V2Ray-конфигураций и MTProto-прокси, который запускается каждые 30 минут через GitHub Actions. Он собирает ключи из нескольких источников, проверяет их работоспособность и публикует подписку с кликабельными ссылками.

#### Что он делает

1. **Собирает** V2Ray-конфиги (`vless://`, `vmess://`, `ss://`, `trojan://`, `hy2://`) из:
   - Telegram-каналов (указанных в `telegram_channels.json`)
   - Форума 4pda (тема «Суверенный Интернет»)
   - Raw-файлов с GitHub/GitLab/GitVerse (ссылки, найденные на 4pda или вручную добавленные в `github_repos.json`)

2. **Фильтрует**:
   - Исключает конфиги с `security=none`
   - В `Config/whitelist.txt` сохраняет только `vless://` и `hy2://` из 4pda и GitHub

3. **Проверяет** доступность:
   - TCP-соединение к серверу (порт открыт)
   - Для `vless`, `vmess`, `hysteria2` – дополнительный HTTP-запрос к `http://connectivitycheck.gstatic.com/generate_204`
   - Для остальных протоколов – TCP + (если нужен TLS) рукопожатие TLS

4. **Публикует** результаты:
   - Сохраняет рабочие конфиги в папку `sub/`:
     - `allconfig.txt` – все рабочие конфиги (все протоколы)
     - `whitelist.txt` – рабочие `vless` + `hy2` (если есть)
     - Отдельные файлы по протоколам (`vless.txt`, `vmess.txt` и т.д.)
   - Отправляет сообщение в Telegram с raw-ссылками на эти файлы (подписка).
   - Также обрабатывает MTProto-прокси (`tg://proxy?…`) и отправляет отдельное сообщение со списком рабочих ссылок.

#### Структура репозитория

| Файл / Папка | Описание |
| :--- | :--- |
| `Config/` | Сырые собранные конфиги (до проверки) |
| `Config/vless.txt`, `vmess.txt`, ... | Конфиги по протоколам (из Telegram) |
| `Config/whitelist.txt` | `vless` + `hy2` из 4pda/GitHub |
| `Config/mtproto.txt` | Собранные MTProto-ссылки (`tg://proxy?…`) |
| `sub/` | **Проверенные и рабочие** конфиги (публикуются) |
| `sub/allconfig.txt` | Все рабочие конфиги (подписка) |
| `sub/whitelist.txt` | Рабочие `vless` + `hy2` (если есть) |
| `sub/vless.txt`, `vmess.txt`, ... | Рабочие конфиги по протоколам |
| `telegram_channels.json` | Список Telegram-каналов для парсинга |
| `github_repos.json` | Список raw-URL-адресов дополнительных файлов с конфигами |
| `parserv3.py` | Основной скрипт парсера |
| `checker.py` | Скрипт проверки и публикации |
| `checker_mtproto.py` | Скрипт проверки MTProto и публикации |
| `.github/workflows/run.yml` | GitHub Actions workflow (запуск каждые 30 мин) |

#### Настройка секретов (обязательно)

Для публикации в Telegram необходимо добавить следующие секреты в настройках репозитория:

- `TELEGRAM_BOT_TOKEN` – токен вашего бота
- `TELEGRAM_CHANNEL` – имя канала (с `@` или без, например `rjaviiiiii`)

#### Как использовать

1. Форкните этот репозиторий.
2. Добавьте необходимые секреты в настройках репозитория.
3. Обновите `telegram_channels.json` – укажите каналы для парсинга.
4. При желании добавьте raw-ссылки в `github_repos.json` для дополнительных источников.
5. Workflow будет запускаться автоматически каждые 30 минут.
6. Вы также можете запустить его вручную в разделе «Actions».

#### Авторы

Разработано и поддерживается **Rjavii_Gang**.

---

<p align="center">
  <b>parserv3</b> — automated config harvesting & checking system.
</p>
