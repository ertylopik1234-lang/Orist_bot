import os
import re
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import BOT_TOKEN

from google import search_google
from alerts import google_alerts, talkwalker_alerts
from news import google_news

from parser import (
    parse_public_page,
    clean_text,
)


def normalize_phone(phone):
    return re.sub(r"\D", "", phone)


def phone_variants(phone):
    digits = normalize_phone(phone)

    variants = []

    if not digits:
        return variants

    variants.append(digits)

    if digits.startswith("8") and len(digits) == 11:
        variants.append("7" + digits[1:])

    if digits.startswith("7") and len(digits) == 11:
        variants.append("8" + digits[1:])

    if digits.startswith("7") and len(digits) == 11:
        variants.append("+" + digits)

        variants.append(
            "+7 "
            + digits[1:4]
            + " "
            + digits[4:7]
            + " "
            + digits[7:9]
            + " "
            + digits[9:11]
        )

        variants.append(
            "+7 "
            + digits[1:4]
            + " "
            + digits[4:7]
            + "-"
            + digits[7:9]
            + "-"
            + digits[9:11]
        )

    return list(dict.fromkeys(variants))


def result_contains_text(item, query):
    text = " ".join(
        [
            str(item.get("title", "")),
            str(item.get("snippet", "")),
        ]
    ).lower()

    query = clean_text(query).lower().strip()

    return bool(query) and query in text


def result_contains_phone(item, phone):
    text = " ".join(
        [
            str(item.get("title", "")),
            str(item.get("snippet", "")),
            str(item.get("url", "")),
        ]
    )

    digits_text = normalize_phone(text)

    phone_digits = normalize_phone(phone)

    if not phone_digits:
        return False

    if phone_digits in digits_text:
        return True

    for variant in phone_variants(phone):
        variant_digits = normalize_phone(variant)

        if variant_digits and variant_digits in digits_text:
            return True

    return False


def unique_results(results):
    result = []
    seen = set()

    for item in results:
        url = item.get("url", "").strip()

        if not url:
            continue

        key = url.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def search_name(name):
    results = []

    try:
        results.extend(
            search_google(
                f'"{name}"',
                limit=10
            )
        )
    except Exception as e:
        print("Google:", e)

    try:
        for item in google_alerts():
            if result_contains_text(item, name):
                results.append(item)
    except Exception as e:
        print("Google Alerts:", e)

    try:
        for item in talkwalker_alerts():
            if result_contains_text(item, name):
                results.append(item)
    except Exception as e:
        print("Talkwalker:", e)

    try:
        results.extend(
            google_news(
                f'"{name}"',
                limit=10
            )
        )
    except Exception as e:
        print("Google News:", e)

    return unique_results(results)


def search_phone(phone):
    results = []

    variants = phone_variants(phone)

    if not variants:
        return []

    search_variants = variants[:6]

    for variant in search_variants:
        try:
            query = f'"{variant}"'

            results.extend(
                search_google(
                    query,
                    limit=10
                )
            )

        except Exception as e:
            print("Google phone:", e)

    try:
        for item in google_alerts():
            if result_contains_phone(item, phone):
                results.append(item)

    except Exception as e:
        print("Google Alerts phone:", e)

    try:
        for item in talkwalker_alerts():
            if result_contains_phone(item, phone):
                results.append(item)

    except Exception as e:
        print("Talkwalker phone:", e)

    for variant in search_variants[:3]:

        try:
            results.extend(
                google_news(
                    f'"{variant}"',
                    limit=10
                )
            )

        except Exception as e:
            print("Google News phone:", e)

    results = [
        item
        for item in results
        if (
            item.get("source") == "Google Search"
            or result_contains_phone(item, phone)
        )
    ]

    return unique_results(results)


def collect_public_pages(results, query):
    pages = []

    urls = []

    for item in results:
        url = item.get("url", "").strip()

        if not url:
            continue

        if url in urls:
            continue

        urls.append(url)

        if len(urls) >= 15:
            break

    for url in urls:

        parsed = parse_public_page(
            url,
            query=query
        )

        if parsed:
            pages.append(parsed)

    return pages


def extract_socials(pages):
    result = []
    seen = set()

    for page in pages:

        for social in page.get(
            "socials",
            []
        ):

            key = social["url"].lower()

            if key in seen:
                continue

            seen.add(key)

            result.append(social)

    return result


def extract_emails(pages):
    result = []
    seen = set()

    for page in pages:

        for email in page.get(
            "emails",
            []
        ):

            if email in seen:
                continue

            seen.add(email)
            result.append(email)

    return result


def extract_page_phones(pages):
    result = []
    seen = set()

    for page in pages:

        for phone in page.get(
            "phones",
            []
        ):

            normalized = normalize_phone(phone)

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(phone)

    return result


def get_domain(url):
    try:
        return urlparse(url).netloc.lower().removeprefix(
            "www."
        )
    except Exception:
        return ""


def format_socials(socials):
    if not socials:
        return ""

    lines = [
        "",
        "🌐 Публичные социальные страницы:"
    ]

    for social in socials[:10]:

        lines.append(
            f"• {social['name']} — {social['url']}"
        )

    return "\n".join(lines)


def format_pages(pages):
    if not pages:
        return ""

    lines = [
        "",
        "🔎 Открытые публичные страницы:"
    ]

    count = 0

    for page in pages:

        title = (
            page.get("title")
            or page.get("domain")
            or "Страница"
        )

        url = page.get("url", "")

        if not url:
            continue

        lines.append(
            f"• {title[:100]}"
        )

        lines.append(
            f"  {url}"
        )

        count += 1

        if count >= 10:
            break

    return "\n".join(lines)


def format_news(results):
    news = [
        item
        for item in results
        if item.get("source") == "Google News"
    ]

    if not news:
        return ""

    lines = [
        "",
        "📰 Новости:"
    ]

    for item in news[:8]:

        title = clean_text(
            item.get("title", "")
        )

        url = item.get("url", "")

        if not title or not url:
            continue

        lines.append(
            f"• {title[:140]}"
        )

        lines.append(
            f"  {url}"
        )

    return "\n".join(lines)


def format_extra_data(pages):
    phones = extract_page_phones(pages)
    emails = extract_emails(pages)

    lines = []

    if phones:
        lines.append("")
        lines.append("📱 Публично опубликованные телефоны:")

        for phone in phones[:10]:
            lines.append(f"• {phone}")

    if emails:
        lines.append("")
        lines.append("✉️ Публично опубликованные email:")

        for email in emails[:10]:
            lines.append(f"• {email}")

    return "\n".join(lines)


def build_report(query, results, pages, mode):
    socials = extract_socials(pages)

    lines = []

    if mode == "phone":
        lines.append(
            f"📱 Номер: {query}"
        )
    else:
        lines.append(
            f"👤 Запрос: {query}"
        )

    lines.append("")

    if results:
        lines.append(
            f"🔎 Найдено публичных результатов: "
            f"{len(results)}"
        )
    else:
        lines.append(
            "🔎 Публичных результатов не найдено."
        )

    lines.append(
        format_extra_data(pages)
    )

    lines.append(
        format_socials(socials)
    )

    lines.append(
        format_pages(pages)
    )

    lines.append(
        format_news(results)
    )

    lines.append("")

    lines.append(
        "ℹ️ Бот показывает только информацию, "
        "доступную публично в найденных источниках."
    )

    lines.append(
        "Личность частного владельца номера "
        "по скрытым или закрытым данным не устанавливается."
    )

    return "\n".join(
        line
        for line in lines
        if line is not None
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Я ищу публичные упоминания в интернете.\n\n"
        "Команды:\n"
        "/phone 79911990209\n"
        "/name Иван Петров\n\n"
        "Поиск работает только с публичными источниками."
    )


async def phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:

        await update.message.reply_text(
            "Использование:\n"
            "/phone 79911990209"
        )

        return

    value = " ".join(
        context.args
    ).strip()

    if len(normalize_phone(value)) < 7:

        await update.message.reply_text(
            "❌ Похоже, номер слишком короткий."
        )

        return

    await update.message.reply_text(
        "🔎 Ищу публичные упоминания номера..."
    )

    results = search_phone(value)

    pages = collect_public_pages(
        results,
        value
    )

    report = build_report(
        value,
        results,
        pages,
        "phone"
    )

    await update.message.reply_text(
        report[:4000],
        disable_web_page_preview=True
    )


async def name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:

        await update.message.reply_text(
            "Использование:\n"
            "/name Иван Петров"
        )

        return

    value = " ".join(
        context.args
    ).strip()

    if len(value) < 2:

        await update.message.reply_text(
            "❌ Введи имя или имя и фамилию."
        )

        return

    await update.message.reply_text(
        "🔎 Ищу публичные упоминания..."
    )

    results = search_name(value)

    pages = collect_public_pages(
        results,
        value
    )

    report = build_report(
        value,
        results,
        pages,
        "name"
    )

    await update.message.reply_text(
        report[:4000],
        disable_web_page_preview=True
    )


def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не указан в Environment Variables"
        )

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    render_url = os.environ.get(
        "RENDER_EXTERNAL_URL"
    )

    if not render_url:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL не найден"
        )

    webhook_url = (
        f"{render_url.rstrip('/')}/telegram"
    )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "phone",
            phone
        )
    )

    app.add_handler(
        CommandHandler(
            "name",
            name
        )
    )

    print(
        f"Starting webhook on port {port}"
    )

    print(
        f"Webhook URL: {webhook_url}"
    )

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="telegram",
        webhook_url=webhook_url,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
