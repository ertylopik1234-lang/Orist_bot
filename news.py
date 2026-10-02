import feedparser
from urllib.parse import quote_plus


def google_news(query, limit=10):
    url = (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}"
        "&hl=ru&gl=RU&ceid=RU:ru"
    )

    try:
        feed = feedparser.parse(url)

        results = []

        for entry in feed.entries[:limit]:
            results.append({
                "source": "Google News",
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "snippet": entry.get("summary", ""),
            })

        return results

    except Exception as e:
        print("Google News error:", e)
        return []
