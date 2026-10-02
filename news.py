import feedparser


def google_news(query):
    url = (
        "https://news.google.com/rss/search?"
        f"q={query.replace(' ', '+')}"
        "&hl=ru&gl=RU&ceid=RU:ru"
    )

    feed = feedparser.parse(url)

    results = []

    for entry in feed.entries[:10]:
        results.append({
            "source": "Google News",
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "snippet": entry.get("summary", ""),
        })

    return results