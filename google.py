import requests

from config import GOOGLE_API_KEY, GOOGLE_CX


def search_google(query, limit=10):
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        return []

    try:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": GOOGLE_API_KEY,
                "cx": GOOGLE_CX,
                "q": query,
                "num": min(limit, 10),
            },
            timeout=15,
            headers={
                "User-Agent": "ONIST-bot/1.0"
            },
        )

        response.raise_for_status()

        data = response.json()

        results = []

        for item in data.get("items", []):
            results.append({
                "source": "Google Search",
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })

        return results

    except Exception as e:
        print("Google Search error:", e)
        return []
