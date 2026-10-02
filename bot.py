import os
import re

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN
from google import search_google
from alerts import google_alerts, talkwalker_alerts
from news import google_news


def normalize_phone(value):
    digits = re.sub(r"\D", "", value)

    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]

    return digits


def phone_variants(phone):
    digits = normalize_phone(phone)

    if len(digits) != 11 or not digits.startswith("7"):
        return [phone]

    return [
        digits,
        "+" + digits,
        "7 " + digits[1:4] + " " + digits[4:7] + " " +
        digits[7:9] + " " + digits[9:11],
        "+7 " + digits[1:4] + " " + digits[4:7] + "-" +
        digits[7:9] + "-" + digits[9:11],
        "8 " + digits[1:4] + " " + digits[4:7] + "-" +
        digits[7:9] + "-" + digits[9:11],
    ]


def result_contains_phone(item, variants):
    text = " ".join([
        str(item.get("title", "")),
        str(item.get("snippet", "")),
        str(item.get("url", "")),
    ]).lower()

    normalized_text = re.sub(r"\D", "", text)

    digits = normalize_phone(variants[0])

    if digits and digits in normalized_text:
        return True

    for variant in variants:
        clean_variant = variant.lower().replace(" ", "")
        if clean_variant in text.replace(" ", ""):
            return True

    return False


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


def search_phone(phone):
    variants = phone_variants(phone)
    results = []

    for variant in variants:
        try:
            query = f'"{variant}"'
            results.extend(search_google(query, limit=10))
        except Exception as e:
            print("Google:", e)

    # Google Alerts
    try:
        alert_results = google_alerts()

        for item in alert_results:
            if result_contains_phone(item, variants):
                results.append(item)

    except Exception as e:
        print("Google Alerts:", e)

    # Talkwalker
    try:
        talkwalker_results = talkwalker_alerts()

        for item in talkwalker_results:
            if result_contains_phone(item, variants):
                results.append(item)

    except Exception as e:
        print("Talkwalker:", e)

    # Google News
    for variant in variants[:3]:
        try:
            results.extend(
                google_news(f'"{variant}"')
            )
        except Exception as e:
            print("Google News:", e)

    # Финальная фильтрация
    filtered = []

    for item in results:
        source = item.get("source", "")

        # Для Google Search оставляем только материалы,
        # где номер найден в результате.
        if source == "Google Search":
            if result_contains_phone(item, variants):
                filtered.append(item)

        # Для Alerts/Talkwalker/News тоже проверяем номер.
        else:
            if result_contains_phone(item, variants):
                filtered.append(item)

    return unique_results(filtered)


def search_name(name):
    results = []

    try:
        results.extend(
            search_google(f'"{name}"', limit=10)
        )
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
        results.extend(
            google_news(f'"{name}"')
        )
    except Exception as e:
        print("Google News:", e)

    return unique_results(results)


def format_results(query, results):
    text = (
        "🔎 Результаты поиска\n\n"
        f"Запрос: {query}\n\n"
    )

    if not results:
        return (
            text +
            "Ничего релевантного не найдено.\n\n"
            "ℹ️ Это означает только то, что в подключённых "
            "публичных источниках не обнаружено совпадений."
        )

    sources = {}

    for item in results:
        sources.setdefault(
            item.get("source", "Источник"),
            []
        ).append(item)

    text += f"📊 Релевантных результатов: {len(results)}\n\n"

    for source, items in sources.items():
        text += f"━━ {source} ━━\n"

        for item in items[:5]:
            title = item.get("title", "")[:120]
            url = item.get("url", "")

            text += (
                f"• {title}\n"
                f"  {url}\n"
            )

        text += "\n"

    text += (
        "🔐 Проверяются только публичные источники. "
        "Совпадение номера или имени не подтверждает "
        "личность владельца."
    )

    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Публичный поиск\n\n"
        "📱 /phone 79911990209\n"
        "👤 /name Иван Петров\n\n"
        "🔎 Ищу совпадения только в публичных источниках."
    )


async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Пример:\n/phone 79911990209"
        )
        return

    query = " ".join(context.args)

    msg = await update.message.reply_text(
        "🔎 Ищу публичные упоминания номера..."
    )

    results = search_phone(query)

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
        "🔎 Ищу публичные упоминания..."
    )

    results = search_name(query)

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
