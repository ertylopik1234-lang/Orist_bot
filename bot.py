import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN
from google import search_google
from alerts import google_alerts, talkwalker_alerts
from news import google_news


def unique_results(results):
    seen = set()
    output = []

    for item in results:
        url = item.get("url", "")

        if not url or url in seen:
            continue

        seen.add(url)
        output.append(item)

    return output


def search_everywhere(query):
    results = []

    try:
        results.extend(search_google(query))
    except Exception as e:
        print("Google:", e)

    try:
        results.extend(google_alerts())
    except Exception as e:
        print("Google Alerts:", e)

    try:
        results.extend(talkwalker_alerts())
    except Exception as e:
        print("Talkwalker:", e)

    try:
        results.extend(google_news(query))
    except Exception as e:
        print("Google News:", e)

    return unique_results(results)


def format_results(query, results):
    text = (
        "🔎 Результаты поиска\n\n"
        f"Запрос: {query}\n\n"
    )

    if not results:
        return text + "Ничего не найдено."

    sources = {}

    for item in results:
        sources.setdefault(item["source"], []).append(item)

    text += f"📊 Уникальных результатов: {len(results)}\n\n"

    for source, items in sources.items():
        text += f"━━ {source} ━━\n"

        for item in items[:5]:
            title = item.get("title", "")[:100]
            url = item.get("url", "")

            text += (
                f"• {title}\n"
                f"  {url}\n"
            )

        text += "\n"

    text += (
        "🔐 Используются публичные источники. "
        "Совпадение имени, номера или аккаунта "
        "само по себе не подтверждает личность человека."
    )

    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Публичный поиск\n\n"
        "📱 /phone 79024246175\n"
        "👤 /name Иван Петров\n\n"
        "🔎 Бот проверяет подключённые публичные источники."
    )


async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Пример:\n/phone 79024246175"
        )
        return

    query = " ".join(context.args)

    msg = await update.message.reply_text(
        "🔎 Проверяю источники..."
    )

    results = search_everywhere(query)

    await msg.edit_text(
        format_results(query, results),
        disable_web_page_preview=True
    )


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Пример:\n/name Иван Петров"
        )
        return

    query = " ".join(context.args)

    msg = await update.message.reply_text(
        "🔎 Проверяю источники..."
    )

    results = search_everywhere(f'"{query}"')

    await msg.edit_text(
        format_results(query, results),
        disable_web_page_preview=True
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не указан в Environment Variables"
        )

    port = int(os.environ.get("PORT", "10000"))

    render_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not render_url:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL не найден"
        )

    webhook_url = f"{render_url}/telegram"

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("phone", phone))
    app.add_handler(CommandHandler("name", name))

    print(f"Starting webhook on port {port}")
    print(f"Webhook URL: {webhook_url}")

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="telegram",
        webhook_url=webhook_url,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
