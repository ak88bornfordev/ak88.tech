#!/usr/bin/env python3
"""
sync_telegram.py — подтягивает новые посты из телеграм-канала в ak88.html.

КАК ЭТО РАБОТАЕТ
-----------------
Бот, добавленный в канал администратором, получает все новые посты канала
через метод getUpdates (Bot API). Скрипт:
  1. Спрашивает у Telegram все новые обновления начиная с последнего
     обработанного (offset хранится в state.json).
  2. Отбирает среди них посты именно из вашего канала (channel_post).
  3. Форматирует каждый пост в HTML-карточку в стиле сайта.
  4. Вставляет новые карточки в ak88.html между маркерами
     <!-- AK88_POSTS_START --> и <!-- AK88_POSTS_END -->.

ВАЖНО ПРО ТОКЕН
-----------------
Токен бота НИКОГДА не хранится в этом файле и не попадает в сайт.
Скрипт читает его из переменной окружения TELEGRAM_BOT_TOKEN.

Запуск:
    export TELEGRAM_BOT_TOKEN="ваш_токен_бота"
    python3 sync_telegram.py

Для автоматического запуска по расписанию см. пример GitHub Actions
в комментарии внизу файла.
"""

import json
import os
import sys
import html
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ---- Настройки ----
CHANNEL_USERNAME = "ak88chanel"          # без @, из ссылки t.me/ak88chanel
SITE_DIR = os.path.dirname(os.path.abspath(__file__))
AK88_HTML_PATH = os.path.join(SITE_DIR, "ak88.html")
STATE_PATH = os.path.join(SITE_DIR, "telegram_state.json")

START_MARKER = "<!-- AK88_POSTS_START -->"
END_MARKER = "<!-- AK88_POSTS_END -->"

MONTHS_RU = [
    "янв", "фев", "мар", "апр", "май", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]


def load_dotenv(path):
    """Простой загрузчик .env без внешних зависимостей.
    Читает файл вида KEY=VALUE построчно и кладёт значения в os.environ,
    если такой переменной там ещё нет."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def get_token():
    load_dotenv(os.path.join(SITE_DIR, ".env"))
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit(
            "Ошибка: переменная TELEGRAM_BOT_TOKEN не найдена.\n"
            "Создайте файл .env рядом со скриптом на основе .env.example\n"
            "и впишите туда токен, либо задайте переменную окружения вручную:\n"
            '  export TELEGRAM_BOT_TOKEN="..."\n'
            "Никогда не прописывайте токен прямо в этом файле (sync_telegram.py) или в HTML сайта."
        )
    return token


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"last_update_id": 0, "posted_ids": []}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def api_call(token, method, params=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"Ошибка Telegram API ({method}): HTTP {e.code} — {e.read().decode('utf-8', 'ignore')}")
    if not data.get("ok"):
        sys.exit(f"Telegram API вернул ошибку: {data}")
    return data["result"]


def fetch_new_channel_posts(token, state):
    params = {
        "offset": state["last_update_id"] + 1,
        "timeout": 0,
        "allowed_updates": json.dumps(["channel_post"]),
    }
    updates = api_call(token, "getUpdates", params)

    new_posts = []
    max_update_id = state["last_update_id"]

    for upd in updates:
        max_update_id = max(max_update_id, upd["update_id"])
        post = upd.get("channel_post")
        if not post:
            continue
        chat = post.get("chat", {})
        if chat.get("username") != CHANNEL_USERNAME:
            continue
        post_id = post["message_id"]
        if post_id in state["posted_ids"]:
            continue
        text = post.get("text") or post.get("caption") or ""
        if not text.strip():
            continue  # пропускаем посты без текста (только фото/видео без подписи)
        new_posts.append({"id": post_id, "date": post["date"], "text": text})

    return new_posts, max_update_id


def format_date(ts):
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return f"{dt.day:02d} {MONTHS_RU[dt.month - 1]} {dt.year}"


def build_card(post):
    date_str = format_date(post["date"])
    text = html.escape(post["text"])
    lines = text.split("\n")
    title = lines[0][:120]
    preview = " ".join(lines[1:])[:180] or (text[:180] if len(text) > len(title) else "")
    post_url = f"https://t.me/{CHANNEL_USERNAME}/{post['id']}"
    return f'''          <a class="blog-row" href="{post_url}" target="_blank" rel="noopener">
            <span class="blog-date">{date_str}</span>
            <div class="blog-info">
              <h3>{title}</h3>
              <p>{preview}</p>
            </div>
            <span class="blog-tag">Telegram</span>
          </a>'''


def update_ak88_html(new_cards):
    if not os.path.exists(AK88_HTML_PATH):
        sys.exit(f"Не найден {AK88_HTML_PATH} — сначала должен существовать файл ak88.html")

    with open(AK88_HTML_PATH, encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        sys.exit("В ak88.html не найдены маркеры AK88_POSTS_START / AK88_POSTS_END")

    before, rest = content.split(START_MARKER, 1)
    middle, after = rest.split(END_MARKER, 1)

    if "Постов пока нет" in middle:
        middle = ""

    updated_middle = "\n" + "\n".join(new_cards) + "\n" + middle.strip() + "\n"

    new_content = before + START_MARKER + updated_middle + END_MARKER + after
    with open(AK88_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    token = get_token()
    state = load_state()

    new_posts, max_update_id = fetch_new_channel_posts(token, state)

    if not new_posts:
        print("Новых постов в канале нет.")
        state["last_update_id"] = max_update_id
        save_state(state)
        return

    new_posts.sort(key=lambda p: p["date"], reverse=True)
    cards = [build_card(p) for p in new_posts]

    update_ak88_html(cards)

    state["last_update_id"] = max_update_id
    state["posted_ids"] = list(set(state["posted_ids"]) | {p["id"] for p in new_posts})
    save_state(state)

    print(f"Добавлено новых постов: {len(new_posts)}")


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# Пример автоматического запуска через GitHub Actions по расписанию:
#
# .github/workflows/sync-telegram.yml
# ---------------------------------------------------------------------------
# name: Sync Telegram AK88
# on:
#   schedule:
#     - cron: "*/15 * * * *"   # каждые 15 минут
#   workflow_dispatch: {}       # + возможность запустить вручную
#
# jobs:
#   sync:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v4
#       - uses: actions/setup-python@v5
#         with:
#           python-version: "3.11"
#       - name: Run sync script
#         env:
#           TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
#         run: python3 sync_telegram.py
#       - name: Commit changes if any
#         run: |
#           git config user.name "telegram-sync-bot"
#           git config user.email "actions@users.noreply.github.com"
#           git add ak88.html telegram_state.json
#           git diff --cached --quiet || git commit -m "Sync AK88 posts from Telegram"
#           git push
#
# Токен добавляется в GitHub через:
#   Settings -> Secrets and variables -> Actions -> New repository secret
#   Имя: TELEGRAM_BOT_TOKEN
# Он никогда не появляется в самом коде репозитория.
# ---------------------------------------------------------------------------
