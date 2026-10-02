import feedparser

from config import GOOGLE_ALERT_RSS, TALKWALKER_RSS


def _read_feeds(value, source):
    if not value:
        return []

    results = []

    for rss_url in value.split(","):
        rss_url = rss_url.strip()

        if not rss_url:
            continue

        feed = feedparser.parse(rss_url)

        for entry in feed.entries:
            results.append({
                "source": source,
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "snippet": entry.get("summary", ""),
            })

    return results


def google_alerts():
    return _read_feeds(
        GOOGLE_ALERT_RSS,
        "Google Alerts"
    )


def talkwalker_alerts():
    return _read_feeds(
        TALKWALKER_RSS,
        "Talkwalker Alerts"
    )